from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from .models import SalesInvoice, SalesReturn, SalesCreditNote, SalesInvoiceItem, SalesReturnItem, SalesInvoiceItem


@receiver(post_save, sender=SalesInvoice)
def create_cashbox_transaction_for_sales(sender, instance, created, **kwargs):
    """إنشاء معاملة صندوق تلقائياً عند إنشاء فاتورة مبيعات نقدية"""
    # 🔧 تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        from cashboxes.models import CashboxTransaction
        from core.models import AuditLog
        
        # التحقق من أن الفاتورة جديدة ونقدية
        if created and instance.payment_type == 'cash' and instance.total_amount > 0:
            # 🔧 استخدام الصندوق المحدد في الفاتورة أولاً (إن وُجد)
            cashbox = instance.cashbox
            
            # إذا لم يكن هناك صندوق محدد، حدد واحد حسب المستخدم
            if not cashbox:
                # إذا كان المستخدم يستطيع الوصول لنقطة البيع، استخدم صندوقه الخاص
                if instance.created_by.has_perm('users.can_access_pos'):
                    from cashboxes.models import Cashbox
                    cashbox = Cashbox.objects.filter(responsible_user=instance.created_by).first()
                    
                    # إذا لم يكن له صندوق، إنشاء واحد تلقائياً
                    if not cashbox:
                        # اسم الصندوق = اسم المستخدم
                        cashbox_name = instance.created_by.username
                        
                        # الحصول على العملة الأساسية
                        from core.models import CompanySettings
                        company_settings = CompanySettings.get_settings()
                        currency = 'JOD'
                        if company_settings and company_settings.currency:
                            currency = company_settings.currency
                        
                        cashbox = Cashbox.objects.create(
                            name=cashbox_name,
                            description=_('صندوق مستخدم نقطة البيع: %(full_name)s') % {
                                'full_name': instance.created_by.get_full_name() or instance.created_by.username
                            },
                            balance=Decimal('0.000'),
                            currency=currency,
                            location=_('نقطة البيع - %(username)s') % {'username': instance.created_by.username},
                            responsible_user=instance.created_by,
                            is_active=True
                        )
                        
                        # تسجيل إنشاء الصندوق في سجل الأنشطة
                        try:
                            AuditLog.objects.create(
                                user=instance.created_by,
                                action='create',
                                model_name='Cashbox',
                                object_id=cashbox.id,
                                object_repr=str(cashbox),
                                description=_('تم إنشاء صندوق تلقائياً لمستخدم نقطة البيع: %(username)s') % {'username': instance.created_by.username},
                                ip_address='127.0.0.1'
                            )
                        except Exception as log_error:
                            print(f"خطأ في تسجيل نشاط إنشاء الصندوق: {log_error}")
                
                # إذا لم يتم تحديد صندوق، استخدم الصندوق الرئيسي أو إنشاء واحد
                if not cashbox:
                    from cashboxes.models import Cashbox
                    cashbox = Cashbox.objects.filter(name__icontains='رئيسي', is_active=True).first()
                    if not cashbox:
                        cashbox = Cashbox.objects.filter(is_active=True).first()
                    if not cashbox:
                        # إنشاء صندوق رئيسي افتراضي
                        cashbox = Cashbox.objects.create(
                            name='الصندوق الرئيسي',
                            description='الصندوق الرئيسي للمبيعات النقدية',
                            balance=0,
                            location='المكتب الرئيسي',
                            is_active=True
                        )
                
                # ربط الفاتورة بالصندوق (فقط إذا لم يكن محدداً مسبقاً)
                if cashbox and not instance.cashbox:
                    instance.cashbox = cashbox
                    instance.save(update_fields=['cashbox'])
            
            # إنشاء معاملة إيداع في الصندوق
            if cashbox:
                # CashboxTransaction model does not have reference_type/reference_id fields
                # (we avoid adding DB fields for now). Store invoice identity in the description
                transaction = CashboxTransaction.objects.create(
                    cashbox=cashbox,
                    transaction_type='deposit',
                    amount=instance.total_amount,
                    date=instance.date,
                    description=f'مبيعات نقدية - فاتورة رقم {instance.invoice_number}',
                    created_by=instance.created_by
                )
                
                # تحديث رصيد الصندوق
                cashbox.balance += instance.total_amount
                cashbox.save(update_fields=['balance'])
                
                # تسجيل النشاط في سجل الأنشطة
                try:
                    AuditLog.objects.create(
                        user=instance.created_by,
                        action='create',
                        model_name='CashboxTransaction',
                        object_id=transaction.id,
                        object_repr=str(transaction),
                        description=_('تم إيداع %(amount)s في الصندوق %(cashbox)s من فاتورة مبيعات رقم %(invoice)s') % {
                            'amount': instance.total_amount,
                            'cashbox': cashbox.name,
                            'invoice': instance.invoice_number
                        },
                        ip_address='127.0.0.1'
                    )
                except Exception as log_error:
                    print(f"خطأ في تسجيل نشاط معاملة الصندوق: {log_error}")
                
                print(f"تم إيداع {instance.total_amount} في {cashbox.name} من فاتورة {instance.invoice_number}")
                
    except Exception as e:
        print(f"خطأ في إنشاء معاملة الصندوق لفاتورة {instance.invoice_number}: {e}")
        # لا نوقف عملية إنشاء الفاتورة في حالة فشل إنشاء معاملة الصندوق
        pass


@receiver(post_save, sender=SalesInvoice)
def create_payment_receipt_for_cash_sales(sender, instance, created, **kwargs):
    """إنشاء سند قبض تلقائياً عند إنشاء فاتورة مبيعات نقدية"""
    # 🔧 تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        from receipts.models import PaymentReceipt
        from core.models import DocumentSequence
        from core.models import AuditLog
        
        # التحقق من أن الفاتورة جديدة ونقدية
        if created and instance.payment_type == 'cash' and instance.total_amount > 0:
            # توليد رقم السند
            sequence = DocumentSequence.objects.get_or_create(
                document_type='payment_receipt',
                defaults={'current_number': 0}
            )[0]
            sequence.current_number += 1
            sequence.save()
            receipt_number = f"PR{sequence.current_number:06d}"
            
            # إنشاء سند القبض
            receipt = PaymentReceipt.objects.create(
                receipt_number=receipt_number,
                date=instance.date,
                customer=instance.customer,  # حتى لو كان عميل نقدي
                payment_type='cash',
                amount=instance.total_amount,
                cashbox=instance.cashbox,
                created_by=instance.created_by
            )
            
            # تسجيل النشاط في سجل الأنشطة
            try:
                AuditLog.objects.create(
                    user=instance.created_by,
                    action='create',
                    model_name='PaymentReceipt',
                    object_id=receipt.id,
                    object_repr=str(receipt),
                    description=_('تم إنشاء سند قبض تلقائياً رقم %(receipt)s لفاتورة المبيعات النقدية %(invoice)s') % {
                        'receipt': receipt_number,
                        'invoice': instance.invoice_number
                    },
                    ip_address='127.0.0.1'
                )
            except Exception as log_error:
                print(f"خطأ في تسجيل نشاط إنشاء سند القبض: {log_error}")
            
            print(f"تم إنشاء سند قبض {receipt_number} لفاتورة المبيعات النقدية {instance.invoice_number}")
            
    except Exception as e:
        print(f"خطأ في إنشاء سند القبض لفاتورة {instance.invoice_number}: {e}")
        # لا نوقف عملية إنشاء الفاتورة في حالة فشل إنشاء سند القبض
        pass


@receiver(post_save, sender=SalesInvoice)
def update_cashbox_transaction_on_invoice_change(sender, instance, created, **kwargs):
    """تحديث معاملة الصندوق عند تعديل الفاتورة"""
    # 🔧 تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        from cashboxes.models import CashboxTransaction
        
        # إذا لم تكن الفاتورة جديدة وكانت نقدية
        if not created and instance.payment_type == 'cash':
            # البحث عن المعاملة المرتبطة بالفاتورة: نطابق وصف المعاملة الذي يحتوي رقم الفاتورة
            try:
                transaction = CashboxTransaction.objects.filter(
                    transaction_type='deposit',
                    description__icontains=str(instance.invoice_number)
                ).first()
            except Exception:
                transaction = None
            
            if transaction:
                # حساب الفرق في المبلغ
                amount_difference = instance.total_amount - transaction.amount
                
                if amount_difference != 0:
                    # تحديث مبلغ المعاملة
                    transaction.amount = instance.total_amount
                    transaction.description = f'مبيعات نقدية - فاتورة رقم {instance.invoice_number} (محدثة)'
                    transaction.save()
                    
                    # تحديث رصيد الصندوق
                    if transaction.cashbox:
                        transaction.cashbox.balance += amount_difference
                        transaction.cashbox.save(update_fields=['balance'])
                        
                        print(f"تم تحديث معاملة الصندوق للفاتورة {instance.invoice_number}")
                        
    except Exception as e:
        print(f"خطأ في تحديث معاملة الصندوق للفاتورة {instance.invoice_number}: {e}")
        pass


@receiver(post_save, sender=SalesInvoice)
def update_inventory_on_sales_invoice(sender, instance, created, **kwargs):
    """تحديث المخزون عند إنشاء أو تعديل فاتورة مبيعات"""
    # 🔧 تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        from inventory.models import InventoryMovement, Warehouse
        
        # تحديد المستودع
        warehouse = instance.warehouse
        if not warehouse:
            warehouse = Warehouse.get_default_warehouse()
            if warehouse:
                instance.warehouse = warehouse
                instance.save(update_fields=['warehouse'])
        
        if not warehouse:
            print(f"لا يوجد مستودع افتراضي لفاتورة المبيعات {instance.invoice_number}")
            return
        
        # للفواتير الجديدة، إنشاء حركات مخزون صادرة
        if created:
            for item in instance.items.all():
                if item.product.product_type == 'physical':
                    InventoryMovement.objects.create(
                        date=instance.date,
                        product=item.product,
                        warehouse=warehouse,
                        movement_type='out',
                        reference_type='sales_invoice',
                        reference_id=instance.id,
                        quantity=item.quantity,
                        unit_cost=item.product.calculate_weighted_average_cost(),
                        notes=f'مبيعات - فاتورة رقم {instance.invoice_number}',
                        created_by=instance.created_by
                    )
        else:
            # للتعديلات، حذف الحركات القديمة وإنشاء جديدة
            InventoryMovement.objects.filter(
                reference_type='sales_invoice',
                reference_id=instance.id
            ).delete()
            
            for item in instance.items.all():
                if item.product.product_type == 'physical':
                    InventoryMovement.objects.create(
                        date=instance.date,
                        product=item.product,
                        warehouse=warehouse,
                        movement_type='out',
                        reference_type='sales_invoice',
                        reference_id=instance.id,
                        quantity=item.quantity,
                        unit_cost=item.product.calculate_weighted_average_cost(),
                        notes=f'مبيعات - فاتورة رقم {instance.invoice_number}',
                        created_by=instance.created_by
                    )
        
        print(f"تم تحديث المخزون لفاتورة المبيعات {instance.invoice_number}")
        
        # إنشاء قيد تكلفة البضاعة المباعة بعد تحديث المخزون
        if created:
            # انتظار لحظة للتأكد من حفظ حركات المخزون
            from time import sleep
            sleep(1.0)  # زيادة الوقت
            
            try:
                from journal.services import JournalService
                cogs_entry = JournalService.create_cogs_entry(instance, instance.created_by)
                if cogs_entry:
                    print(f"تم إنشاء قيد COGS {cogs_entry.entry_number} لفاتورة المبيعات {instance.invoice_number}")
                else:
                    print(f"لم يتم إنشاء قيد COGS لفاتورة المبيعات {instance.invoice_number}")
            except Exception as cogs_error:
                print(f"خطأ في إنشاء قيد COGS: {cogs_error}")
        
    except Exception as e:
        print(f"خطأ في تحديث المخزون لفاتورة المبيعات {instance.invoice_number}: {e}")
        pass


@receiver(post_save, sender=SalesReturn)
def create_sales_return_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي لمردود المبيعات"""
    # 🔧 تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        if created:
            from journal.services import JournalService
            entry = JournalService.create_sales_return_entry(instance, instance.created_by)
            if entry:
                print(f"تم إنشاء قيد {entry.entry_number} لمردود المبيعات {instance.return_number}")
    except Exception as e:
        print(f"خطأ في إنشاء قيد مردود المبيعات {instance.return_number}: {e}")
        pass


@receiver(post_save, sender=SalesReturn)
def update_inventory_on_sales_return(sender, instance, created, **kwargs):
    """تحديث المخزون عند إنشاء مردود المبيعات"""
    # 🔧 تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        from inventory.models import InventoryMovement
        
        warehouse = instance.original_invoice.warehouse
        if not warehouse:
            from inventory.models import Warehouse
            warehouse = Warehouse.get_default_warehouse()
        
        if not warehouse:
            print(f"لا يوجد مستودع لمردود المبيعات {instance.return_number}")
            return
        
        if created:
            for item in instance.items.all():
                if item.product.product_type == 'physical':
                    InventoryMovement.objects.create(
                        date=instance.date,
                        product=item.product,
                        warehouse=warehouse,
                        movement_type='in',
                        reference_type='sales_return',
                        reference_id=instance.id,
                        quantity=item.returned_quantity,
                        unit_cost=item.unit_price,
                        notes=f'مردود مبيعات - رقم {instance.return_number}',
                        created_by=instance.created_by
                    )
        else:
            # للتعديلات، حذف الحركات القديمة وإنشاء جديدة
            InventoryMovement.objects.filter(
                reference_type='sales_return',
                reference_id=instance.id
            ).delete()
            
            for item in instance.items.all():
                if item.product.product_type == 'physical':
                    InventoryMovement.objects.create(
                        date=instance.date,
                        product=item.product,
                        warehouse=warehouse,
                        movement_type='in',
                        reference_type='sales_return',
                        reference_id=instance.id,
                        quantity=item.returned_quantity,
                        unit_cost=item.unit_price,
                        notes=f'مردود مبيعات - رقم {instance.return_number}',
                        created_by=instance.created_by
                    )
        
        print(f"تم تحديث المخزون لمردود المبيعات {instance.return_number}")
        
    except Exception as e:
        print(f"خطأ في تحديث المخزون لمردود المبيعات {instance.return_number}: {e}")
        pass


@receiver(post_save, sender=SalesCreditNote)
def create_sales_credit_note_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي لإشعار الدائن"""
    # 🔧 تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        if created:
            from journal.services import JournalService
            entry = JournalService.create_sales_credit_note_entry(instance, instance.created_by)
            if entry:
                print(f"تم إنشاء قيد {entry.entry_number} لإشعار الدائن {instance.note_number}")
    except Exception as e:
        print(f"خطأ في إنشاء قيد إشعار الدائن {instance.note_number}: {e}")
        pass


@receiver(post_save, sender=SalesInvoiceItem)
def update_inventory_on_sales_invoice_item(sender, instance, created, **kwargs):
    """تحديث المخزون عند إضافة/تعديل عنصر فاتورة مبيعات"""
    # 🔧 تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        from inventory.models import InventoryMovement, Warehouse

        invoice = instance.invoice
        warehouse = invoice.warehouse
        if not warehouse:
            warehouse = Warehouse.get_default_warehouse()
            if warehouse:
                invoice.warehouse = warehouse
                invoice.save(update_fields=['warehouse'])

        if not warehouse:
            print(f"لا يوجد مستودع افتراضي لفاتورة المبيعات {invoice.invoice_number}")
            return

        # حذف الحركات القديمة لهذا العنصر
        InventoryMovement.objects.filter(
            reference_type='sales_invoice',
            reference_id=invoice.id,
            product=instance.product
        ).delete()

        # إنشاء حركة مخزون صادرة
        if instance.product.product_type == 'physical':
            InventoryMovement.objects.create(
                date=invoice.date,
                product=instance.product,
                warehouse=warehouse,
                movement_type='out',
                reference_type='sales_invoice',
                reference_id=invoice.id,
                quantity=instance.quantity,
                unit_cost=instance.product.calculate_weighted_average_cost(),
                notes=f'مبيعات - فاتورة رقم {invoice.invoice_number}',
                created_by=invoice.created_by
            )

        print(f"تم تحديث المخزون لفاتورة المبيعات {invoice.invoice_number}")

    except Exception as e:
        print(f"خطأ في تحديث المخزون لفاتورة المبيعات {invoice.invoice_number}: {e}")
        pass


@receiver(post_save, sender=SalesInvoiceItem)
def create_cogs_entry_for_sales_invoice_item(sender, instance, created, **kwargs):
    """إنشاء قيد تكلفة البضاعة المباعة عند إضافة عنصر فاتورة مبيعات"""
    # 🔧 تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        if created and instance.product.product_type == 'physical':
            from time import sleep
            sleep(0.5)  # انتظار لحفظ حركات المخزون
            
            # التحقق من عدم وجود قيد COGS مسبقاً
            from journal.models import JournalEntry
            existing_cogs = JournalEntry.objects.filter(
                reference_type='sales_invoice_cogs',
                reference_id=instance.invoice.id
            ).exists()
            
            if not existing_cogs:
                from journal.services import JournalService
                cogs_entry = JournalService.create_cogs_entry(instance.invoice, instance.invoice.created_by)
                if cogs_entry:
                    print(f"تم إنشاء قيد COGS {cogs_entry.entry_number} لفاتورة المبيعات {instance.invoice.invoice_number}")
                else:
                    print(f"لم يتم إنشاء قيد COGS لفاتورة المبيعات {instance.invoice.invoice_number}")
    except Exception as e:
        print(f"خطأ في إنشاء قيد COGS لفاتورة المبيعات {instance.invoice.invoice_number}: {e}")
        pass

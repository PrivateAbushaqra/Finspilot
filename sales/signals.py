from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from .models import SalesInvoice, SalesReturn, SalesCreditNote, SalesInvoiceItem, SalesReturnItem, SalesInvoiceItem
from django.utils import timezone


def should_log_activity(user, action_type, content_type, object_id, description_prefix, minutes=1):
    """التحقق من عدم وجود سجل نشاط مشابه حديث"""
    from core.models import AuditLog
    recent_logs = AuditLog.objects.filter(
        user=user,
        action_type=action_type,
        content_type=content_type,
        object_id=object_id,
        timestamp__gte=timezone.now() - timezone.timedelta(minutes=minutes)
    ).filter(description__startswith=description_prefix)
    
    return not recent_logs.exists()


@receiver(post_save, sender=SalesInvoice)
def create_cashbox_transaction_for_sales(sender, instance, created, **kwargs):
    """إنشاء معاملة صندوق تلقائياً عند إنشاء أو تحديث فاتورة مبيعات نقدية"""
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
        
        # التحقق من أن الفاتورة نقدية ولديها مبلغ
        if instance.payment_type == 'cash' and instance.total_amount > 0:
            # التحقق من عدم وجود معاملة صندوق مسبقاً (لتجنب التكرار)
            existing_transaction = CashboxTransaction.objects.filter(
                description__contains=instance.invoice_number,
                amount=instance.total_amount
            ).first()
            
            # إنشاء المعاملة فقط إذا لم تكن موجودة
            if existing_transaction:
                return
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
                            description = _('تم إنشاء صندوق تلقائياً لمستخدم نقطة البيع: %(username)s - %(cashbox)s') % {
                                'username': instance.created_by.username,
                                'cashbox': str(cashbox)
                            }
                            if should_log_activity(instance.created_by, 'create', 'Cashbox', cashbox.id, 'تم إنشاء صندوق تلقائياً'):
                                AuditLog.objects.create(
                                    user=instance.created_by,
                                    action_type='create',
                                    content_type='Cashbox',
                                    object_id=cashbox.id,
                                    description=description,
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
            
            # ✅ إنشاء حركة الصندوق مباشرة للفاتورة النقدية
            # هذا يضمن ترصيد النقد فوراً عند إنشاء الفاتورة
            if cashbox:
                try:
                    CashboxTransaction.objects.create(
                        cashbox=cashbox,
                        transaction_type='deposit',
                        amount=instance.total_amount,
                        description=f'إيداع نقدي من فاتورة مبيعات رقم {instance.invoice_number}',
                        date=instance.date,
                        reference_type='sales_invoice',
                        reference_id=instance.id,
                        created_by=instance.created_by
                    )
                    
                    # تحديث رصيد الصندوق
                    cashbox.balance += instance.total_amount
                    cashbox.save(update_fields=['balance'])
                    
                    # تسجيل في سجل الأنشطة
                    description = _('تم إيداع %(amount)s في الصندوق %(cashbox)s من فاتورة مبيعات رقم %(invoice)s') % {
                        'amount': instance.total_amount,
                        'cashbox': cashbox.name,
                        'invoice': instance.invoice_number
                    }
                    if should_log_activity(instance.created_by, 'create', 'CashboxTransaction', None, f'تم إيداع نقدي من فاتورة {instance.invoice_number}'):
                        AuditLog.objects.create(
                            user=instance.created_by,
                            action_type='create',
                            content_type='CashboxTransaction',
                            object_id=None,
                            description=description,
                            ip_address='127.0.0.1'
                        )
                    
                    print(f"✅ تم إنشاء معاملة إيداع في الصندوق {cashbox.name} بقيمة {instance.total_amount}")
                    
                except Exception as transaction_error:
                    print(f"خطأ في إنشاء معاملة الصندوق: {transaction_error}")
            
            print(f"تم ربط فاتورة {instance.invoice_number} بالصندوق {cashbox.name if cashbox else 'غير محدد'}")
                
    except Exception as e:
        print(f"خطأ في معالجة الصندوق لفاتورة {instance.invoice_number}: {e}")
        # لا نوقف عملية إنشاء الفاتورة في حالة فشل إنشاء معاملة الصندوق
        pass


@receiver(pre_delete, sender=SalesInvoice)
def delete_cashbox_transaction_for_sales(sender, instance, **kwargs):
    """حذف معاملة الصندوق وتحديث الرصيد عند حذف فاتورة مبيعات نقدية"""
    # 🔧 تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        from cashboxes.models import CashboxTransaction
        
        # التحقق من أن الفاتورة نقدية ولها صندوق
        if instance.payment_type == 'cash' and instance.cashbox and instance.total_amount > 0:
            # البحث عن معاملة الصندوق
            transactions = CashboxTransaction.objects.filter(
                cashbox=instance.cashbox,
                transaction_type='deposit',
                amount=instance.total_amount,
                description__contains=instance.invoice_number
            )
            
            for transaction in transactions:
                # خصم المبلغ من رصيد الصندوق
                instance.cashbox.balance -= transaction.amount
                instance.cashbox.save(update_fields=['balance'])
                
                # حذف المعاملة
                transaction.delete()
                
                print(f"تم خصم {transaction.amount} من {instance.cashbox.name} عند حذف فاتورة {instance.invoice_number}")
                
    except Exception as e:
        print(f"خطأ في حذف معاملة الصندوق لفاتورة {instance.invoice_number}: {e}")
        pass


# @receiver(post_save, sender=SalesInvoice)
# def create_payment_receipt_for_cash_sales(sender, instance, created, **kwargs):
#     """إنشاء سند قبض تلقائياً عند إنشاء فاتورة مبيعات نقدية - معطل"""
#     pass


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
                    # حساب متوسط التكلفة من حركات المخزون السابقة
                    from inventory.models import get_product_average_cost
                    avg_cost = get_product_average_cost(item.product, warehouse)
                    
                    InventoryMovement.objects.create(
                        date=instance.date,
                        product=item.product,
                        warehouse=warehouse,
                        movement_type='out',
                        reference_type='sales_invoice',
                        reference_id=instance.id,
                        quantity=item.quantity,
                        unit_cost=avg_cost,  # استخدام متوسط التكلفة
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
                    # حساب متوسط التكلفة من حركات المخزون السابقة
                    from inventory.models import get_product_average_cost
                    avg_cost = get_product_average_cost(item.product, warehouse)
                    
                    InventoryMovement.objects.create(
                        date=instance.date,
                        product=item.product,
                        warehouse=warehouse,
                        movement_type='out',
                        reference_type='sales_invoice',
                        reference_id=instance.id,
                        quantity=item.quantity,
                        unit_cost=avg_cost,  # استخدام متوسط التكلفة
                        notes=f'مبيعات - فاتورة رقم {instance.invoice_number}',
                        created_by=instance.created_by
                    )
        
        print(f"تم تحديث المخزون لفاتورة المبيعات {instance.invoice_number}")
        
        # ملاحظة: قيد COGS يتم إنشاؤه من views.py بعد حفظ الفاتورة وعناصرها
        # لتجنب التكرار، لا نقوم بإنشائه هنا
        
    except Exception as e:
        print(f"خطأ في تحديث المخزون لفاتورة المبيعات {instance.invoice_number}: {e}")
        pass


@receiver(post_save, sender=SalesReturn)
def create_sales_return_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي لمردود المبيعات"""
    # 🔧 تم تعطيل هذه الإشارة لتجنب إنشاء قيد مكرر
    # القيد المحاسبي يتم إنشاؤه الآن من خلال الـ View فقط
    # sales/views.py -> SalesReturnCreateView -> create_sales_return_journal_entry()
    return
    
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
                    # حساب التكلفة الفعلية من حركة المخزون الأصلية للفاتورة
                    # استخدام متوسط التكلفة المرجح أو FIFO
                    unit_cost = item.product.cost_price
                    
                    # محاولة الحصول على التكلفة من حركة المخزون الأصلية
                    if instance.original_invoice:
                        original_movement = InventoryMovement.objects.filter(
                            reference_type='sales_invoice',
                            reference_id=instance.original_invoice.id,
                            product=item.product,
                            movement_type='out'
                        ).first()
                        
                        if original_movement and original_movement.unit_cost > 0:
                            unit_cost = original_movement.unit_cost
                        elif hasattr(item.product, 'calculate_weighted_average_cost'):
                            # استخدام المتوسط المرجح إذا كان متوفراً
                            weighted_cost = item.product.calculate_weighted_average_cost()
                            if weighted_cost > 0:
                                unit_cost = weighted_cost
                    
                    InventoryMovement.objects.create(
                        date=instance.date,
                        product=item.product,
                        warehouse=warehouse,
                        movement_type='in',
                        reference_type='sales_return',
                        reference_id=instance.id,
                        quantity=item.quantity,
                        unit_cost=unit_cost,
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
                    # حساب التكلفة الفعلية من حركة المخزون الأصلية للفاتورة
                    unit_cost = item.product.cost_price
                    
                    # محاولة الحصول على التكلفة من حركة المخزون الأصلية
                    if instance.original_invoice:
                        original_movement = InventoryMovement.objects.filter(
                            reference_type='sales_invoice',
                            reference_id=instance.original_invoice.id,
                            product=item.product,
                            movement_type='out'
                        ).first()
                        
                        if original_movement and original_movement.unit_cost > 0:
                            unit_cost = original_movement.unit_cost
                        elif hasattr(item.product, 'calculate_weighted_average_cost'):
                            # استخدام المتوسط المرجح إذا كان متوفراً
                            weighted_cost = item.product.calculate_weighted_average_cost()
                            if weighted_cost > 0:
                                unit_cost = weighted_cost
                    
                    InventoryMovement.objects.create(
                        date=instance.date,
                        product=item.product,
                        warehouse=warehouse,
                        movement_type='in',
                        reference_type='sales_return',
                        reference_id=instance.id,
                        quantity=item.quantity,
                        unit_cost=unit_cost,
                        notes=f'مردود مبيعات - رقم {instance.return_number}',
                        created_by=instance.created_by
                    )
        
        print(f"تم تحديث المخزون لمردود المبيعات {instance.return_number}")
        
    except Exception as e:
        print(f"خطأ في تحديث المخزون لمردود المبيعات {instance.return_number}: {e}")
        pass


@receiver(post_save, sender=SalesCreditNote)
def create_sales_credit_note_journal_entry(sender, instance, created, **kwargs):
    """إنشاء أو تحديث قيد محاسبي لإشعار الدائن"""
    # 🔧 تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    # 🔧 منع التنفيذ المتكرر
    if hasattr(instance, '_signal_processing'):
        return
    
    try:
        instance._signal_processing = True
        
        from journal.services import JournalService
        from journal.models import JournalEntry
        from accounts.models import AccountTransaction
        import uuid
        
        # التحقق من وجود قيد موجود
        existing_entry = JournalEntry.objects.filter(
            reference_type='credit_note',
            reference_id=instance.id
        ).first()
        
        if created or not existing_entry:
            # إنشاء قيد جديد
            entry = JournalService.create_sales_credit_note_entry(instance, instance.created_by)
            if entry:
                print(f"✅ تم إنشاء قيد {entry.entry_number} لإشعار الدائن {instance.note_number}")
        else:
            # تحديث قيد موجود
            # حذف القيد القديم أولاً
            JournalEntry.objects.filter(
                reference_type='credit_note',
                reference_id=instance.id
            ).delete()
            print(f"🗑️ تم حذف القيد القديم لإشعار الدائن {instance.note_number}")
            
            # إنشاء قيد جديد
            entry = JournalService.create_sales_credit_note_entry(instance, instance.created_by)
            if entry:
                print(f"✅ تم تحديث قيد {entry.entry_number} لإشعار الدائن {instance.note_number}")
                
        # إنشاء أو تحديث معاملة حساب العميل
        # حذف المعاملة القديمة إذا كانت موجودة
        existing_trans = AccountTransaction.objects.filter(
            reference_type='credit_note',
            reference_id=instance.id
        )
        
        if existing_trans.exists() and not created:
            existing_trans.delete()
            print(f"🗑️ تم حذف المعاملة القديمة لإشعار الدائن {instance.note_number}")
        
        # إنشاء معاملة جديدة
        transaction_number = f"CN-{uuid.uuid4().hex[:8].upper()}"
        AccountTransaction.objects.create(
            transaction_number=transaction_number,
            date=instance.date,
            customer_supplier=instance.customer,
            transaction_type='credit_note',
            direction='credit',  # دائن (تقليل المدينية من العميل)
            amount=instance.total_amount,
            reference_type='credit_note',
            reference_id=instance.id,
            description=f'إشعار دائن رقم {instance.note_number}',
            notes=instance.notes or '',
            created_by=instance.created_by
        )
        print(f"✅ تم إنشاء معاملة {transaction_number} لإشعار الدائن {instance.note_number}")
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء قيد إشعار الدائن {instance.note_number}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # إزالة الـ flag
        if hasattr(instance, '_signal_processing'):
            delattr(instance, '_signal_processing')


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
    """
    ملاحظة: تم تعطيل إنشاء قيد COGS من هنا لتجنب التكرار.
    قيد COGS يتم إنشاؤه الآن من views.py بعد حفظ الفاتورة وجميع عناصرها.
    هذا يضمن:
    1. إنشاء قيد COGS واحد فقط لكل فاتورة (متوافق مع IFRS)
    2. حساب التكلفة بشكل صحيح بعد حفظ جميع العناصر
    3. تجنب التكرار والقيود المتعددة
    """
    # 🔧 تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    # تم تعطيل إنشاء COGS من هنا
    pass


@receiver(pre_delete, sender=SalesCreditNote)
def delete_sales_credit_note_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي عند حذف إشعار الدائن"""
    try:
        from journal.models import JournalEntry
        from accounts.models import AccountTransaction
        
        # حذف القيد المحاسبي
        JournalEntry.objects.filter(
            reference_type='sales_credit_note',
            reference_id=instance.id
        ).delete()
        
        # حذف معاملات الحساب
        AccountTransaction.objects.filter(
            reference_type='sales_credit_note',
            reference_id=instance.id
        ).delete()
        
        print(f"✓ تم حذف القيد المحاسبي لإشعار الدائن {instance.note_number}")
    except Exception as e:
        print(f"✗ خطأ في حذف قيد إشعار الدائن: {e}")


@receiver(pre_delete, sender=SalesInvoice)
def delete_journal_entries_on_invoice_delete(sender, instance, **kwargs):
    """حذف القيود المحاسبية عند حذف فاتورة المبيعات"""
    try:
        from journal.models import JournalEntry
        from django.db.models import Q
        
        # البحث عن جميع القيود المرتبطة بالفاتورة (المبيعات + COGS)
        journal_entries = JournalEntry.objects.filter(
            Q(sales_invoice=instance) |
            Q(reference_type='sales_invoice', reference_id=instance.id) |
            Q(reference_type='sales_invoice_cogs', reference_id=instance.id)
        ).distinct()
        
        entry_count = journal_entries.count()
        if entry_count > 0:
            entry_numbers = ', '.join([entry.entry_number for entry in journal_entries])
            print(f"🗑️ حذف {entry_count} قيد محاسبي للفاتورة {instance.invoice_number}: {entry_numbers}")
            
            for journal_entry in journal_entries:
                journal_entry.delete()
        else:
            print(f"⚠️ لا توجد قيود محاسبية للفاتورة {instance.invoice_number}")
            
    except Exception as e:
        print(f"❌ خطأ في حذف القيود المحاسبية لفاتورة {instance.invoice_number}: {e}")
        import traceback
        traceback.print_exc()
        pass


@receiver(pre_delete, sender=SalesInvoice)
def delete_sales_invoice_returns_before_deletion(sender, instance, **kwargs):
    """حذف مردودات المبيعات المرتبطة قبل حذف فاتورة المبيعات"""
    try:
        # حذف جميع مردودات المبيعات المرتبطة بهذه الفاتورة
        related_returns = SalesReturn.objects.filter(original_invoice=instance)
        deleted_returns = related_returns.count()
        related_returns.delete()
        
        if deleted_returns > 0:
            print(f"✓ تم حذف {deleted_returns} مردود مبيعات مرتبط بفاتورة المبيعات {instance.invoice_number}")
    except Exception as e:
        print(f"✗ خطأ في حذف مردودات المبيعات المرتبطة بفاتورة {instance.invoice_number}: {e}")


@receiver(post_delete, sender=SalesInvoice)
def delete_sales_invoice_related_records(sender, instance, **kwargs):
    """حذف السجلات المرتبطة عند حذف فاتورة المبيعات"""
    try:
        from inventory.models import InventoryMovement
        from journal.models import JournalEntry
        from accounts.models import AccountTransaction
        from django.db.models import Q
        
        # حذف حركات المخزون
        inventory_movements = InventoryMovement.objects.filter(
            reference_type='sales_invoice',
            reference_id=instance.id
        )
        deleted_inventory = inventory_movements.count()
        inventory_movements.delete()
        
        # حذف جميع القيود المحاسبية (المبيعات + COGS)
        journal_entries = JournalEntry.objects.filter(
            Q(sales_invoice=instance) |
            Q(reference_type='sales_invoice', reference_id=instance.id) |
            Q(reference_type='sales_invoice_cogs', reference_id=instance.id)
        ).distinct()
        deleted_journal = journal_entries.count()
        if deleted_journal > 0:
            print(f"🗑️ [post_delete] حذف {deleted_journal} قيد محاسبي")
        journal_entries.delete()
        
        # حذف معاملات الحساب
        account_transactions = AccountTransaction.objects.filter(
            reference_type='sales_invoice',
            reference_id=instance.id
        )
        deleted_transactions = account_transactions.count()
        account_transactions.delete()
        
        print(f"✓ تم حذف {deleted_inventory} حركة مخزون، {deleted_journal} قيد محاسبي، و {deleted_transactions} معاملة حساب لفاتورة المبيعات {instance.invoice_number}")
    except Exception as e:
        print(f"✗ خطأ في حذف السجلات المرتبطة بفاتورة المبيعات {instance.invoice_number}: {e}")
        import traceback
        traceback.print_exc()


@receiver(pre_delete, sender=SalesReturn)
def delete_journal_entries_on_return_delete(sender, instance, **kwargs):
    """حذف القيود المحاسبية عند حذف مردود المبيعات"""
    try:
        from journal.models import JournalEntry
        from django.db.models import Q
        
        # البحث عن جميع القيود المرتبطة بمردود المبيعات (المردود + COGS)
        journal_entries = JournalEntry.objects.filter(
            Q(sales_return=instance) |
            Q(reference_type='sales_return', reference_id=instance.id) |
            Q(reference_type='sales_return_cogs', reference_id=instance.id)
        ).distinct()
        
        deleted_count = journal_entries.count()
        if deleted_count > 0:
            print(f"🗑️ [pre_delete] حذف {deleted_count} قيد محاسبي لمردود {instance.return_number}")
        
        for journal_entry in journal_entries:
            print(f"  - حذف القيد {journal_entry.entry_number} ({journal_entry.reference_type})")
            journal_entry.delete()
            
    except Exception as e:
        print(f"خطأ في حذف القيود المحاسبية لمردود {instance.return_number}: {e}")
        pass


@receiver(post_delete, sender=SalesReturn)
def delete_sales_return_related_records(sender, instance, **kwargs):
    """حذف السجلات المرتبطة عند حذف مردود المبيعات"""
    try:
        from inventory.models import InventoryMovement
        from journal.models import JournalEntry
        from accounts.models import AccountTransaction
        from django.db.models import Q
        
        # حذف حركات المخزون
        inventory_movements = InventoryMovement.objects.filter(
            reference_type='sales_return',
            reference_id=instance.id
        )
        deleted_inventory = inventory_movements.count()
        inventory_movements.delete()
        
        # حذف جميع القيود المحاسبية (المردود + COGS)
        journal_entries = JournalEntry.objects.filter(
            Q(sales_return=instance) |
            Q(reference_type='sales_return', reference_id=instance.id) |
            Q(reference_type='sales_return_cogs', reference_id=instance.id)
        ).distinct()
        deleted_journal = journal_entries.count()
        if deleted_journal > 0:
            print(f"🗑️ [post_delete] حذف {deleted_journal} قيد محاسبي")
        journal_entries.delete()
        
        # حذف معاملات الحساب
        account_transactions = AccountTransaction.objects.filter(
            reference_type='sales_return',
            reference_id=instance.id
        )
        deleted_transactions = account_transactions.count()
        account_transactions.delete()
        
        print(f"✓ تم حذف {deleted_inventory} حركة مخزون، {deleted_journal} قيد محاسبي، و {deleted_transactions} معاملة حساب لمردود المبيعات {instance.return_number}")
    except Exception as e:
        print(f"✗ خطأ في حذف السجلات المرتبطة بمردود المبيعات {instance.return_number}: {e}")
        import traceback
        traceback.print_exc()


# =====================================================
# Signals لإنشاء القيود المحاسبية تلقائياً
# =====================================================

@receiver(post_save, sender=SalesInvoiceItem)
def create_journal_entry_for_sales_invoice(sender, instance, created, **kwargs):
    """إنشاء القيد المحاسبي تلقائياً عند إضافة عنصر فاتورة"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        from journal.models import JournalEntry
        from journal.services import JournalService
        from django.db import transaction as db_transaction
        
        # الحصول على الفاتورة
        invoice = instance.invoice
        
        # التحقق من وجود عناصر ومبلغ
        if invoice.items.count() > 0 and invoice.total_amount > 0:
            # حذف القيد القديم إذا كان موجوداً
            existing_entry = JournalEntry.objects.filter(sales_invoice=invoice).first()
            if existing_entry:
                existing_entry.delete()
            
            # إنشاء قيد جديد
            def _create_entry():
                JournalService.create_sales_invoice_entry(invoice, invoice.created_by)
            
            db_transaction.on_commit(_create_entry)
    except Exception as e:
        print(f"خطأ في إنشاء القيد المحاسبي لفاتورة المبيعات: {e}")


@receiver(post_save, sender=SalesReturnItem)
def create_journal_entry_for_sales_return(sender, instance, created, **kwargs):
    """إنشاء القيد المحاسبي تلقائياً عند إضافة عنصر مردود"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        from journal.models import JournalEntry
        from journal.services import JournalService
        from django.db import transaction as db_transaction
        
        # الحصول على المردود
        sales_return = instance.return_invoice
        
        # التحقق من وجود عناصر ومبلغ
        if sales_return.items.count() > 0 and sales_return.total_amount > 0:
            # حذف القيد القديم إذا كان موجوداً
            existing_entry = JournalEntry.objects.filter(
                reference_type='sales_return',
                reference_id=sales_return.id
            ).first()
            if existing_entry:
                existing_entry.delete()
            
            # إنشاء قيد جديد
            def _create_entry():
                JournalService.create_sales_return_entry(sales_return, sales_return.created_by)
            
            db_transaction.on_commit(_create_entry)
    except Exception as e:
        print(f"خطأ في إنشاء القيد المحاسبي لمردود المبيعات: {e}")


@receiver(post_save, sender=SalesCreditNote)
def create_journal_entry_for_credit_note(sender, instance, created, **kwargs):
    """إنشاء القيد المحاسبي تلقائياً عند إنشاء أو تحديث إشعار دائن"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        from journal.models import JournalEntry, Account
        from journal.services import JournalService
        from accounts.models import AccountTransaction
        from django.db import transaction as db_transaction
        import uuid
        
        # حذف القيود القديمة إذا كانت موجودة
        JournalEntry.objects.filter(
            reference_type='credit_note',
            reference_id=instance.id
        ).delete()
        
        AccountTransaction.objects.filter(
            reference_type='credit_note',
            reference_id=instance.id
        ).delete()
        
        def _create_entry_and_transaction():
            # إنشاء القيد المحاسبي
            lines_data = []
            
            # حساب المبيعات (مدين - تخفيض المبيعات)
            sales_account = Account.objects.filter(code='4000').first()
            if not sales_account:
                sales_account = Account.objects.create(
                    code='4000',
                    name='إيرادات المبيعات',
                    account_type='revenue',
                    description='حساب إيرادات المبيعات'
                )
            
            lines_data.append({
                'account_id': sales_account.id,
                'debit': float(instance.total_amount),
                'credit': 0,
                'description': f'إشعار دائن رقم {instance.note_number}'
            })
            
            # حساب العميل (دائن - تخفيض الذمم المدينة)
            customer_account = JournalService.get_or_create_customer_account(instance.customer)
            lines_data.append({
                'account_id': customer_account.id,
                'debit': 0,
                'credit': float(instance.total_amount),
                'description': f'إشعار دائن رقم {instance.note_number}'
            })
            
            # إنشاء القيد
            JournalService.create_journal_entry(
                entry_date=instance.date,
                reference_type='credit_note',
                description=f'إشعار دائن رقم {instance.note_number} - {instance.customer.name}',
                lines_data=lines_data,
                reference_id=instance.id,
                user=instance.created_by
            )
            
            # إنشاء حركة حساب العميل
            transaction_number = f"CN-{uuid.uuid4().hex[:8].upper()}"
            AccountTransaction.objects.create(
                transaction_number=transaction_number,
                date=instance.date,
                customer_supplier=instance.customer,
                transaction_type='credit_note',
                direction='credit',  # دائن (تخفيض ذمة العميل)
                amount=instance.total_amount,
                reference_type='credit_note',
                reference_id=instance.id,
                description=f'إشعار دائن رقم {instance.note_number}',
                notes=instance.notes or '',
                created_by=instance.created_by
            )
        
        db_transaction.on_commit(_create_entry_and_transaction)
    except Exception as e:
        print(f"خطأ في إنشاء قيد إشعار الدائن {instance.note_number}: {e}")


@receiver(pre_delete, sender=SalesCreditNote)
def delete_credit_note_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي عند حذف إشعار الدائن"""
    try:
        from journal.models import JournalEntry
        from accounts.models import AccountTransaction
        
        # حذف القيد المحاسبي
        deleted_entries = JournalEntry.objects.filter(
            reference_type='credit_note',
            reference_id=instance.id
        ).delete()
        
        # حذف معاملات الحساب
        deleted_trans = AccountTransaction.objects.filter(
            reference_type='credit_note',
            reference_id=instance.id
        ).delete()
        
        print(f"✓ تم حذف القيد المحاسبي لإشعار الدائن {instance.note_number}")
    except Exception as e:
        print(f"✗ خطأ في حذف قيد إشعار الدائن: {e}")

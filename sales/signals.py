from django.db.models import Q
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from .models import SalesInvoice, SalesReturn, SalesCreditNote, SalesInvoiceItem, SalesReturnItem, SalesInvoiceItem
from django.utils import timezone

POS_CASHBOX_NAME = 'Cash POS Box'
POS_CARD_CASHBOX_NAME = 'Card POS Box'
OLD_CARD_CASHBOX_SUFFIX = ' - card'


def find_pos_cashbox_for_user(user, payment_method):
    """Return the POS cashbox or card cashbox based on exact naming convention."""
    from cashboxes.models import Cashbox
    
    # الأسماء الموحدة والمعتمدة لنظام FinsPilot POS Pro
    target_cash_name = f"{user.username} - Cash"
    target_card_name = f"{user.username} - Card"

    if payment_method == 'card':
        return Cashbox.objects.filter(
            responsible_user=user,
            is_active=True,
            name__iexact=target_card_name
        ).first()

    return Cashbox.objects.filter(
        responsible_user=user,
        is_active=True,
        name__iexact=target_cash_name
    ).first()

    return Cashbox.objects.filter(
        responsible_user=user,
        is_active=True,
        name=target_cash_name
    ).first()


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
    # 🔧 حماية من الحلقة المفرغة والتكرار
    if getattr(instance, '_bypass_signals', False):
        return

    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        from cashboxes.models import CashboxTransaction
        from core.models import AuditLog
        
        #if instance.payment_type == 'cash' and instance.total_amount > 0:
        # ✅ السماح للكاش والبطاقة بالدخول لمعالجة الصناديق وبناء القيد المحاسبي
        if instance.total_amount > 0 and (instance.payment_type == 'cash' or getattr(instance, 'pos_payment_method', None) == 'card'):
            existing_transaction = CashboxTransaction.objects.filter(
                reference_type='sales_invoice',
                reference_id=instance.id,
                transaction_type='deposit'
            ).first()
            
            # إذا كانت طريقة الدفع في POS بطاقة، تأكد من استخدام صندوق البطاقة الصحيح
            if getattr(instance, 'pos_payment_method', None) == 'card' and instance.created_by:
                card_cashbox = find_pos_cashbox_for_user(instance.created_by, 'card')
                if card_cashbox and (not instance.cashbox or instance.cashbox.id != card_cashbox.id):
                    instance.cashbox = card_cashbox
                    # حفظ آمن بدون إعادة إطلاق السيجنالات
                    instance._bypass_signals = True
                    instance.save(update_fields=['cashbox'])
                    instance._bypass_signals = False
            
            # إذا لم تكن الفاتورة مرتبطة بصندوق، نحدد الصندوق الافتراضي لها
            if not instance.cashbox:
                from cashboxes.models import Cashbox
                cashbox = None
                
                # حاول الحصول على صندوق الكاش للمستخدم من POS
                if instance.created_by and instance.created_by.has_perm('users.can_access_pos'):
                    # استخدم الدالة الموحدة للبحث عن الصناديق
                    payment_method = getattr(instance, 'pos_payment_method', 'cash')
                    cashbox = find_pos_cashbox_for_user(instance.created_by, payment_method)
                
                if not cashbox:
                    # إذا لم تجد صندوق POS، ابحث عن الصندوق الرئيسي
                    cashbox = Cashbox.objects.filter(name__icontains='رئيسي', is_active=True).first()
                
                if cashbox:
                    instance.cashbox = cashbox
                    # حفظ آمن بدون إعادة إطلاق السيجنالات
                    instance._bypass_signals = True
                    instance.save(update_fields=['cashbox'])
                    instance._bypass_signals = False

            # تحذير: لا تضع return هنا للبطاقة لكي تسمح لباقي السيجنالات والـ views بإنشاء القيد!
            #if existing_transaction:
            #    return

            # التحقق من وجود حركة صندوق مسبقاً لمنع التكرار
            if existing_transaction:
                # إذا كانت طريقة الدفع بطاقة، لا تخرج بـ return! دع السيجنال يكمل طريقه لبناء القيد المحاسبي
                if getattr(instance, 'pos_payment_method', None) == 'card':
                    print(f"فاتورة بطاقة {instance.invoice_number} - تخطي الـ return لإنشاء القيد المحاسبي")
                else:
                    # إذا كانت كاش عادي، اخرج لمنع تكرار الحركة
                    return

            # تم تعطيل المعاملة المباشرة لأنها تعتمد على القيد المحاسبي الموزون
            print(f"تمت معالجة صناديق فاتورة {instance.invoice_number} بنجاح")
                
    except Exception as e:
        print(f"خطأ في معالجة الصندوق لفاتورة {instance.invoice_number}: {e}")
        pass
        """-----------------End of new------------------"""


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



@receiver(post_save, sender=SalesInvoice)
def update_cashbox_transaction_on_invoice_change(sender, instance, created, **kwargs):
    """تحديث معاملة الصندوق عند تعديل الفاتورة"""

# 🔧 حماية من الحلقة المفرغة: إذا كان هذا العلم موجوداً، توقف فوراً
    if getattr(instance, '_bypass_signals', False):
        return

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
            transaction = None
            try:
                transaction = CashboxTransaction.objects.filter(
                    transaction_type='deposit',
                    reference_type='sales_invoice',
                    reference_id=instance.id
                ).first()
            except Exception:
                transaction = None
            
            if transaction:
                # إذا كانت الفاتورة بطاقة POS، تأكد من أن حركة الصندوق مرتبطة بالصندوق الصحيح
                if getattr(instance, 'pos_payment_method', None) == 'card' and instance.created_by:
                    card_cashbox = find_pos_cashbox_for_user(instance.created_by, 'card')
                    if card_cashbox and transaction.cashbox_id != card_cashbox.id:
                        transaction.cashbox = card_cashbox
                
                # حساب الفرق في المبلغ
                amount_difference = instance.total_amount - transaction.amount
                
                if amount_difference != 0:
                    transaction.amount = instance.total_amount
                    transaction.description = f'مبيعات نقدية - فاتورة رقم {instance.invoice_number} (محدثة)'
                    transaction.save()
                    
                    # لا حاجة لتعديل الرصيد يدوياً إذا كان CashboxTransactionSignal يقوم بذلك تلقائياً
                    print(f"تم تحديث معاملة الصندوق للفاتورة {instance.invoice_number}")
                        
    except Exception as e:
        print(f"خطأ في تحديث معاملة الصندوق للفاتورة {instance.invoice_number}: {e}")
        pass


@receiver(post_save, sender=SalesInvoice)
def create_account_transaction_for_sales_invoice(sender, instance, created, **kwargs):
    """إنشاء أو تحديث حركة حساب للعميل عند إنشاء أو تعديل فاتورة مبيعات آجلة"""

# 🔧 حماية من الحلقة المفرغة: إذا كان هذا العلم موجوداً، توقف فوراً
    if getattr(instance, '_bypass_signals', False):
        return

    # 🔧 تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        from accounts.models import AccountTransaction
        import uuid
        
        # إذا كانت طريقة الدفع ليست نقداً ولديها عميل، نسجل حركة في حساب العميل
        if instance.payment_type != 'cash' and instance.customer and instance.total_amount > 0:
            # البحث عن حركة موجودة
            existing_transaction = AccountTransaction.objects.filter(
                reference_type='sales_invoice',
                reference_id=instance.id
            ).first()
            
            if existing_transaction:
                # تحديث المعاملة الموجودة إذا تغير المبلغ
                if existing_transaction.amount != instance.total_amount:
                    old_amount = existing_transaction.amount
                    existing_transaction.amount = instance.total_amount
                    existing_transaction.date = instance.date
                    existing_transaction.description = f'مبيعات - فاتورة رقم {instance.invoice_number}'
                    existing_transaction.save()
                    print(f"✅ تم تحديث حركة الحساب {existing_transaction.transaction_number} للفاتورة {instance.invoice_number} من {old_amount} إلى {instance.total_amount}")
                return  # الحركة موجودة وتم تحديثها أو لا تحتاج تحديث
            
            # إنشاء حركة جديدة للفواتير الجديدة فقط
            if created:
                # توليد رقم الحركة
                transaction_number = f"SALE-{uuid.uuid4().hex[:8].upper()}"
                
                # إنشاء حركة مدينة للعميل (زيادة الذمم المدينة)
                AccountTransaction.objects.create(
                    transaction_number=transaction_number,
                    date=instance.date,
                    customer_supplier=instance.customer,
                    transaction_type='sales_invoice',
                    direction='debit',
                    amount=instance.total_amount,
                    reference_type='sales_invoice',
                    reference_id=instance.id,
                    description=f'مبيعات - فاتورة رقم {instance.invoice_number}',
                    created_by=instance.created_by
                )
                
                print(f"✅ تم إنشاء حركة حساب {transaction_number} للفاتورة {instance.invoice_number}")
            
    except ImportError:
        # في حالة عدم وجود نموذج الحسابات
        pass
    except Exception as e:
        print(f"خطأ في إنشاء/تحديث حركة الحساب للفاتورة {instance.invoice_number}: {e}")
        # لا نوقف العملية في حالة فشل تسجيل الحركة المالية
        pass

@receiver(post_save, sender=SalesInvoice)
def update_inventory_on_sales_invoice(sender, instance, created, **kwargs):
    """تحديث المخزون عند إنشاء أو تعديل فاتورة مبيعات"""
    # 🔧 حماية من الحلقة المفرغة والتكرار
    if getattr(instance, '_bypass_signals', False):
        return

    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    try:
        from inventory.models import InventoryMovement, Warehouse
        
        # تحديد المستودع الافتراضي إذا لم يوجد
        if not instance.warehouse:
            warehouse = Warehouse.get_default_warehouse()
            if warehouse:
                instance.warehouse = warehouse
                # حفظ آمن بدون إعادة إطلاق السيجنالات
                instance._bypass_signals = True
                instance.save(update_fields=['warehouse'])
                instance._bypass_signals = False
        
        warehouse = instance.warehouse
        if not warehouse:
            return
        
        # تنفيذ حركات المخزون (كودك الأصلي تماماً بدون أي تعديل)
        if created:
            for item in instance.items.all():
                if item.product.product_type == 'physical':
                    from inventory.models import get_product_fifo_cost
                    fifo_cost = get_product_fifo_cost(item.product, warehouse, item.quantity, instance.date)
                    
                    InventoryMovement.objects.create(
                        date=instance.date, product=item.product, warehouse=warehouse,
                        movement_type='out', reference_type='sales_invoice', reference_id=instance.id,
                        quantity=item.quantity, unit_cost=fifo_cost, notes=f'مبيعات - فاتورة رقم {instance.invoice_number}',
                        created_by=instance.created_by
                    )
        else:
            InventoryMovement.objects.filter(reference_type='sales_invoice', reference_id=instance.id).delete()
            for item in instance.items.all():
                if item.product.product_type == 'physical':
                    from inventory.models import get_product_fifo_cost
                    fifo_cost = get_product_fifo_cost(item.product, warehouse, item.quantity, instance.date)
                    
                    InventoryMovement.objects.create(
                        date=instance.date, product=item.product, warehouse=warehouse,
                        movement_type='out', reference_type='sales_invoice', reference_id=instance.id,
                        quantity=item.quantity, unit_cost=fifo_cost, notes=f'مبيعات - فاتورة رقم {instance.invoice_number}',
                        created_by=instance.created_by
                    )
        
        print(f"تم تحديث المخزون لفاتورة المبيعات {instance.invoice_number}")
        
    except Exception as e:
        print(f"خطأ في تحديث المخزون لفاتورة المبيعات {instance.invoice_number}: {e}")
        pass
        """----end of new----"""


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
                    # حساب التكلفة باستخدام FIFO
                    from inventory.models import get_product_fifo_cost
                    fifo_cost = get_product_fifo_cost(item.product, warehouse, item.quantity, instance.date)
                    
                    # محاولة الحصول على التكلفة من حركة المخزون الأصلية
                    if instance.original_invoice:
                        original_movement = InventoryMovement.objects.filter(
                            reference_type='sales_invoice',
                            reference_id=instance.original_invoice.id,
                            product=item.product,
                            movement_type='out'
                        ).first()
                        
                        if original_movement and original_movement.unit_cost > 0:
                            fifo_cost = original_movement.unit_cost
                    
                    InventoryMovement.objects.create(
                        date=instance.date,
                        product=item.product,
                        warehouse=warehouse,
                        movement_type='in',
                        reference_type='sales_return',
                        reference_id=instance.id,
                        quantity=item.quantity,
                        unit_cost=fifo_cost,
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
                    # حساب التكلفة باستخدام FIFO من تاريخ المردود
                    # مردود المبيعات يُعيد البضاعة للمخزون بتكلفة FIFO
                    from inventory.models import get_product_fifo_cost
                    fifo_cost = get_product_fifo_cost(item.product, warehouse, item.quantity, instance.date)
                    
                    # إذا كانت هناك حركة أصلية، يمكن استخدامها كمرجع
                    if instance.original_invoice:
                        original_movement = InventoryMovement.objects.filter(
                            reference_type='sales_invoice',
                            reference_id=instance.original_invoice.id,
                            product=item.product,
                            movement_type='out'
                        ).first()
                        
                        # استخدام تكلفة الحركة الأصلية إذا كانت موجودة ومعقولة
                        if original_movement and original_movement.unit_cost > 0:
                            fifo_cost = original_movement.unit_cost
                    
                    InventoryMovement.objects.create(
                        date=instance.date,
                        product=item.product,
                        warehouse=warehouse,
                        movement_type='in',
                        reference_type='sales_return',
                        reference_id=instance.id,
                        quantity=item.quantity,
                        unit_cost=fifo_cost,  # استخدام FIFO أو تكلفة الحركة الأصلية
                        notes=f'مردود مبيعات - رقم {instance.return_number}',
                        created_by=instance.created_by
                    )
        
        print(f"تم تحديث المخزون لمردود المبيعات {instance.return_number}")
        
    except Exception as e:
        print(f"خطأ في تحديث المخزون لمردود المبيعات {instance.return_number}: {e}")
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
        
        # حذف القيد المحاسبي (استخدام نفس reference_type المستخدم عند الإنشاء)
        JournalEntry.objects.filter(
            reference_type='credit_note',
            reference_id=instance.id
        ).delete()
        
        # حذف معاملات الحساب
        AccountTransaction.objects.filter(
            reference_type='credit_note',
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
            print(f"⚠️ {_('There are no accounting vouchers for the invoice.')}: {instance.invoice_number}")
            
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
        from accounts.services import recalculate_customer_supplier_balance
        from django.db.models import Q
        
        # حذف حركات المخزون
        inventory_movements = InventoryMovement.objects.filter(
            reference_type='sales_invoice',
            reference_id=instance.id
        )
        deleted_inventory = inventory_movements.count()
        inventory_movements.delete()
        
        # حذف جميع القيود المحاسبية (المبيعات + COGS)
        # لا نستخدم .distinct() قبل الحذف - نحذف كل مجموعة على حدة
        journal_entries_count = 0
        
        # حذف القيود المرتبطة بالفاتورة مباشرة
        je1 = JournalEntry.objects.filter(sales_invoice=instance)
        journal_entries_count += je1.count()
        je1.delete()
        
        # حذف القيود المرتبطة كمرجع sales_invoice
        je2 = JournalEntry.objects.filter(
            reference_type='sales_invoice',
            reference_id=instance.id
        )
        journal_entries_count += je2.count()
        je2.delete()
        
        # حذف القيود المرتبطة كمرجع sales_invoice_cogs
        je3 = JournalEntry.objects.filter(
            reference_type='sales_invoice_cogs',
            reference_id=instance.id
        )
        journal_entries_count += je3.count()
        je3.delete()
        
        if journal_entries_count > 0:
            print(f"🗑️ [post_delete] حذف {journal_entries_count} قيد محاسبي")
        
        # حذف معاملات الحساب وإعادة حساب رصيد العميل
        account_transactions = AccountTransaction.objects.filter(
            reference_type='sales_invoice',
            reference_id=instance.id
        )
        deleted_transactions = account_transactions.count()
        
        # جمع العملاء المتأثرين قبل الحذف
        affected_customers = set()
        for transaction in account_transactions:
            affected_customers.add(transaction.customer_supplier)
        
        # حذف المعاملات
        account_transactions.delete()
        
        # إعادة حساب رصيد جميع العملاء المتأثرين
        for customer in affected_customers:
            recalculate_customer_supplier_balance(customer)
            print(f"✅ تم إعادة حساب رصيد العميل {customer.name} بعد حذف الفاتورة")
        
        print(f"✓ تم حذف {deleted_inventory} حركة مخزون، {journal_entries_count} قيد محاسبي، و {deleted_transactions} معاملة حساب لفاتورة المبيعات {instance.invoice_number}")
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

@receiver(post_save, sender=SalesInvoice)
def create_journal_entry_for_sales_invoice(sender, instance, created, **kwargs):
    """إنشاء القيد المحاسبي تلقائياً عند حفظ فاتورة المبيعات"""

    # 🔧 حماية من الحلقة المفرغة: إذا كان هذا العلم موجوداً، توقف فوراً
    if getattr(instance, '_bypass_signals', False):
        return
    
    # 1. تجاهل أثناء استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    # 2. التحقق من وجود القيد مسبقاً لمنع التكرار (هذا هو الحل الجذري)
    try:
        from journal.models import JournalEntry
        from journal.services import JournalService
        from django.db import transaction as db_transaction
        
        # instance هنا هي الفاتورة (SalesInvoice) مباشرة
        invoice = instance
        
        # التحقق إذا كان القيد موجوداً بالفعل لهذه الفاتورة
        if JournalEntry.objects.filter(sales_invoice=invoice).exists():
            return # إذا وجد قيد، لا تفعل شيئاً

        # التحقق من وجود عناصر ومبلغ، وأن الفاتورة مرتبطة بصندوق
        #if invoice.items.count() > 0 and invoice.total_amount > 0 and invoice.cashbox:
        # التأكد من شمولية طرق الدفع (كاش أو بطاقة)
        if invoice.items.count() > 0 and invoice.total_amount > 0 and (invoice.cashbox or invoice.payment_type == 'card'):
            
            # إنشاء القيود الجديدة فقط إذا لم تكن موجودة
            def _create_entries():
                # قيد الإيراد (المبيعات)
                sales_entry = JournalService.create_sales_invoice_entry(invoice, invoice.created_by)
                if sales_entry:
                    print(f"✅ تم إنشاء قيد المبيعات {sales_entry.entry_number}")
                
                # قيد تكلفة البضاعة المباعة (COGS)
                cogs_entry = JournalService.create_cogs_entry(invoice, invoice.created_by)
                if cogs_entry:
                    print(f"✅ تم إنشاء قيد COGS {cogs_entry.entry_number}")
            
            db_transaction.on_commit(_create_entries)
            
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

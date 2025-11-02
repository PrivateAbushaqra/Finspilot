from django.db.models.signals import post_save, pre_save, pre_delete, post_delete
from django.dispatch import receiver
from .models import PurchaseInvoice, PurchaseInvoiceItem, PurchaseReturn, PurchaseReturnItem, PurchaseDebitNote
from django.db import transaction
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


@receiver(post_save, sender=PurchaseInvoice)
def create_journal_entry_for_purchase_invoice(sender, instance, created, **kwargs):
    """إنشاء القيد المحاسبي تلقائياً عند إنشاء أو تحديث فاتورة مشتريات"""
    def _create_entry():
        try:
            # 🔧 تعطيل السيجنال أثناء عملية استعادة النسخة الاحتياطية
            try:
                from backup.restore_context import is_restoring
                if is_restoring():
                    return
            except ImportError:
                pass
            
            from journal.models import JournalEntry
            from journal.services import JournalService
            
            # التحقق من وجود عناصر
            if instance.items.count() > 0:
                # إعادة حساب المجاميع من العناصر لضمان الدقة
                from decimal import Decimal, ROUND_HALF_UP
                subtotal = Decimal('0')
                tax_amount = Decimal('0')
                total_amount = Decimal('0')

                for item in instance.items.all():
                    subtotal += item.quantity * item.unit_price
                    tax_amount += item.tax_amount
                    total_amount += item.total_amount

                # تحديث المجاميع في الفاتورة
                instance.subtotal = subtotal.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                instance.tax_amount = tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                instance.total_amount = total_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                instance.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])
                
                existing_entry = JournalEntry.objects.filter(
                    purchase_invoice=instance
                ).first()
                
                # حذف القيد القديم إذا كان موجوداً
                if existing_entry:
                    existing_entry.delete()
                
                # إنشاء قيد جديد دائماً
                JournalService.create_purchase_invoice_entry(instance, instance.created_by)
        except Exception as e:
            print(f"خطأ في إنشاء القيد المحاسبي لفاتورة المشتريات {instance.invoice_number}: {e}")
    
    # استخدام transaction.on_commit لتجنب الاستدعاء المتكرر
    import threading
    if not hasattr(threading.current_thread(), '_purchase_signal_called'):
        threading.current_thread()._purchase_signal_called = set()
    
    signal_key = f"purchase_{instance.id}"
    if signal_key not in threading.current_thread()._purchase_signal_called:
        threading.current_thread()._purchase_signal_called.add(signal_key)
        transaction.on_commit(_create_entry)
    else:
        print(f"DEBUG: Skipping duplicate signal call for {instance.invoice_number}")


@receiver(post_save, sender=PurchaseInvoice)
def create_supplier_account_transaction(sender, instance, created, **kwargs):
    """إنشاء أو تحديث معاملة حساب المورد تلقائياً - متوافق مع IFRS"""
    # 🔧 تعطيل السيجنال أثناء عملية استعادة النسخة الاحتياطية
    try:
        try:
            from backup.restore_context import is_restoring
            if is_restoring():
                return
        except ImportError:
            pass
    except:
        pass
    
    if instance.payment_type == 'credit' and instance.items.count() > 0 and instance.total_amount > 0:
        try:
            from accounts.models import AccountTransaction
            import uuid
            
            # البحث عن معاملة موجودة
            existing_transaction = AccountTransaction.objects.filter(
                reference_type='purchase_invoice',
                reference_id=instance.id
            ).first()
            
            if existing_transaction:
                # تحديث المعاملة الموجودة (IFRS: تعديل التقديرات المحاسبية)
                existing_transaction.date = instance.date
                existing_transaction.customer_supplier = instance.supplier
                existing_transaction.amount = instance.total_amount
                existing_transaction.description = f'فاتورة مشتريات رقم {instance.invoice_number}'
                existing_transaction.notes = instance.notes or ''
                existing_transaction.save()
                print(f"✓ تم تحديث معاملة حساب المورد للفاتورة {instance.invoice_number}")
            else:
                # إنشاء معاملة جديدة
                transaction_number = f"PT-{uuid.uuid4().hex[:8].upper()}"
                AccountTransaction.objects.create(
                    transaction_number=transaction_number,
                    date=instance.date,
                    customer_supplier=instance.supplier,
                    transaction_type='purchase_invoice',
                    direction='credit',  # دائن (نحن ندين للمورد)
                    amount=instance.total_amount,
                    reference_type='purchase_invoice',
                    reference_id=instance.id,
                    description=f'فاتورة مشتريات رقم {instance.invoice_number}',
                    notes=instance.notes or '',
                    created_by=instance.created_by
                )
                print(f"✓ تم إنشاء معاملة حساب المورد للفاتورة {instance.invoice_number}")
        except Exception as e:
            print(f"✗ خطأ في إنشاء/تحديث معاملة حساب المورد للفاتورة {instance.invoice_number}: {e}")
            import traceback
            traceback.print_exc()
    
    # التعامل مع المدفوعات النقدية والشيكات والتحويلات
    if instance.payment_type == 'cash' and instance.payment_method and instance.items.count() > 0 and instance.total_amount > 0:
        try:
            from accounts.models import AccountTransaction
            from cashboxes.models import CashboxTransaction
            from banks.models import BankTransaction
            import uuid
            
            # البحث عن معاملة دفع موجودة
            existing_transaction = AccountTransaction.objects.filter(
                reference_type='purchase_payment',
                reference_id=instance.id
            ).first()
            
            if existing_transaction:
                # تحديث المعاملة الموجودة
                existing_transaction.date = instance.date
                existing_transaction.customer_supplier = instance.supplier
                existing_transaction.amount = instance.total_amount
                existing_transaction.description = f'دفع فاتورة مشتريات رقم {instance.invoice_number}'
                existing_transaction.notes = instance.notes or ''
                existing_transaction.save()
                print(f"✓ تم تحديث معاملة دفع المورد للفاتورة {instance.invoice_number}")
                
                # تحديث معاملات الصندوق/البنك
                if instance.payment_method == 'cash' and instance.cashbox:
                    cashbox_trans = CashboxTransaction.objects.filter(
                        description__icontains=f'فاتورة مشتريات رقم {instance.invoice_number}'
                    ).first()
                    if cashbox_trans:
                        cashbox_trans.cashbox = instance.cashbox
                        cashbox_trans.date = instance.date
                        cashbox_trans.amount = instance.total_amount
                        cashbox_trans.save()
                elif instance.payment_method in ['check', 'transfer'] and instance.bank_account:
                    bank_trans = BankTransaction.objects.filter(
                        description__icontains=f'فاتورة مشتريات رقم {instance.invoice_number}'
                    ).first()
                    if bank_trans:
                        bank_trans.bank = instance.bank_account
                        bank_trans.date = instance.date
                        bank_trans.amount = instance.total_amount
                        bank_trans.reference_number = instance.check_number if instance.payment_method == 'check' else f'PI-{instance.invoice_number}'
                        bank_trans.save()
            else:
                # إنشاء معاملات جديدة
                transaction_number = f"PP-{uuid.uuid4().hex[:8].upper()}"
                
                # إنشاء معاملة حساب المورد (مدين - نحن ندفع للمورد)
                AccountTransaction.objects.create(
                    transaction_number=transaction_number,
                    date=instance.date,
                    customer_supplier=instance.supplier,
                    transaction_type='purchase',
                    direction='debit',  # مدين (نحن ندفع للمورد)
                    amount=instance.total_amount,
                    reference_type='purchase_payment',
                    reference_id=instance.id,
                    description=f'دفع فاتورة مشتريات رقم {instance.invoice_number}',
                    notes=instance.notes or '',
                    created_by=instance.created_by
                )
                
                # إنشاء معاملة الصندوق أو الحساب البنكي حسب طريقة الدفع
                if instance.payment_method == 'cash' and instance.cashbox:
                    # معاملة الصندوق
                    CashboxTransaction.objects.create(
                        cashbox=instance.cashbox,
                        transaction_type='withdrawal',
                        date=instance.date,
                        amount=instance.total_amount,
                        description=f'دفع فاتورة مشتريات رقم {instance.invoice_number}',
                        created_by=instance.created_by
                    )
                elif instance.payment_method in ['check', 'transfer'] and instance.bank_account:
                    # معاملة الحساب البنكي
                    transaction_type = 'check' if instance.payment_method == 'check' else 'transfer'
                    # إنشاء معاملة الحساب البنكي
                    BankTransaction.objects.create(
                        bank=instance.bank_account,
                        transaction_type='withdrawal',
                        amount=instance.total_amount,
                        reference_number=instance.check_number if instance.payment_method == 'check' else f'PI-{instance.invoice_number}',
                        description=f'دفع فاتورة مشتريات رقم {instance.invoice_number}',
                        date=instance.date,
                        created_by=instance.created_by
                    )
                print(f"✓ تم إنشاء معاملات دفع المورد للفاتورة {instance.invoice_number}")
        except Exception as e:
            print(f"خطأ في إنشاء معاملات الدفع للفاتورة {instance.invoice_number}: {e}")
            import traceback
            traceback.print_exc()


@receiver(post_save, sender=PurchaseInvoice)
def update_inventory_on_purchase_invoice(sender, instance, created, **kwargs):
    """تحديث المخزون عند إنشاء أو تعديل فاتورة شراء"""
    try:
        # 🔧 تعطيل السيجنال أثناء عملية استعادة النسخة الاحتياطية
        try:
            from backup.restore_context import is_restoring
            if is_restoring():
                return
        except ImportError:
            pass
        
        from inventory.models import InventoryMovement
        from core.models import AuditLog
        
        warehouse = instance.warehouse
        if not warehouse:
            from inventory.models import Warehouse
            warehouse = Warehouse.get_default_warehouse()
            if warehouse:
                instance.warehouse = warehouse
                instance.save(update_fields=['warehouse'])
        
        if not warehouse:
            print(f"لا يوجد مستودع افتراضي لفاتورة الشراء {instance.invoice_number}")
            return
        
        # للفواتير الجديدة، إنشاء حركات مخزون واردة
        if created:
            for item in instance.items.all():
                if item.product.product_type == 'physical':
                    InventoryMovement.objects.create(
                        date=instance.date,
                        product=item.product,
                        warehouse=warehouse,
                        movement_type='in',
                        reference_type='purchase_invoice',
                        reference_id=instance.id,
                        quantity=item.quantity,
                        unit_cost=item.unit_price,
                        notes=f'مشتريات - فاتورة رقم {instance.invoice_number}',
                        created_by=instance.created_by
                    )
        else:
            # للتعديلات، حذف الحركات القديمة وإنشاء جديدة
            InventoryMovement.objects.filter(
                reference_type='purchase_invoice',
                reference_id=instance.id
            ).delete()
            
            for item in instance.items.all():
                if item.product.product_type == 'physical':
                    InventoryMovement.objects.create(
                        date=instance.date,
                        product=item.product,
                        warehouse=warehouse,
                        movement_type='in',
                        reference_type='purchase_invoice',
                        reference_id=instance.id,
                        quantity=item.quantity,
                        unit_cost=item.unit_price,
                        notes=f'مشتريات - فاتورة رقم {instance.invoice_number}',
                        created_by=instance.created_by
                    )
        
        print(f"تم تحديث المخزون لفاتورة الشراء {instance.invoice_number}")
        
        # تسجيل العملية في سجل الأنشطة
        try:
            description = f'{"إنشاء" if created else "تحديث"} فاتورة مشتريات رقم {instance.invoice_number}'
            if should_log_activity(instance.created_by, 'create' if created else 'update', 'PurchaseInvoice', instance.id, description[:20]):
                AuditLog.objects.create(
                    user=instance.created_by,
                    action_type='create' if created else 'update',
                    content_type='PurchaseInvoice',
                    object_id=instance.id,
                    description=description,
                    ip_address='127.0.0.1'
                )
        except Exception as log_error:
            print(f"خطأ في تسجيل نشاط فاتورة المشتريات: {log_error}")
        
    except Exception as e:
        print(f"خطأ في تحديث المخزون لفاتورة الشراء {instance.invoice_number}: {e}")
        pass


@receiver(post_save, sender=PurchaseReturn)
def create_journal_entry_for_purchase_return(sender, instance, created, **kwargs):
    """إنشاء القيد المحاسبي تلقائياً عند إنشاء أو تحديث مردود مشتريات"""
    def _create_entry():
        try:
            # 🔧 تعطيل السيجنال أثناء عملية استعادة النسخة الاحتياطية
            try:
                from backup.restore_context import is_restoring
                if is_restoring():
                    return
            except ImportError:
                pass
            
            from journal.models import JournalEntry
            from journal.services import JournalService
            
            # التحقق من وجود قيد محاسبي سابق
            existing_entry = JournalEntry.objects.filter(
                reference_type='purchase_return',
                reference_id=instance.id
            ).first()
            
            # حذف القيد القديم إذا كان موجوداً وإنشاء قيد جديد
            if existing_entry:
                existing_entry.delete()
                print(f"✓ تم حذف القيد المحاسبي القديم لمردود المشتريات {instance.return_number}")
            
            # إنشاء قيد جديد دائماً
            JournalService.create_purchase_return_entry(instance, instance.created_by)
            print(f"✓ تم {'إنشاء' if not existing_entry else 'تحديث'} القيد المحاسبي لمردود المشتريات {instance.return_number}")
        except Exception as e:
            print(f"✗ خطأ في إنشاء القيد المحاسبي لمردود المشتريات {instance.return_number}: {e}")
            import traceback
            traceback.print_exc()
    
    # استخدام transaction.on_commit لتجنب الاستدعاء المتكرر
    import threading
    if not hasattr(threading.current_thread(), '_purchase_return_signal_called'):
        threading.current_thread()._purchase_return_signal_called = set()
    
    signal_key = f"purchase_return_{instance.id}"
    if signal_key not in threading.current_thread()._purchase_return_signal_called:
        threading.current_thread()._purchase_return_signal_called.add(signal_key)
        transaction.on_commit(_create_entry)


@receiver(post_save, sender=PurchaseReturn)
def create_supplier_account_transaction_for_return(sender, instance, created, **kwargs):
    """إنشاء أو تحديث معاملة حساب المورد للمردود تلقائياً - متوافق مع IFRS"""
    # 🔧 تعطيل السيجنال أثناء عملية استعادة النسخة الاحتياطية
    try:
        try:
            from backup.restore_context import is_restoring
            if is_restoring():
                return
        except ImportError:
            pass
    except:
        pass
    
    try:
        from accounts.models import AccountTransaction
        import uuid
        
        # التحقق من وجود معاملة سابقة
        existing_transaction = AccountTransaction.objects.filter(
            reference_type='purchase_return',
            reference_id=instance.id
        ).first()
        
        # تحديد الاتجاه والوصف بناءً على نوع الفاتورة الأصلية
        original_invoice = instance.original_invoice
        if original_invoice and original_invoice.payment_type == 'credit':
            # الفاتورة الأصلية ذمم -> المردود يقلل الدين للمورد (مدين)
            direction = 'debit'
            description = f'مردود مشتريات ذمم رقم {instance.return_number}'
        else:
            # الفاتورة الأصلية نقدي -> المردود يقلل الرصيد (دائن)
            direction = 'credit'
            description = f'مردود مشتريات نقدي رقم {instance.return_number}'
        
        if existing_transaction:
            # تحديث المعاملة الموجودة (IFRS: تعديل التقديرات المحاسبية)
            existing_transaction.date = instance.date
            existing_transaction.customer_supplier = instance.supplier
            existing_transaction.amount = instance.total_amount
            existing_transaction.direction = direction
            existing_transaction.description = description
            existing_transaction.notes = instance.notes or ''
            existing_transaction.save()
            print(f"✓ تم تحديث معاملة حساب المورد لمردود المشتريات {instance.return_number}")
        else:
            # إنشاء معاملة جديدة
            transaction_number = f"PRET-{uuid.uuid4().hex[:8].upper()}"
            AccountTransaction.objects.create(
                transaction_number=transaction_number,
                date=instance.date,
                customer_supplier=instance.supplier,
                transaction_type='purchase_return',
                direction=direction,
                amount=instance.total_amount,
                reference_type='purchase_return',
                reference_id=instance.id,
                description=description,
                notes=instance.notes or '',
                created_by=instance.created_by
            )
            print(f"✓ تم إنشاء معاملة حساب المورد لمردود المشتريات {instance.return_number}")
    except Exception as e:
        print(f"✗ خطأ في إنشاء/تحديث معاملة حساب المورد للمردود {instance.return_number}: {e}")
        import traceback
        traceback.print_exc()


@receiver(post_save, sender=PurchaseReturn)
def update_inventory_on_purchase_return(sender, instance, created, **kwargs):
    """تحديث المخزون عند إنشاء أو تعديل مردود مشتريات"""
    # 🔧 تم تعطيل هذه الإشارة لتجنب التكرار مع create_inventory_movements في PurchaseReturnCreateView
    # حركات المخزون تُنشأ يدوياً في PurchaseReturnCreateView.create_inventory_movements()
    return

    try:
        # 🔧 تعطيل السيجنال أثناء عملية استعادة النسخة الاحتياطية
        from backup.restore_context import is_restoring
        if is_restoring():
            return

        from inventory.models import InventoryMovement

        warehouse = instance.original_invoice.warehouse
        if not warehouse:
            from inventory.models import Warehouse
            warehouse = Warehouse.get_default_warehouse()
            if warehouse:
                instance.original_invoice.warehouse = warehouse
                instance.original_invoice.save(update_fields=['warehouse'])

        if not warehouse:
            print(f"لا يوجد مستودع لمردود المشتريات {instance.return_number}")
            return

        # للمردودات الجديدة، إنشاء حركات مخزون صادرة
        if created:
            for item in instance.items.all():
                if item.product.product_type == 'physical':
                    InventoryMovement.objects.create(
                        date=instance.date,
                        product=item.product,
                        warehouse=warehouse,
                        movement_type='out',
                        reference_type='purchase_return',
                        reference_id=instance.id,
                        quantity=item.returned_quantity,
                        unit_cost=item.unit_price,
                        notes=f'مردود مشتريات - رقم {instance.return_number}',
                        created_by=instance.created_by
                    )
        else:
            # للتعديلات، حذف الحركات القديمة وإنشاء جديدة
            InventoryMovement.objects.filter(
                reference_type='purchase_return',
                reference_id=instance.id
            ).delete()

            for item in instance.items.all():
                if item.product.product_type == 'physical':
                    InventoryMovement.objects.create(
                        date=instance.date,
                        product=item.product,
                        warehouse=warehouse,
                        movement_type='out',
                        reference_type='purchase_return',
                        reference_id=instance.id,
                        quantity=item.returned_quantity,
                        unit_cost=item.unit_price,
                        notes=f'مردود مشتريات - رقم {instance.return_number}',
                        created_by=instance.created_by
                    )
        
        print(f"تم تحديث المخزون لمردود المشتريات {instance.return_number}")
        
        # تسجيل العملية في سجل الأنشطة
        try:
            from core.models import AuditLog
            description = f'{"إنشاء" if created else "تحديث"} مردود مشتريات رقم {instance.return_number}'
            if should_log_activity(instance.created_by, 'create' if created else 'update', 'PurchaseReturn', instance.id, description[:20]):
                AuditLog.objects.create(
                    user=instance.created_by,
                    action_type='create' if created else 'update',
                    content_type='PurchaseReturn',
                    object_id=instance.id,
                    description=description,
                    ip_address='127.0.0.1'
                )
        except Exception as log_error:
            print(f"خطأ في تسجيل نشاط مردود المشتريات: {log_error}")
        
    except Exception as e:
        print(f"خطأ في تحديث المخزون لمردود المشتريات {instance.return_number}: {e}")
        pass


@receiver(post_save, sender=PurchaseInvoiceItem)
def update_inventory_on_purchase_invoice_item(sender, instance, created, **kwargs):
    """تحديث المخزون عند إضافة/تعديل عنصر فاتورة شراء"""
    try:
        # 🔧 تعطيل السيجنال أثناء عملية استعادة النسخة الاحتياطية
        try:
            from backup.restore_context import is_restoring
            if is_restoring():
                return
        except ImportError:
            pass
        
        from inventory.models import InventoryMovement
        
        invoice = instance.invoice
        warehouse = invoice.warehouse
        if not warehouse:
            from inventory.models import Warehouse
            warehouse = Warehouse.get_default_warehouse()
            if warehouse:
                invoice.warehouse = warehouse
                invoice.save(update_fields=['warehouse'])
        
        if not warehouse:
            print(f"لا يوجد مستودع افتراضي لفاتورة الشراء {invoice.invoice_number}")
            return
        
        # حذف الحركات القديمة لهذا العنصر
        InventoryMovement.objects.filter(
            reference_type='purchase_invoice',
            reference_id=invoice.id,
            product=instance.product
        ).delete()
        
        # إنشاء حركة مخزون جديدة
        if instance.product.product_type == 'physical':
            InventoryMovement.objects.create(
                date=invoice.date,
                product=instance.product,
                warehouse=warehouse,
                movement_type='in',
                reference_type='purchase_invoice',
                reference_id=invoice.id,
                quantity=instance.quantity,
                unit_cost=instance.unit_price,
                notes=f'مشتريات - فاتورة رقم {invoice.invoice_number}',
                created_by=invoice.created_by
            )
        
        print(f"تم تحديث المخزون لفاتورة الشراء {invoice.invoice_number}")
        
        # تحديث مجاميع الفاتورة
        invoice.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])
        
    except Exception as e:
        try:
            print(f"خطأ في تحديث المخزون لفاتورة الشراء {instance.invoice.invoice_number}: {e}")
        except:
            print(f"خطأ في تحديث المخزون: {e}")
        pass


@receiver(post_delete, sender=PurchaseInvoiceItem)
def update_invoice_totals_on_item_delete(sender, instance, **kwargs):
    """تحديث مجاميع الفاتورة عند حذف عنصر"""
    try:
        from decimal import Decimal
        invoice = instance.invoice
        invoice.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])
    except Exception as e:
        print(f"خطأ في تحديث مجاميع الفاتورة عند حذف العنصر: {e}")


@receiver(post_save, sender=PurchaseReturnItem)
def update_inventory_on_purchase_return_item(sender, instance, created, **kwargs):
    """تحديث المخزون عند إضافة/تعديل عنصر مردود المشتريات"""
    # 🔧 تم تعطيل هذه الإشارة لتجنب التكرار مع create_inventory_movements في PurchaseReturnCreateView
    # حركات المخزون تُنشأ يدوياً في PurchaseReturnCreateView.create_inventory_movements()
    return

    try:
        # 🔧 تعطيل السيجنال أثناء عملية استعادة النسخة الاحتياطية
        from backup.restore_context import is_restoring
        if is_restoring():
            return
        
        from inventory.models import InventoryMovement
        
        return_invoice = instance.return_invoice
        warehouse = return_invoice.original_invoice.warehouse
        
        if not warehouse:
            print(f"لا يوجد مستودع لمردود المشتريات {return_invoice.return_number}")
            return
        
        # حذف الحركات القديمة لهذا العنصر
        InventoryMovement.objects.filter(
            reference_type='purchase_return',
            reference_id=return_invoice.id,
            product=instance.product
        ).delete()
        
        # إنشاء حركة مخزون صادرة
        if instance.product.product_type == 'physical':
            InventoryMovement.objects.create(
                date=return_invoice.date,
                product=instance.product,
                warehouse=warehouse,
                movement_type='out',
                reference_type='purchase_return',
                reference_id=return_invoice.id,
                quantity=instance.returned_quantity,
                unit_cost=instance.unit_price,
                notes=f'مردود مشتريات - رقم {return_invoice.return_number}',
                created_by=return_invoice.created_by
            )
        
        print(f"تم تحديث المخزون لمردود المشتريات {return_invoice.return_number}")
        
    except Exception as e:
        print(f"خطأ في تحديث المخزون لمردود المشتريات {return_invoice.return_number}: {e}")
        pass


@receiver(post_save, sender=PurchaseInvoice)
def update_supplier_balance_on_purchase(sender, instance, created, **kwargs):
    """
    تحديث رصيد المورد تلقائياً عند إنشاء أو تعديل فاتورة شراء
    Update supplier balance automatically when purchase invoice is created or modified
    
    IFRS Compliance:
    - IAS 2: Inventories
    - IAS 37: Provisions, Contingent Liabilities and Contingent Assets
    """
    # تجنب التحديث المتكرر
    if getattr(instance, '_skip_balance_update', False):
        return
    
    # تعطيل السيجنال أثناء عملية استعادة النسخة الاحتياطية
    try:
        try:
            from backup.restore_context import is_restoring
            if is_restoring():
                return
        except ImportError:
            pass
    except:
        pass
    
    # تحديث الرصيد فقط للموردين وإذا كانت الفاتورة تحتوي على عناصر
    if instance.supplier and instance.items.count() > 0 and instance.total_amount > 0:
        with transaction.atomic():
            supplier = instance.supplier
            
            # حساب رصيد المورد من جميع الحركات
            from decimal import Decimal
            from django.db.models import Sum
            from payments.models import PaymentVoucher
            
            # إجمالي المشتريات (دائن - تزيد الذمم الدائنة)
            total_purchases = PurchaseInvoice.objects.filter(
                supplier=supplier
            ).aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0.000')
            
            # إجمالي المدفوعات (مدين - تقلل الذمم الدائنة)
            total_payments = PaymentVoucher.objects.filter(
                supplier=supplier,
                voucher_type='supplier',
                is_reversed=False
            ).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.000')
            
            # الرصيد = المشتريات - المدفوعات
            # Positive balance = we owe supplier (credit balance)
            new_balance = total_purchases - total_payments
            
            # تحديث رصيد المورد
            if supplier.balance != new_balance:
                supplier._skip_signal = True  # تجنب تفعيل إشارة التحديث في نموذج المورد
                supplier.balance = new_balance
                supplier.save(update_fields=['balance'])
                supplier._skip_signal = False
                
                print(f"✓ تم تحديث رصيد المورد {supplier.name}: {new_balance}")


@receiver(post_save, sender=PurchaseDebitNote)
def create_purchase_debit_note_entry(sender, instance, created, **kwargs):
    """
    إنشاء أو تحديث قيد محاسبي عند حفظ إشعار خصم المشتريات (Debit Note)
    """
    if hasattr(instance, '_skip_journal_entry'):
        return
        
    try:
        from purchases.views import create_debit_note_journal_entry
        from journal.models import JournalEntry
        from accounts.models import AccountTransaction
        import uuid
        
        if created:
            # إنشاء قيد جديد
            create_debit_note_journal_entry(instance, instance.created_by)
            print(f"✓ تم إنشاء قيد محاسبي لإشعار خصم المشتريات رقم {instance.note_number}")
        else:
            # تحديث قيد موجود
            # حذف القيد القديم أولاً
            old_entries = JournalEntry.objects.filter(
                reference_type='debit_note',
                reference_id=instance.id
            )
            if old_entries.exists():
                old_entries.delete()
                print(f"تم حذف القيد القديم لإشعار خصم المشتريات {instance.note_number}")
            
            # إنشاء قيد جديد
            create_debit_note_journal_entry(instance, instance.created_by)
            print(f"✓ تم تحديث قيد محاسبي لإشعار خصم المشتريات رقم {instance.note_number}")
            
        # إنشاء أو تحديث معاملة حساب المورد
        # حذف المعاملة القديمة إذا كانت موجودة
        AccountTransaction.objects.filter(
            reference_type='debit_note',
            reference_id=instance.id
        ).delete()
        
        # إنشاء معاملة جديدة
        transaction_number = f"PDN-{uuid.uuid4().hex[:8].upper()}"
        AccountTransaction.objects.create(
            transaction_number=transaction_number,
            date=instance.date,
            customer_supplier=instance.supplier,
            transaction_type='debit_note',
            direction='debit',  # مدين (زيادة المدينية من المورد)
            amount=instance.total_amount,
            reference_type='debit_note',
            reference_id=instance.id,
            description=f'إشعار مدين رقم {instance.note_number}',
            notes=instance.notes or '',
            created_by=instance.created_by
        )
        print(f"✓ تم إنشاء معاملة حساب {transaction_number} لإشعار المدين {instance.note_number}")
    except Exception as e:
        print(f"✗ خطأ في إنشاء قيد محاسبي لإشعار خصم المشتريات: {e}")


@receiver(pre_delete, sender=PurchaseDebitNote)
def delete_purchase_debit_note_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي عند حذف إشعار المدين"""
    try:
        from journal.models import JournalEntry
        from accounts.models import AccountTransaction
        
        # حذف القيد المحاسبي - البحث بـ reference_type='debit_note'
        deleted_entries = JournalEntry.objects.filter(
            reference_type='debit_note',
            reference_id=instance.id
        ).delete()
        
        # حذف معاملات الحساب - البحث بـ reference_type='debit_note'
        deleted_trans = AccountTransaction.objects.filter(
            reference_type='debit_note',
            reference_id=instance.id
        ).delete()
        
        print(f"✓ تم حذف القيد المحاسبي ({deleted_entries[0]} قيود) ومعاملات الحساب ({deleted_trans[0]} معاملات) لإشعار المدين {instance.note_number}")
    except Exception as e:
        print(f"✗ خطأ في حذف قيد إشعار المدين: {e}")


@receiver(pre_delete, sender=PurchaseInvoice)
def delete_purchase_invoice_returns_before_deletion(sender, instance, **kwargs):
    """حذف مردودات المشتريات المرتبطة قبل حذف فاتورة المشتريات"""
    try:
        # حذف جميع مردودات المشتريات المرتبطة بهذه الفاتورة
        related_returns = PurchaseReturn.objects.filter(original_invoice=instance)
        deleted_returns = related_returns.count()
        related_returns.delete()
        
        if deleted_returns > 0:
            print(f"✓ تم حذف {deleted_returns} مردود مشتريات مرتبط بفاتورة المشتريات {instance.invoice_number}")
    except Exception as e:
        print(f"✗ خطأ في حذف مردودات المشتريات المرتبطة بفاتورة {instance.invoice_number}: {e}")


@receiver(post_delete, sender=PurchaseInvoice)
def delete_purchase_invoice_related_records(sender, instance, **kwargs):
    """حذف السجلات المرتبطة عند حذف فاتورة المشتريات"""
    try:
        from inventory.models import InventoryMovement
        from journal.models import JournalEntry
        from accounts.models import AccountTransaction
        from cashboxes.models import CashboxTransaction
        from banks.models import BankTransaction
        
        # حذف حركات المخزون
        inventory_movements = InventoryMovement.objects.filter(
            reference_type='purchase_invoice',
            reference_id=instance.id
        )
        deleted_inventory = inventory_movements.count()
        inventory_movements.delete()
        
        # حذف القيود المحاسبية - استخدام ForeignKey
        journal_entries = JournalEntry.objects.filter(purchase_invoice=instance)
        deleted_journal = journal_entries.count()
        journal_entries.delete()
        
        # حذف معاملات حساب المورد - جميع الأنواع المرتبطة بالفاتورة
        account_transactions = AccountTransaction.objects.filter(
            reference_type__in=['purchase_invoice', 'purchase_payment'],
            reference_id=instance.id
        )
        deleted_transactions = account_transactions.count()
        account_transactions.delete()
        
        # حذف معاملات الصندوق المرتبطة بالفاتورة
        cashbox_transactions = CashboxTransaction.objects.filter(
            description__icontains=f'فاتورة مشتريات رقم {instance.invoice_number}'
        )
        deleted_cashbox = cashbox_transactions.count()
        cashbox_transactions.delete()
        
        # حذف معاملات الحساب البنكي المرتبطة بالفاتورة
        bank_transactions = BankTransaction.objects.filter(
            description__icontains=f'فاتورة مشتريات رقم {instance.invoice_number}'
        )
        deleted_bank = bank_transactions.count()
        bank_transactions.delete()
        
        print(f"✓ تم حذف {deleted_inventory} حركة مخزون، {deleted_journal} قيد محاسبي، {deleted_transactions} معاملة حساب، {deleted_cashbox} معاملة صندوق، و {deleted_bank} معاملة بنكية لفاتورة المشتريات {instance.invoice_number}")
    except Exception as e:
        print(f"✗ خطأ في حذف السجلات المرتبطة بفاتورة المشتريات {instance.invoice_number}: {e}")
        import traceback
        traceback.print_exc()


@receiver(post_delete, sender=PurchaseReturn)
def delete_purchase_return_related_records(sender, instance, **kwargs):
    """حذف السجلات المرتبطة عند حذف مردود المشتريات"""
    try:
        from inventory.models import InventoryMovement
        from journal.models import JournalEntry
        from accounts.models import AccountTransaction
        
        # حذف حركات المخزون
        inventory_movements = InventoryMovement.objects.filter(
            reference_type='purchase_return',
            reference_id=instance.id
        )
        deleted_inventory = inventory_movements.count()
        inventory_movements.delete()
        
        # حذف القيود المحاسبية
        journal_entries = JournalEntry.objects.filter(
            reference_type='purchase_return',
            reference_id=instance.id
        )
        deleted_journal = journal_entries.count()
        journal_entries.delete()
        
        # حذف معاملات الحساب
        account_transactions = AccountTransaction.objects.filter(
            reference_type='purchase_return',
            reference_id=instance.id
        )
        deleted_transactions = account_transactions.count()
        account_transactions.delete()
        
        print(f"✓ تم حذف {deleted_inventory} حركة مخزون، {deleted_journal} قيد محاسبي، و {deleted_transactions} معاملة حساب لمردود المشتريات {instance.return_number}")
    except Exception as e:
        print(f"✗ خطأ في حذف السجلات المرتبطة بمردود المشتريات {instance.return_number}: {e}")
        import traceback
        traceback.print_exc()


@receiver(post_save, sender=PurchaseInvoiceItem)
def create_journal_entry_after_item_added(sender, instance, created, **kwargs):
    """إنشاء أو تحديث القيد المحاسبي بعد إضافة أو تحديث عنصر فاتورة المشتريات"""
    def _create_entry():
        try:
            invoice = instance.invoice
            
            # 🔧 تعطيل السيجنال أثناء عملية استعادة النسخة الاحتياطية
            try:
                from backup.restore_context import is_restoring
                if is_restoring():
                    return
            except ImportError:
                pass
            
            from journal.models import JournalEntry
            from journal.services import JournalService
            
            # التحقق من وجود عناصر
            if invoice.items.count() > 0:
                existing_entry = JournalEntry.objects.filter(
                    purchase_invoice=invoice
                ).first()
                
                # حذف القيد القديم إذا كان موجوداً
                if existing_entry:
                    existing_entry.delete()
                
                # إنشاء قيد جديد
                try:
                    JournalService.create_purchase_invoice_entry(invoice, invoice.created_by)
                except Exception as e:
                    print(f"خطأ في إنشاء قيد فاتورة المشتريات {invoice.invoice_number}: {e}")
                    import traceback
                    traceback.print_exc()
        except Exception as e:
            print(f"خطأ في إنشاء القيد المحاسبي لعنصر فاتورة المشتريات: {e}")
    
    # استخدام transaction.on_commit لضمان حفظ جميع العناصر
    import threading
    if not hasattr(threading.current_thread(), '_item_signal_called'):
        threading.current_thread()._item_signal_called = set()
    
    signal_key = f"item_{instance.invoice.id}"
    if signal_key not in threading.current_thread()._item_signal_called:
        threading.current_thread()._item_signal_called.add(signal_key)
        transaction.on_commit(_create_entry)
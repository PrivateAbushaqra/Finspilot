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
    # 🔧 تعطيل السيجنال أثناء عملية استعادة النسخة الاحتياطية
    try:
        from backup.restore_context import is_restoring
        if is_restoring():
            return
    except ImportError:
        pass
    
    # تجنب الاستدعاء المتكرر
    import threading
    if not hasattr(threading.current_thread(), '_purchase_journal_signal_called'):
        threading.current_thread()._purchase_journal_signal_called = set()
    
    signal_key = f"purchase_journal_{instance.id}_{instance.updated_at}"
    if signal_key in threading.current_thread()._purchase_journal_signal_called:
        print(f"DEBUG: Skipping duplicate journal signal call for {instance.invoice_number}")
        return
    threading.current_thread()._purchase_journal_signal_called.add(signal_key)
    
    def _create_entry():
        try:
            from journal.models import JournalEntry
            from journal.services import JournalService
            from decimal import Decimal, ROUND_HALF_UP
            
            # التحقق من وجود عناصر
            if instance.items.count() == 0:
                return
            
            # إعادة حساب المجاميع من العناصر لضمان الدقة
            subtotal = Decimal('0')
            tax_amount = Decimal('0')
            total_amount = Decimal('0')

            for item in instance.items.all():
                # المجموع الفرعي = الإجمالي - الضريبة (لأن total_amount قد يكون شامل الضريبة)
                item_subtotal = item.total_amount - item.tax_amount
                subtotal += item_subtotal
                tax_amount += item.tax_amount
                total_amount += item.total_amount

            # تحديث المجاميع في الفاتورة بدون إطلاق السيجنالات
            if (instance.subtotal != subtotal or 
                instance.tax_amount != tax_amount or 
                instance.total_amount != total_amount):
                PurchaseInvoice.objects.filter(id=instance.id).update(
                    subtotal=subtotal.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP),
                    tax_amount=tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP),
                    total_amount=total_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                )
                # تحديث المتغير المحلي
                instance.refresh_from_db()
            
            # البحث عن قيد موجود
            existing_entry = JournalEntry.objects.filter(
                purchase_invoice=instance
            ).first()
            
            # حذف القيد القديم إذا كان موجوداً
            if existing_entry:
                print(f"✓ حذف القيد القديم {existing_entry.entry_number} للفاتورة {instance.invoice_number}")
                existing_entry.delete()
            
            # إنشاء قيد جديد دائماً
            print(f"✓ إنشاء قيد جديد للفاتورة {instance.invoice_number} بمبلغ {instance.total_amount}")
            JournalService.create_purchase_invoice_entry(instance, instance.created_by)
        except Exception as e:
            print(f"خطأ في إنشاء القيد المحاسبي لفاتورة المشتريات {instance.invoice_number}: {e}")
            import traceback
            traceback.print_exc()
    
    # استخدام transaction.on_commit
    transaction.on_commit(_create_entry)


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
    
    # تجنب الاستدعاء المتكرر
    import threading
    if not hasattr(threading.current_thread(), '_purchase_account_signal_called'):
        threading.current_thread()._purchase_account_signal_called = set()
    
    signal_key = f"purchase_account_{instance.id}_{instance.updated_at}"
    if signal_key in threading.current_thread()._purchase_account_signal_called:
        return
    threading.current_thread()._purchase_account_signal_called.add(signal_key)
    
    # تنفيذ بعد الـ commit لضمان تحديث المجاميع أولاً
    def _create_transaction():
        # التحقق من وجود الفاتورة قبل الاستمرار
        try:
            instance.refresh_from_db()
        except PurchaseInvoice.DoesNotExist:
            # الفاتورة تم حذفها، نخرج من الدالة
            return
        
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
                    # إنشاء معاملة جديدة فقط إذا لم تكن موجودة
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
        # تجنب الاستدعاء المتكرر
        if not hasattr(threading.current_thread(), '_purchase_payment_signal_called'):
            threading.current_thread()._purchase_payment_signal_called = set()
        
        payment_signal_key = f"purchase_payment_{instance.id}_{instance.updated_at}"
        if payment_signal_key in threading.current_thread()._purchase_payment_signal_called:
            print(f"DEBUG: Skipping duplicate payment signal call for {instance.invoice_number}")
            return
        threading.current_thread()._purchase_payment_signal_called.add(payment_signal_key)
        
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
                    # إنشاء معاملات جديدة فقط إذا لم تكن موجودة
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
    
    # استخدام transaction.on_commit لتنفيذ بعد حفظ جميع البيانات
    transaction.on_commit(_create_transaction)


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
    # تجنب الاستدعاء المتكرر
    import threading
    if not hasattr(threading.current_thread(), '_purchase_return_journal_signal_called'):
        threading.current_thread()._purchase_return_journal_signal_called = set()
    
    signal_key = f"purchase_return_journal_{instance.id}_{instance.updated_at}"
    if signal_key in threading.current_thread()._purchase_return_journal_signal_called:
        return
    threading.current_thread()._purchase_return_journal_signal_called.add(signal_key)
    
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
            
            # إعادة تحميل للحصول على أحدث البيانات
            instance.refresh_from_db()
            
            # التحقق من وجود عناصر ومبلغ
            if instance.items.count() == 0 or instance.total_amount <= 0:
                print(f"⚠️ تخطي إنشاء قيد لمردود {instance.return_number} - لا توجد عناصر أو المبلغ صفر")
                return
            
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
    
    # استخدام transaction.on_commit لتنفيذ بعد حفظ جميع البيانات
    transaction.on_commit(_create_entry)


@receiver(post_save, sender=PurchaseReturn)
def create_supplier_account_transaction_for_return(sender, instance, created, **kwargs):
    """إنشاء أو تحديث معاملة حساب المورد للمردود تلقائياً - متوافق مع IFRS"""
    # تجنب الاستدعاء المتكرر
    import threading
    if not hasattr(threading.current_thread(), '_purchase_return_account_signal_called'):
        threading.current_thread()._purchase_return_account_signal_called = set()
    
    signal_key = f"purchase_return_account_{instance.id}_{instance.updated_at}"
    if signal_key in threading.current_thread()._purchase_return_account_signal_called:
        return
    threading.current_thread()._purchase_return_account_signal_called.add(signal_key)
    
    def _create_transaction():
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
            
            # إعادة تحميل للحصول على أحدث البيانات
            instance.refresh_from_db()
            
            # التحقق من وجود عناصر ومبلغ
            if instance.items.count() == 0 or instance.total_amount <= 0:
                print(f"⚠️ تخطي إنشاء معاملة حساب لمردود {instance.return_number} - لا توجد عناصر أو المبلغ صفر")
                return
            
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
    
    # استخدام transaction.on_commit لتنفيذ بعد حفظ جميع البيانات
    transaction.on_commit(_create_transaction)


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
        from decimal import Decimal, ROUND_HALF_UP
        
        invoice = instance.invoice
        warehouse = invoice.warehouse
        if not warehouse:
            from inventory.models import Warehouse
            warehouse = Warehouse.get_default_warehouse()
            if warehouse:
                invoice.warehouse = warehouse
                PurchaseInvoice.objects.filter(id=invoice.id).update(warehouse=warehouse)
        
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
        
        # تحديث مجاميع الفاتورة - حساب من جميع العناصر
        subtotal = Decimal('0')
        tax_amount = Decimal('0')
        total_amount = Decimal('0')
        
        for item in invoice.items.all():
            subtotal += item.quantity * item.unit_price
            tax_amount += item.tax_amount
            total_amount += item.total_amount
        
        # تحديث المجاميع مباشرة بدون إطلاق السيجنالات
        PurchaseInvoice.objects.filter(id=invoice.id).update(
            subtotal=subtotal.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP),
            tax_amount=tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP),
            total_amount=total_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        )
        print(f"✓ تم تحديث مجاميع الفاتورة: الإجمالي={total_amount}")
        
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
    """تحديث المخزون والمجاميع عند إضافة/تعديل عنصر مردود المشتريات"""
    try:
        # 🔧 تعطيل السيجنال أثناء عملية استعادة النسخة الاحتياطية
        try:
            from backup.restore_context import is_restoring
            if is_restoring():
                return
        except ImportError:
            pass
        
        from inventory.models import InventoryMovement
        from decimal import Decimal, ROUND_HALF_UP
        
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
        
        # إنشاء حركة مخزون صادرة (إرجاع)
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
        
        print(f"✓ تم تحديث المخزون لمردود المشتريات {return_invoice.return_number}")
        
        # تحديث مجاميع المردود - حساب من جميع العناصر
        subtotal = Decimal('0')
        tax_amount = Decimal('0')
        total_amount = Decimal('0')
        
        for item in return_invoice.items.all():
            subtotal += item.returned_quantity * item.unit_price
            tax_amount += item.tax_amount
            total_amount += item.total_amount
        
        # تحديث المجاميع مباشرة بدون إطلاق السيجنالات
        PurchaseReturn.objects.filter(id=return_invoice.id).update(
            subtotal=subtotal.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP),
            tax_amount=tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP),
            total_amount=total_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        )
        print(f"✓ تم تحديث مجاميع المردود: الإجمالي={total_amount}")
        
        # إنشاء/تحديث القيد ومعاملة الحساب بعد تحديث المجاميع
        def _create_journal_and_transaction():
            try:
                # إعادة تحميل للحصول على أحدث البيانات
                return_invoice.refresh_from_db()
                
                if return_invoice.total_amount > 0:
                    # إنشاء القيد المحاسبي
                    from journal.models import JournalEntry
                    from journal.services import JournalService
                    
                    existing_entry = JournalEntry.objects.filter(
                        reference_type='purchase_return',
                        reference_id=return_invoice.id
                    ).first()
                    
                    if existing_entry:
                        existing_entry.delete()
                    
                    JournalService.create_purchase_return_entry(return_invoice, return_invoice.created_by)
                    print(f"✓ تم إنشاء/تحديث القيد المحاسبي لمردود {return_invoice.return_number}")
                    
                    # إنشاء معاملة حساب المورد
                    from accounts.models import AccountTransaction
                    import uuid
                    
                    existing_transaction = AccountTransaction.objects.filter(
                        reference_type='purchase_return',
                        reference_id=return_invoice.id
                    ).first()
                    
                    original_invoice = return_invoice.original_invoice
                    if original_invoice and original_invoice.payment_type == 'credit':
                        direction = 'debit'
                        description = f'مردود مشتريات ذمم رقم {return_invoice.return_number}'
                    else:
                        direction = 'credit'
                        description = f'مردود مشتريات نقدي رقم {return_invoice.return_number}'
                    
                    if existing_transaction:
                        existing_transaction.date = return_invoice.date
                        existing_transaction.customer_supplier = return_invoice.supplier
                        existing_transaction.amount = return_invoice.total_amount
                        existing_transaction.direction = direction
                        existing_transaction.description = description
                        existing_transaction.notes = return_invoice.notes or ''
                        existing_transaction.save()
                    else:
                        transaction_number = f"PRET-{uuid.uuid4().hex[:8].upper()}"
                        AccountTransaction.objects.create(
                            transaction_number=transaction_number,
                            date=return_invoice.date,
                            customer_supplier=return_invoice.supplier,
                            transaction_type='purchase_return',
                            direction=direction,
                            amount=return_invoice.total_amount,
                            reference_type='purchase_return',
                            reference_id=return_invoice.id,
                            description=description,
                            notes=return_invoice.notes or '',
                            created_by=return_invoice.created_by
                        )
                    print(f"✓ تم إنشاء/تحديث معاملة حساب المورد لمردود {return_invoice.return_number}")
            except Exception as e:
                print(f"خطأ في إنشاء القيد/المعاملة: {e}")
                import traceback
                traceback.print_exc()
        
        # استخدام transaction.on_commit
        transaction.on_commit(_create_journal_and_transaction)
        
    except Exception as e:
        try:
            print(f"خطأ في تحديث المخزون/المجاميع لمردود المشتريات {instance.return_invoice.return_number}: {e}")
        except:
            print(f"خطأ في تحديث المخزون/المجاميع للمردود: {e}")
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
    وفقاً لمعايير IFRS
    """
    if hasattr(instance, '_skip_journal_entry'):
        return
        
    try:
        from purchases.views import create_debit_note_journal_entry
        from journal.models import JournalEntry
        from accounts.models import AccountTransaction
        
        if created:
            # إنشاء قيد جديد - دالة create_debit_note_journal_entry 
            # تقوم بإنشاء القيد المحاسبي و AccountTransaction معاً
            create_debit_note_journal_entry(instance, instance.created_by)
            print(f"✓ تم إنشاء قيد محاسبي وحركة حساب لإشعار المدين رقم {instance.note_number}")
        else:
            # تحديث قيد موجود
            # حذف القيد القديم والمعاملات القديمة أولاً
            old_entries = JournalEntry.objects.filter(
                reference_type='debit_note',
                reference_id=instance.id
            )
            if old_entries.exists():
                old_entries.delete()
                print(f"تم حذف القيد القديم لإشعار المدين {instance.note_number}")
            
            # حذف المعاملات القديمة
            AccountTransaction.objects.filter(
                reference_type='debit_note',
                reference_id=instance.id
            ).delete()
            
            # إنشاء قيد جديد - دالة create_debit_note_journal_entry 
            # تقوم بإنشاء القيد المحاسبي و AccountTransaction معاً
            create_debit_note_journal_entry(instance, instance.created_by)
            print(f"✓ تم تحديث قيد محاسبي وحركة حساب لإشعار المدين رقم {instance.note_number}")
            
    except Exception as e:
        print(f"✗ خطأ في إنشاء قيد محاسبي لإشعار المدين: {e}")


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


@receiver(pre_delete, sender=PurchaseInvoice)
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
def update_invoice_on_item_change(sender, instance, created, **kwargs):
    """تحديث الفاتورة عند إضافة أو تعديل بند لتحديث القيد المحاسبي تلقائياً"""
    try:
        # 🔧 تعطيل السيجنال أثناء عملية استعادة النسخة الاحتياطية
        try:
            from backup.restore_context import is_restoring
            if is_restoring():
                return
        except ImportError:
            pass
        
        # حفظ الفاتورة لتفعيل السيجنال الأساسي الذي يُنشئ القيد
        invoice = instance.invoice
        invoice.save()
        
    except Exception as e:
        print(f"خطأ في تحديث الفاتورة بعد تعديل البند: {e}")


# تم تعطيل هذا السيجنال لأن السيجنال الأساسي create_journal_entry_for_purchase_invoice يتعامل مع جميع الحالات
# @receiver(post_save, sender=PurchaseInvoiceItem)
def create_journal_entry_after_item_added_DISABLED(sender, instance, created, **kwargs):
    """إنشاء أو تحديث القيد المحاسبي ومعاملات الحساب بعد إضافة أو تحديث عنصر فاتورة المشتريات
    ملاحظة: تم تعطيل هذا السيجنال لتجنب التكرار مع السيجنال الأساسي
    """
    def _create_entry_and_transactions():
        try:
            invoice = instance.invoice
            
            # 🔧 تعطيل السيجنال أثناء عملية استعادة النسخة الاحتياطية
            try:
                from backup.restore_context import is_restoring
                if is_restoring():
                    return
            except ImportError:
                pass
            
            # إعادة تحميل الفاتورة للحصول على أحدث البيانات
            invoice.refresh_from_db()
            
            # التحقق من وجود عناصر ومبلغ
            if invoice.items.count() > 0 and invoice.total_amount > 0:
                from journal.models import JournalEntry
                from journal.services import JournalService
                from accounts.models import AccountTransaction
                from cashboxes.models import CashboxTransaction
                from banks.models import BankTransaction
                import uuid
                
                # 1. إنشاء/تحديث القيد المحاسبي
                existing_entry = JournalEntry.objects.filter(
                    purchase_invoice=invoice
                ).first()
                
                if existing_entry:
                    existing_entry.delete()
                
                try:
                    JournalService.create_purchase_invoice_entry(invoice, invoice.created_by)
                    print(f"✓ تم إنشاء القيد المحاسبي للفاتورة {invoice.invoice_number}")
                except Exception as e:
                    print(f"خطأ في إنشاء قيد فاتورة المشتريات {invoice.invoice_number}: {e}")
                
                # 2. إنشاء/تحديث معاملة حساب المورد
                if invoice.payment_type == 'credit':
                    # فاتورة ذمم
                    existing_transaction = AccountTransaction.objects.filter(
                        reference_type='purchase_invoice',
                        reference_id=invoice.id
                    ).first()
                    
                    if existing_transaction:
                        existing_transaction.date = invoice.date
                        existing_transaction.customer_supplier = invoice.supplier
                        existing_transaction.amount = invoice.total_amount
                        existing_transaction.description = f'فاتورة مشتريات رقم {invoice.invoice_number}'
                        existing_transaction.notes = invoice.notes or ''
                        existing_transaction.save()
                        print(f"✓ تم تحديث معاملة حساب المورد للفاتورة {invoice.invoice_number}")
                    else:
                        transaction_number = f"PT-{uuid.uuid4().hex[:8].upper()}"
                        AccountTransaction.objects.create(
                            transaction_number=transaction_number,
                            date=invoice.date,
                            customer_supplier=invoice.supplier,
                            transaction_type='purchase_invoice',
                            direction='credit',
                            amount=invoice.total_amount,
                            reference_type='purchase_invoice',
                            reference_id=invoice.id,
                            description=f'فاتورة مشتريات رقم {invoice.invoice_number}',
                            notes=invoice.notes or '',
                            created_by=invoice.created_by
                        )
                        print(f"✓ تم إنشاء معاملة حساب المورد للفاتورة {invoice.invoice_number}")
                
                # 3. إنشاء/تحديث معاملات الدفع النقدي
                elif invoice.payment_type == 'cash' and invoice.payment_method:
                    # معاملة حساب المورد
                    existing_transaction = AccountTransaction.objects.filter(
                        reference_type='purchase_payment',
                        reference_id=invoice.id
                    ).first()
                    
                    if existing_transaction:
                        existing_transaction.date = invoice.date
                        existing_transaction.customer_supplier = invoice.supplier
                        existing_transaction.amount = invoice.total_amount
                        existing_transaction.description = f'دفع فاتورة مشتريات رقم {invoice.invoice_number}'
                        existing_transaction.notes = invoice.notes or ''
                        existing_transaction.save()
                        print(f"✓ تم تحديث معاملة دفع المورد للفاتورة {invoice.invoice_number}")
                    else:
                        transaction_number = f"PP-{uuid.uuid4().hex[:8].upper()}"
                        AccountTransaction.objects.create(
                            transaction_number=transaction_number,
                            date=invoice.date,
                            customer_supplier=invoice.supplier,
                            transaction_type='purchase',
                            direction='debit',
                            amount=invoice.total_amount,
                            reference_type='purchase_payment',
                            reference_id=invoice.id,
                            description=f'دفع فاتورة مشتريات رقم {invoice.invoice_number}',
                            notes=invoice.notes or '',
                            created_by=invoice.created_by
                        )
                        print(f"✓ تم إنشاء معاملة دفع المورد للفاتورة {invoice.invoice_number}")
                    
                    # معاملة الصندوق أو البنك
                    if invoice.payment_method == 'cash' and invoice.cashbox:
                        cashbox_trans = CashboxTransaction.objects.filter(
                            description__icontains=f'فاتورة مشتريات رقم {invoice.invoice_number}'
                        ).first()
                        if cashbox_trans:
                            cashbox_trans.cashbox = invoice.cashbox
                            cashbox_trans.date = invoice.date
                            cashbox_trans.amount = invoice.total_amount
                            cashbox_trans.save()
                        else:
                            CashboxTransaction.objects.create(
                                cashbox=invoice.cashbox,
                                transaction_type='withdrawal',
                                date=invoice.date,
                                amount=invoice.total_amount,
                                description=f'دفع فاتورة مشتريات رقم {invoice.invoice_number}',
                                created_by=invoice.created_by
                            )
                        print(f"✓ تم إنشاء/تحديث معاملة الصندوق للفاتورة {invoice.invoice_number}")
                    
                    elif invoice.payment_method in ['check', 'transfer'] and invoice.bank_account:
                        bank_trans = BankTransaction.objects.filter(
                            description__icontains=f'فاتورة مشتريات رقم {invoice.invoice_number}'
                        ).first()
                        if bank_trans:
                            bank_trans.bank = invoice.bank_account
                            bank_trans.date = invoice.date
                            bank_trans.amount = invoice.total_amount
                            bank_trans.reference_number = invoice.check_number if invoice.payment_method == 'check' else f'PI-{invoice.invoice_number}'
                            bank_trans.save()
                        else:
                            BankTransaction.objects.create(
                                bank=invoice.bank_account,
                                transaction_type='withdrawal',
                                amount=invoice.total_amount,
                                reference_number=invoice.check_number if invoice.payment_method == 'check' else f'PI-{invoice.invoice_number}',
                                description=f'دفع فاتورة مشتريات رقم {invoice.invoice_number}',
                                date=invoice.date,
                                created_by=invoice.created_by
                            )
                        print(f"✓ تم إنشاء/تحديث معاملة البنك للفاتورة {invoice.invoice_number}")
                
        except Exception as e:
            print(f"خطأ في إنشاء القيد المحاسبي/المعاملات لعنصر فاتورة المشتريات: {e}")
            import traceback
            traceback.print_exc()
    
    # استخدام transaction.on_commit لضمان حفظ جميع البيانات
    import threading
    if not hasattr(threading.current_thread(), '_item_signal_called'):
        threading.current_thread()._item_signal_called = set()
    
    signal_key = f"item_{instance.invoice.id}_{instance.invoice.updated_at}"
    if signal_key not in threading.current_thread()._item_signal_called:
        threading.current_thread()._item_signal_called.add(signal_key)
        transaction.on_commit(_create_entry_and_transactions)
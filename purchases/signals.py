from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import PurchaseInvoice, PurchaseInvoiceItem, PurchaseReturn, PurchaseReturnItem, PurchaseDebitNote
from django.db import transaction


@receiver(post_save, sender=PurchaseInvoice)
def create_journal_entry_for_purchase_invoice(sender, instance, created, **kwargs):
    """إنشاء القيد المحاسبي تلقائياً عند إنشاء أو تحديث فاتورة مشتريات"""
    try:
        from journal.models import JournalEntry
        from journal.services import JournalService
        
        # التحقق من وجود عناصر وعدم وجود قيد محاسبي مسبقاً
        if instance.items.count() > 0:
            existing_entry = JournalEntry.objects.filter(
                reference_type='purchase_invoice',
                reference_id=instance.id
            ).first()
            
            # إنشاء القيد فقط إذا لم يكن موجوداً من قبل
            if not existing_entry:
                JournalService.create_purchase_invoice_entry(instance, instance.created_by)
    except Exception as e:
        print(f"خطأ في إنشاء القيد المحاسبي لفاتورة المشتريات {instance.invoice_number}: {e}")


@receiver(post_save, sender=PurchaseInvoice)
def create_supplier_account_transaction(sender, instance, created, **kwargs):
    """إنشاء معاملة حساب المورد تلقائياً"""
    if instance.payment_type == 'credit' and instance.items.count() > 0 and instance.total_amount > 0:
        try:
            from accounts.models import AccountTransaction
            import uuid
            
            # التحقق من عدم وجود معاملة مسبقاً
            existing_transaction = AccountTransaction.objects.filter(
                reference_type='purchase_invoice',
                reference_id=instance.id
            ).first()
            
            # إنشاء المعاملة فقط إذا لم تكن موجودة من قبل
            if not existing_transaction:
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
        except Exception as e:
            print(f"خطأ في إنشاء معاملة حساب المورد للفاتورة {instance.invoice_number}: {e}")


@receiver(post_save, sender=PurchaseInvoice)
def update_inventory_on_purchase_invoice(sender, instance, created, **kwargs):
    """تحديث المخزون عند إنشاء أو تعديل فاتورة شراء"""
    try:
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
            AuditLog.objects.create(
                user=instance.created_by,
                action_type='create' if created else 'update',
                content_type='PurchaseInvoice',
                object_id=instance.id,
                description=f'{"إنشاء" if created else "تحديث"} فاتورة مشتريات رقم {instance.invoice_number}',
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
    try:
        from journal.models import JournalEntry
        from journal.services import JournalService
        
        # التحقق من وجود عناصر وعدم وجود قيد محاسبي مسبقاً
        if instance.items.count() > 0:
            existing_entry = JournalEntry.objects.filter(
                reference_type='purchase_return',
                reference_id=instance.id
            ).first()
            
            # إنشاء القيد فقط إذا لم يكن موجوداً من قبل
            if not existing_entry:
                JournalService.create_purchase_return_entry(instance, instance.created_by)
    except Exception as e:
        print(f"خطأ في إنشاء القيد المحاسبي لمردود المشتريات {instance.return_number}: {e}")


@receiver(post_save, sender=PurchaseReturn)
def create_supplier_account_transaction_for_return(sender, instance, created, **kwargs):
    """إنشاء معاملة حساب المورد للمردود تلقائياً"""
    if instance.items.count() > 0 and instance.total_amount > 0:
        try:
            from accounts.models import AccountTransaction
            import uuid
            
            # التحقق من عدم وجود معاملة مسبقاً
            existing_transaction = AccountTransaction.objects.filter(
                reference_type='purchase_return',
                reference_id=instance.id
            ).first()
            
            # إنشاء المعاملة فقط إذا لم تكن موجودة من قبل
            if not existing_transaction:
                transaction_number = f"RTN-{uuid.uuid4().hex[:8].upper()}"
                AccountTransaction.objects.create(
                    transaction_number=transaction_number,
                    date=instance.date,
                    customer_supplier=instance.original_invoice.supplier,
                    transaction_type='purchase_return',
                    direction='debit',  # مدين (تقليل دين المورد)
                    amount=instance.total_amount,
                    reference_type='purchase_return',
                    reference_id=instance.id,
                    description=f'مردود مشتريات رقم {instance.return_number}',
                    notes=instance.notes or '',
                    created_by=instance.created_by
                )
        except Exception as e:
            print(f"خطأ في إنشاء معاملة حساب المورد للمردود {instance.return_number}: {e}")


@receiver(post_save, sender=PurchaseReturn)
def update_inventory_on_purchase_return(sender, instance, created, **kwargs):
    """تحديث المخزون عند إنشاء أو تعديل مردود مشتريات"""
    try:
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
            AuditLog.objects.create(
                user=instance.created_by,
                action_type='create' if created else 'update',
                content_type='PurchaseReturn',
                object_id=instance.id,
                description=f'{"إنشاء" if created else "تحديث"} مردود مشتريات رقم {instance.return_number}',
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
        
    except Exception as e:
        print(f"خطأ في تحديث المخزون لفاتورة الشراء {invoice.invoice_number}: {e}")
        pass


@receiver(post_save, sender=PurchaseReturnItem)
def update_inventory_on_purchase_return_item(sender, instance, created, **kwargs):
    """تحديث المخزون عند إضافة/تعديل عنصر مردود المشتريات"""
    try:
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


@receiver(post_save, sender=PurchaseReturn)
def update_inventory_on_purchase_return(sender, instance, created, **kwargs):
    """تحديث المخزون عند إنشاء أو تعديل مردود مشتريات"""
    try:
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
        
    except Exception as e:
        print(f"خطأ في تحديث المخزون لمردود المشتريات {instance.return_number}: {e}")
        pass
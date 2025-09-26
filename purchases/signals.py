from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PurchaseInvoice


@receiver(post_save, sender=PurchaseInvoice)
def update_inventory_on_purchase_invoice(sender, instance, created, **kwargs):
    """تحديث المخزون عند إنشاء أو تعديل فاتورة شراء"""
    try:
        from inventory.models import InventoryMovement
        
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
        
    except Exception as e:
        print(f"خطأ في تحديث المخزون لفاتورة الشراء {instance.invoice_number}: {e}")
        pass
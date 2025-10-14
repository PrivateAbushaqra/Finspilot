"""
إشارات لنظام المنتجات
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Product
from decimal import Decimal


@receiver(pre_save, sender=Product)
def handle_product_opening_balance(sender, instance, **kwargs):
    """
    معالجة الرصيد الافتتاحي عند إنشاء/تعديل المنتج
    """
    # إذا كان المنتج جديداً، سنتعامل معه في post_save
    if not instance.pk:
        return
    
    # إذا كان المنتج قديماً، نحفظ القيم القديمة للمقارنة
    try:
        old_product = Product.objects.get(pk=instance.pk)
        instance._old_opening_balance_quantity = old_product.opening_balance_quantity
        instance._old_opening_balance_cost = old_product.opening_balance_cost
        instance._old_opening_balance_warehouse = old_product.opening_balance_warehouse
    except Product.DoesNotExist:
        pass


@receiver(post_save, sender=Product)
def create_or_update_opening_balance_movement(sender, instance, created, **kwargs):
    """
    إنشاء أو تحديث حركة المخزون للرصيد الافتتاحي
    """
    from inventory.models import InventoryMovement
    from journal.models import JournalEntry, JournalLine, Account
    from django.utils import timezone
    from django.contrib.auth import get_user_model
    from core.models import DocumentSequence
    
    User = get_user_model()
    
    # تجاهل المنتجات الخدمية
    if instance.is_service:
        return
    
    # تحقق من وجود رصيد افتتاحي
    if instance.opening_balance_quantity <= 0:
        # حذف حركة المخزون إن وجدت
        InventoryMovement.objects.filter(
            product=instance,
            reference_type='opening_balance'
        ).delete()
        return
    
    # تحقق من وجود مستودع
    if not instance.opening_balance_warehouse:
        return
    
    # حساب تكلفة الوحدة
    unit_cost = instance.opening_balance_cost / instance.opening_balance_quantity if instance.opening_balance_quantity > 0 else Decimal('0')
    
    # الحصول على مستخدم للتعيين
    user = User.objects.first()
    if not user:
        return
    
    # توليد رقم الحركة
    try:
        seq = DocumentSequence.objects.get(document_type='inventory_movement')
        movement_number = seq.get_next_number()
    except DocumentSequence.DoesNotExist:
        movement_number = f'OB-{instance.code}-{timezone.now().strftime("%Y%m%d%H%M%S")}'
    
    # إنشاء أو تحديث حركة المخزون
    movement, movement_created = InventoryMovement.objects.update_or_create(
        product=instance,
        reference_type='opening_balance',
        defaults={
            'movement_number': movement_number,
            'warehouse': instance.opening_balance_warehouse,
            'movement_type': 'in',
            'reference_id': 0,
            'quantity': instance.opening_balance_quantity,
            'unit_cost': unit_cost,
            'total_cost': instance.opening_balance_cost,
            'date': timezone.now().date(),
            'notes': f'الرصيد الافتتاحي للمنتج {instance.name}',
            'created_by': user,
        }
    )
    
    # إنشاء قيد اليومية للرصيد الافتتاحي (إذا كان إنشاء جديد)
    if movement_created:
        try:
            # البحث عن حساب المخزون (1501)
            inventory_account = Account.objects.filter(code='1501').first()
            # البحث عن حساب رأس المال أو الأرباح المحتجزة (301)
            equity_account = Account.objects.filter(code='301').first()
            
            if inventory_account and equity_account:
                # إنشاء قيد اليومية
                journal_entry = JournalEntry.objects.create(
                    entry_date=timezone.now().date(),
                    entry_type='daily',
                    reference_type='manual',
                    description=f'رصيد افتتاحي - {instance.name} ({instance.code})',
                    total_amount=instance.opening_balance_cost,
                    created_by=movement.warehouse.manager if hasattr(movement.warehouse, 'manager') else None,
                )
                
                # إنشاء أطراف القيد
                # مدين: المخزون
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=inventory_account,
                    debit=instance.opening_balance_cost,
                    credit=Decimal('0'),
                    line_description=f'رصيد افتتاحي - {instance.name}'
                )
                
                # دائن: حقوق الملكية
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=equity_account,
                    debit=Decimal('0'),
                    credit=instance.opening_balance_cost,
                    line_description=f'رصيد افتتاحي - {instance.name}'
                )
                
                # تحديث أرصدة الحسابات
                inventory_account.update_account_balance()
                equity_account.update_account_balance()
        except Exception as e:
            # في حالة حدوث خطأ في إنشاء القيد، نستمر (الحركة موجودة على الأقل)
            print(f"خطأ في إنشاء قيد اليومية للرصيد الافتتاحي: {e}")

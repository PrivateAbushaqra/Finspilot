"""
إشارات لنظام المنتجات
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Product
from core.models import AuditLog
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
def create_opening_balance_on_new_product(sender, instance, created, **kwargs):
    """
    إنشاء حركة المخزون والقيد المحاسبي للرصيد الافتتاحي عند إنشاء منتج جديد فقط
    ملاحظة: التحديثات تتم من خلال views.py مباشرة
    ملاحظة: تم تعطيل هذه الإشارة لأن إنشاء حركات المخزون يتم من خلال views.py
    """
    # تعطيل الإشارة - يتم إنشاء حركات المخزون من views.py
    return
    
    # هذه الإشارة تعمل فقط عند إنشاء منتج جديد
    if not created:
        return
    
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
    
    # إنشاء حركة المخزون
    try:
        movement = InventoryMovement.objects.create(
            movement_number=movement_number,
            product=instance,
            warehouse=instance.opening_balance_warehouse,
            movement_type='in',
            reference_type='opening_balance',
            reference_id=instance.id,
            quantity=instance.opening_balance_quantity,
            unit_cost=unit_cost,
            total_cost=instance.opening_balance_cost,
            date=timezone.now().date(),
            notes=f'الرصيد الافتتاحي للمنتج {instance.name}',
            created_by=user,
        )
        
        # تسجيل في سجل الأنشطة
        AuditLog.objects.create(
            user=user,
            action_type='create',
            content_type='InventoryMovement',
            object_id=movement.id,
            description=f'إنشاء حركة مخزون للرصيد الافتتاحي - المنتج: {instance.name} - الكمية: {instance.opening_balance_quantity} - التكلفة: {instance.opening_balance_cost}',
            ip_address='127.0.0.1'
        )
    except Exception as e:
        print(f"خطأ في إنشاء حركة المخزون للرصيد الافتتاحي: {e}")
        return
    
    # إنشاء قيد اليومية للرصيد الافتتاحي (حسب IFRS)
    try:
        # البحث عن حساب المخزون (1501) - Assets (IAS 2: Inventories)
        inventory_account = Account.objects.filter(code='1501').first()
        # البحث عن حساب حقوق الملكية (301) - Equity (IAS 1)
        equity_account = Account.objects.filter(code='301').first()
        
        if inventory_account and equity_account and instance.opening_balance_cost > 0:
            # توليد رقم القيد
            try:
                seq = DocumentSequence.objects.get(document_type='journal')
                entry_number = seq.get_next_number()
            except DocumentSequence.DoesNotExist:
                last_entry = JournalEntry.objects.order_by('-id').first()
                if last_entry and last_entry.entry_number:
                    try:
                        last_num = int(last_entry.entry_number.split('-')[-1])
                        entry_number = f'JE-{last_num + 1:06d}'
                    except:
                        entry_number = f'JE-{timezone.now().strftime("%Y%m%d%H%M%S")}'
                else:
                    entry_number = 'JE-000001'
            
            # إنشاء قيد اليومية (IFRS Compliant)
            journal_entry = JournalEntry.objects.create(
                entry_number=entry_number,
                entry_date=timezone.now().date(),
                entry_type='daily',
                reference_type='manual',
                description=f'رصيد افتتاحي - {instance.name} ({instance.code})',
                total_amount=instance.opening_balance_cost,
                created_by=user,
            )
            
            # إنشاء أطراف القيد
            # مدين: المخزون (أصل) - IAS 2: Inventories should be measured at cost
            JournalLine.objects.create(
                journal_entry=journal_entry,
                account=inventory_account,
                debit=instance.opening_balance_cost,
                credit=Decimal('0'),
                line_description=f'رصيد افتتاحي - {instance.name}'
            )
            
            # دائن: حقوق الملكية - IAS 1: Opening balances affect equity
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
            
            # تسجيل في سجل الأنشطة
            AuditLog.objects.create(
                user=user,
                action_type='create',
                content_type='JournalEntry',
                object_id=journal_entry.id,
                description=f'إنشاء قيد محاسبي للرصيد الافتتاحي - المنتج: {instance.name} - رقم القيد: {entry_number} - المبلغ: {instance.opening_balance_cost}',
                ip_address='127.0.0.1'
            )
    except Exception as e:
        # في حالة حدوث خطأ في إنشاء القيد، نسجل الخطأ
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"خطأ في إنشاء قيد اليومية للرصيد الافتتاحي: {e}")

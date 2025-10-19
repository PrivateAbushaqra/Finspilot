from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from core.signals import log_activity
from .models import Asset, Liability, AssetCategory, LiabilityCategory, DepreciationEntry
from journal.services import JournalService
from journal.models import Account


@receiver(post_save, sender=Asset)
def log_asset_changes(sender, instance, created, **kwargs):
    """تسجيل إضافة أو تعديل أصل في سجل الانشطة"""
    action = _('Created') if created else _('Updated')
    description = f"{action} Asset: {instance.asset_number} - {instance.name}"
    log_activity(instance.created_by, 'create' if created else 'update', instance, description)


@receiver(post_delete, sender=Asset)
def log_asset_deletion(sender, instance, **kwargs):
    """تسجيل حذف أصل في سجل الانشطة"""
    description = f"Deleted Asset: {instance.asset_number} - {instance.name}"
    log_activity(instance.created_by, 'delete', instance, description)


@receiver(post_save, sender=Liability)
def log_liability_changes(sender, instance, created, **kwargs):
    """تسجيل إضافة أو تعديل خصم في سجل الانشطة"""
    action = _('Created') if created else _('Updated')
    description = f"{action} Liability: {instance.liability_number} - {instance.name}"
    log_activity(instance.created_by, 'create' if created else 'update', instance, description)


@receiver(post_delete, sender=Liability)
def log_liability_deletion(sender, instance, **kwargs):
    """تسجيل حذف خصم في سجل الانشطة"""
    description = f"Deleted Liability: {instance.liability_number} - {instance.name}"
    log_activity(instance.created_by, 'delete', instance, description)


@receiver(post_save, sender=AssetCategory)
def log_asset_category_changes(sender, instance, created, **kwargs):
    """تسجيل إضافة أو تعديل فئة أصل في سجل الانشطة"""
    action = _('Created') if created else _('Updated')
    description = f"{action} Asset Category: {instance.name}"
    log_activity(instance.created_by, 'create' if created else 'update', instance, description)


@receiver(post_save, sender=LiabilityCategory)
def log_liability_category_changes(sender, instance, created, **kwargs):
    """تسجيل إضافة أو تعديل فئة خصم في سجل الانشطة"""
    action = _('Created') if created else _('Updated')
    description = f"{action} Liability Category: {instance.name}"
    log_activity(instance.created_by, 'create' if created else 'update', instance, description)


@receiver(post_save, sender=DepreciationEntry)
def log_depreciation_entry(sender, instance, created, **kwargs):
    """تسجيل إضافة أو تعديل سجل التخفيض في سجل الانشطة"""
    action = _('Created') if created else _('Updated')
    description = f"{action} Depreciation Entry: {instance.id} - {instance.notes or 'إهلاك'}"
    log_activity(instance.created_by, 'create' if created else 'update', instance, description)


@receiver(post_save, sender=Asset)
def create_asset_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي عند إضافة أصل"""
    if created and instance.category and instance.category.account:
        # الحصول على حساب نقد افتراضي
        cash_account = Account.objects.filter(code__startswith='101', account_type='asset').first()
        if not cash_account:
            # إنشاء حساب نقد إذا لم يوجد
            cash_account = Account.objects.create(
                code='101001',
                name='الصندوق النقدي الرئيسي',
                account_type='asset',
                description='حساب الصندوق النقدي الرئيسي'
            )
        
        # إنشاء القيد
        lines_data = [
            {
                'account_id': instance.category.account.id,
                'debit': instance.purchase_cost,
                'credit': 0,
                'description': f'شراء أصل: {instance.name}'
            },
            {
                'account_id': cash_account.id,
                'debit': 0,
                'credit': instance.purchase_cost,
                'description': f'دفع ثمن أصل: {instance.name}'
            }
        ]
        
        JournalService.create_journal_entry(
            entry_date=instance.purchase_date,
            reference_type='manual',  # أو 'asset_purchase'
            description=f'قيد شراء الأصل {instance.name}',
            lines_data=lines_data,
            reference_id=instance.id,
            user=instance.created_by
        )


@receiver(post_save, sender=Liability)
def create_liability_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي عند إضافة خصم"""
    if created and instance.category and instance.category.account:
        # الحصول على حساب نقد افتراضي
        cash_account = Account.objects.filter(code__startswith='101', account_type='asset').first()
        if not cash_account:
            cash_account = Account.objects.create(
                code='101001',
                name='الصندوق النقدي الرئيسي',
                account_type='asset',
                description='حساب الصندوق النقدي الرئيسي'
            )
        
        # إنشاء القيد
        lines_data = [
            {
                'account_id': cash_account.id,
                'debit': instance.original_amount,
                'credit': 0,
                'description': f'استلام خصم: {instance.name}'
            },
            {
                'account_id': instance.category.account.id,
                'debit': 0,
                'credit': instance.original_amount,
                'description': f'خصم: {instance.name}'
            }
        ]
        
        JournalService.create_journal_entry(
            entry_date=instance.start_date,
            reference_type='manual',
            description=f'قيد إضافة الخصم {instance.name}',
            lines_data=lines_data,
            reference_id=instance.id,
            user=instance.created_by
        )


@receiver(post_save, sender=DepreciationEntry)
def create_depreciation_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي عند إضافة قيد إهلاك"""
    if created and instance.asset.category:
        category = instance.asset.category
        if category.depreciation_expense_account and category.accumulated_depreciation_account:
            # إنشاء القيد
            lines_data = [
                {
                    'account_id': category.depreciation_expense_account.id,
                    'debit': instance.depreciation_amount,
                    'credit': 0,
                    'description': f'إهلاك الأصل: {instance.asset.name}'
                },
                {
                    'account_id': category.accumulated_depreciation_account.id,
                    'debit': 0,
                    'credit': instance.depreciation_amount,
                    'description': f'تراكمي الإهلاك: {instance.asset.name}'
                }
            ]
            
            JournalService.create_journal_entry(
                entry_date=instance.depreciation_date,
                reference_type='asset_depreciation',
                description=f'قيد إهلاك الأصل {instance.asset.name}',
                lines_data=lines_data,
                reference_id=instance.id,
                user=instance.created_by
            )
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from core.signals import log_activity
from .models import Asset, Liability, AssetCategory, LiabilityCategory


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
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Cashbox
from journal.services import JournalService
from core.signals import log_view_activity
from django.utils.translation import gettext_lazy as _


@receiver(post_save, sender=Cashbox)
def create_cashbox_account(sender, instance, created, **kwargs):
    """إنشاء حساب محاسبي للصندوق عند إنشائه"""
    if created:
        try:
            # إنشاء حساب الصندوق تلقائياً
            account = JournalService.get_cashbox_account(instance)
            
            print(f"تم إنشاء حساب محاسبي للصندوق: {instance.name} - كود: {account.code}")
        except Exception as e:
            print(f"خطأ في إنشاء حساب الصندوق {instance.name}: {e}")
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Cashbox
from journal.services import JournalService
from core.signals import log_view_activity
from django.utils.translation import gettext_lazy as _


from .models import CashboxTransaction


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


@receiver(post_save, sender=CashboxTransaction)
def update_cashbox_balance(sender, instance, created, **kwargs):
    """تحديث رصيد الصندوق عند إنشاء معاملة جديدة"""
    if created:
        try:
            cashbox = instance.cashbox
            
            # تحديث الرصيد حسب نوع المعاملة أو المبلغ
            # إذا كان المبلغ سالباً، فهو سحب (withdrawal)
            # إذا كان المبلغ موجباً، فهو إيداع (deposit)
            
            if instance.amount < 0:
                # المبلغ سالب = سحب
                cashbox.balance += instance.amount  # نضيف السالب (أي نطرح)
            else:
                # المبلغ موجب = إيداع
                cashbox.balance += instance.amount
            
            cashbox.save()
            print(f"✓ تم تحديث رصيد الصندوق {cashbox.name}: {cashbox.balance}")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'خطأ في تحديث رصيد الصندوق: {e}')
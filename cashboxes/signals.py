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
            
            # تسجيل النشاط في سجل الأنشطة
            try:
                from core.models import AuditLog
                AuditLog.objects.create(
                    user=None,  # لا يوجد مستخدم محدد في الإشارات
                    action_type='create',
                    content_type='Account',
                    object_id=account.id,
                    description=f'إنشاء حساب محاسبي تلقائي للصندوق: {instance.name}',
                    ip_address='system'
                )
            except Exception as e:
                pass  # لا نريد أن يفشل إنشاء الحساب بسبب تسجيل النشاط
            
            print(f"تم إنشاء حساب محاسبي للصندوق: {instance.name} - كود: {account.code}")
        except Exception as e:
            print(f"خطأ في إنشاء حساب الصندوق {instance.name}: {e}")
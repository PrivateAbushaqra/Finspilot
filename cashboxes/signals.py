from django.db.models.signals import post_save, post_delete
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


@receiver(post_delete, sender=Cashbox)
def delete_cashbox_account(sender, instance, **kwargs):
    """
    حذف أو تعطيل حساب الصندوق عند حذفه
    """
    try:
        from journal.models import Account
        from core.signals import log_activity
        from core.middleware import get_current_user

        # البحث عن الحساب المرتبط بالصندوق
        # الحسابات تُنشأ بأكواد مثل 101xxx
        code = f'101{instance.id:03d}'
        account = Account.objects.filter(code=code).first()

        if account:
            # التحقق من وجود حركات في الحساب
            has_movements = account.journal_lines.exists()

            if has_movements:
                # إذا كان الحساب يحتوي على حركات، عطلها بدلاً من حذفها
                account.is_active = False
                account.save(update_fields=['is_active'])
                
                # تسجيل النشاط
                user = get_current_user()
                if user:
                    log_activity(user, 'UPDATE', account, f'تم تعطيل حساب الصندوق {account.name} (يحتوي على حركات)')
                
                print(f"✓ تم تعطيل حساب {account.code} - {account.name} (يحتوي على حركات)")
            else:
                # إذا لم يكن يحتوي على حركات، احذفه
                account_name = account.name
                
                # تسجيل النشاط قبل الحذف
                user = get_current_user()
                if user:
                    log_activity(user, 'DELETE', account, f'تم حذف حساب الصندوق {account_name}')
                
                account.delete()
                print(f"✓ تم حذف حساب {account.code} - {account.name}")

    except Exception as e:
        print(f"❌ خطأ في حذف/تعطيل حساب الصندوق: {e}")
        import traceback
        traceback.print_exc()
"""
إشارات نظام المخزون
تنشئ الحسابات المحاسبية تلقائياً عند إنشاء المستودعات
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Warehouse

@receiver(post_save, sender=Warehouse)
def create_warehouse_account(sender, instance, created, **kwargs):
    """
    إنشاء حساب محاسبي للمستودع عند إنشائه
    """
    if not created:
        return

    try:
        from journal.models import Account

        # الحصول على حساب المخزون الرئيسي
        parent_account = Account.objects.filter(code='1201').first()
        if not parent_account:
            print("⚠️ لا يوجد حساب مخزون رئيسي (1201)")
            return

        # إنشاء رمز فريد للمستودع
        code = f"1201{instance.id:04d}"

        # التأكد من عدم وجود حساب بنفس الرمز
        if not Account.objects.filter(code=code).exists():
            Account.objects.create(
                code=code,
                name=f'مستودع - {instance.name}',
                account_type='asset',
                parent=parent_account,
                description=f'حساب المستودع {instance.name}'
            )

    except Exception as e:
        print(f"خطأ في إنشاء حساب المستودع: {e}")


@receiver(post_delete, sender=Warehouse)
def delete_warehouse_account(sender, instance, **kwargs):
    """
    حذف أو تعطيل حساب المستودع عند حذفه
    """
    try:
        from journal.models import Account
        from core.signals import log_activity
        from core.middleware import get_current_user

        # البحث عن الحساب المرتبط بالمستودع
        # الحسابات تُنشأ بأكواد مثل 1201xxxx
        code = f"1201{instance.id:04d}"
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
                    log_activity(user, 'UPDATE', account, f'تم تعطيل حساب المستودع {account.name} (يحتوي على حركات)')
                
                print(f"✓ تم تعطيل حساب {account.code} - {account.name} (يحتوي على حركات)")
            else:
                # إذا لم يكن يحتوي على حركات، احذفه
                account_name = account.name
                
                # تسجيل النشاط قبل الحذف
                user = get_current_user()
                if user:
                    log_activity(user, 'DELETE', account, f'تم حذف حساب المستودع {account_name}')
                
                account.delete()
                print(f"✓ تم حذف حساب {account.code} - {account.name}")

    except Exception as e:
        print(f"❌ خطأ في حذف/تعطيل حساب المستودع: {e}")
        import traceback
        traceback.print_exc()
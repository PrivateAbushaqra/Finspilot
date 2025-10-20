"""
إشارات نظام المخزون
تنشئ الحسابات المحاسبية تلقائياً عند إنشاء المستودعات
"""

from django.db.models.signals import post_save
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
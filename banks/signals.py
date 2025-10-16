"""
Signals for Bank Accounts and Transactions
معالجة الإشارات التلقائية للحسابات البنكية والمعاملات
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal

from .models import BankTransaction


@receiver(post_save, sender=BankTransaction)
def update_bank_balance_on_transaction(sender, instance, created, **kwargs):
    """
    تحديث رصيد البنك تلقائياً عند إنشاء معاملة بنكية
    Update bank balance automatically when bank transaction is created
    """
    if created and instance.bank:
        bank = instance.bank
        
        print(f"  DEBUG: رصيد البنك قبل التحديث: {bank.balance}, المبلغ: {instance.amount}")
        
        # تحديث الرصيد حسب علامة المبلغ
        # إذا كان المبلغ سالباً، فهو سحب (withdrawal)
        # إذا كان المبلغ موجباً، فهو إيداع (deposit)
        if instance.amount < 0:
            # المبلغ سالب = سحب
            bank.balance += instance.amount  # نضيف السالب (أي نطرح)
        else:
            # المبلغ موجب = إيداع
            bank.balance += instance.amount
        
        print(f"  DEBUG: رصيد البنك بعد الحساب: {bank.balance}")
        bank.save(update_fields=['balance'])
        print(f"✓ تم تحديث رصيد البنك {bank.name}: {bank.balance}")
        
        # التحقق من الحفظ
        bank.refresh_from_db()
        print(f"  DEBUG: رصيد البنك بعد refresh: {bank.balance}")


@receiver(post_delete, sender=BankTransaction)
def update_bank_balance_on_transaction_delete(sender, instance, **kwargs):
    """
    تحديث رصيد البنك عند حذف معاملة بنكية
    Update bank balance when bank transaction is deleted
    """
    if instance.bank:
        bank = instance.bank
        
        # عكس التأثير على الرصيد
        if instance.amount < 0:
            # المبلغ كان سالباً (سحب)، نعيده (نضيف موجب)
            bank.balance -= instance.amount  # نطرح السالب (أي نضيف)
        else:
            # المبلغ كان موجباً (إيداع)، نعكسه (نطرح)
            bank.balance -= instance.amount
        
        bank.save(update_fields=['balance'])
        print(f"✓ تم تحديث رصيد البنك بعد الحذف {bank.name}: {bank.balance}")

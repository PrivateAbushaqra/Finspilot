"""
Signals for Bank Accounts and Transactions
معالجة الإشارات التلقائية للحسابات البنكية والمعاملات
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal

from .models import BankTransaction, BankAccount
from journal.services import JournalService
from journal.models import Account


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

@receiver(post_save, sender=BankAccount)
def create_bank_account_opening_balance_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي لرصيد افتتاحي عند إنشاء حساب بنكي"""
    if created and instance.initial_balance != 0:
        try:
            # الحصول على حساب البنك
            bank_account = JournalService.get_or_create_bank_account(instance)
            
            # الحصول على حساب رأس المال
            capital_account = Account.objects.filter(code='301').first()
            if not capital_account:
                capital_account = Account.objects.create(
                    code='301',
                    name='رأس المال',
                    account_type='equity',
                    description='حساب رأس المال'
                )
            
            lines_data = [
                {
                    'account_id': bank_account.id,
                    'debit': instance.initial_balance,
                    'credit': 0,
                    'description': f'رصيد افتتاحي لحساب {instance.name}'
                },
                {
                    'account_id': capital_account.id,
                    'debit': 0,
                    'credit': instance.initial_balance,
                    'description': f'رصيد افتتاحي لحساب {instance.name}'
                }
            ]
            
            JournalService.create_journal_entry(
                entry_date=instance.created_at.date(),
                reference_type='manual',
                description=f'رصيد افتتاحي لحساب البنك {instance.name}',
                lines_data=lines_data,
                reference_id=instance.id,
                user=instance.created_by
            )
        except Exception as e:
            print(f"خطأ في إنشاء قيد الرصيد الافتتاحي: {e}")

@receiver(post_save, sender=BankTransaction)
def create_bank_transaction_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي عند إنشاء معاملة بنكية"""
    if created:
        # إذا تم وضع علامة داخل الكائن لعدم إنشاء القيد (عند إنشاء المعاملات كجزء من تحويل)، تجاهل
        if getattr(instance, '_skip_journal', False):
            print(f"DEBUG: تخطي إنشاء القيد التلقائي للمعاملة البنكية {getattr(instance, 'reference_number', '')} بسبب _skip_journal")
            return
        try:
            bank_account = JournalService.get_or_create_bank_account(instance.bank)
            
            lines_data = []
            if instance.transaction_type == 'deposit':
                # إيداع: مدين البنك، دائن حساب الإيراد أو النقد
                # افتراضياً دائن لحساب إيراد بنكي أو رأس المال
                capital_account = Account.objects.filter(code='301').first()
                if not capital_account:
                    capital_account = Account.objects.create(
                        code='301',
                        name='رأس المال',
                        account_type='equity'
                    )
                
                lines_data = [
                    {
                        'account_id': bank_account.id,
                        'debit': instance.amount,
                        'credit': 0,
                        'description': f'إيداع في {instance.bank.name}: {instance.description}'
                    },
                    {
                        'account_id': capital_account.id,
                        'debit': 0,
                        'credit': instance.amount,
                        'description': f'إيداع في {instance.bank.name}: {instance.description}'
                    }
                ]
            elif instance.transaction_type == 'withdrawal':
                # سحب: دائن البنك، مدين حساب المصروف
                # استخدام حساب المصروفات المتنوعة 6010 بدلاً من 401 (الذي هو حساب المبيعات!)
                expense_account = Account.objects.filter(code='6010').first()
                if not expense_account:
                    expense_account = Account.objects.create(
                        code='6010',
                        name='مصروفات متنوعة',
                        account_type='expense',
                        description='حساب المصروفات المتنوعة'
                    )
                
                lines_data = [
                    {
                        'account_id': expense_account.id,
                        'debit': instance.amount,
                        'credit': 0,
                        'description': f'سحب من {instance.bank.name}: {instance.description}'
                    },
                    {
                        'account_id': bank_account.id,
                        'debit': 0,
                        'credit': instance.amount,
                        'description': f'سحب من {instance.bank.name}: {instance.description}'
                    }
                ]
            
            if lines_data:
                # الحصول على مستخدم افتراضي إذا لم يكن محدد
                if not hasattr(instance, 'created_by') or not instance.created_by:
                    from users.models import User
                    default_user = User.objects.filter(is_superuser=True).first()
                    if not default_user:
                        default_user = User.objects.filter(is_active=True).first()
                else:
                    default_user = instance.created_by
                
                JournalService.create_journal_entry(
                    entry_date=instance.date,
                    reference_type='manual',
                    description=f'معاملة بنكية: {instance.get_transaction_type_display()} - {instance.description}',
                    lines_data=lines_data,
                    reference_id=instance.id,
                    user=default_user
                )
        except Exception as e:
            print(f"خطأ في إنشاء قيد المعاملة البنكية: {e}")

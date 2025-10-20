"""
اختبار تحويل بنكي للتأكد من عدم إنشاء حركة في حساب المبيعات (401)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from banks.models import BankAccount, BankTransfer, BankTransaction
from journal.models import Account, JournalEntry, JournalLine
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

def test_bank_transfer():
    """اختبار تحويل بنكي بين حسابين بنكيين"""

    print("اختبار تحويل بنكي")
    print("=" * 50)

    # الحصول على المستخدم super
    super_user = User.objects.filter(username='super').first()
    if not super_user:
        print("❌ لم يتم العثور على المستخدم 'super'")
        return False

    # الحصول على حسابين بنكيين
    bank_accounts = list(BankAccount.objects.all()[:2])
    if len(bank_accounts) < 2:
        # إنشاء حساب بنكي ثانٍ إذا لم يكن موجوداً
        if len(bank_accounts) == 1:
            second_bank = BankAccount.objects.create(
                name='بنك تجريبي',
                bank_name='تجريبي',
                account_number='1234567890',
                balance=Decimal('5000.000'),
                currency='JOD',
                created_by=super_user
            )
            bank_accounts.append(second_bank)
        else:
            print("❌ لا توجد حسابات بنكية")
            return False

    from_account = bank_accounts[0]
    to_account = bank_accounts[1]

    print(f"📋 تحويل من: {from_account.name} (رصيد: {from_account.balance})")
    print(f"   إلى: {to_account.name} (رصيد: {to_account.balance})")

    # حفظ الأرصدة الأصلية
    original_from_balance = from_account.balance
    original_to_balance = to_account.balance

    # عدد القيود قبل التحويل
    initial_journal_count = JournalEntry.objects.count()

    # محاكاة تحويل 1000
    transfer_amount = Decimal('1000.000')

    print(f"\n🔄 إنشاء تحويل بمبلغ: {transfer_amount}")

    # إنشاء التحويل (محاكاة ما يحدث في View)
    from django.db import transaction
    from core.models import DocumentSequence

    with transaction.atomic():
        # الحصول على رقم التحويل
        sequence = DocumentSequence.objects.get(document_type='bank_transfer')
        transfer_number = sequence.get_next_number()

        # إنشاء التحويل
        transfer = BankTransfer.objects.create(
            transfer_number=transfer_number,
            date=timezone.now().date(),
            from_account=from_account,
            to_account=to_account,
            amount=transfer_amount,
            fees=Decimal('0'),
            exchange_rate=Decimal('1'),
            description='اختبار تحويل بنكي',
            created_by=super_user
        )

        # إنشاء معاملات البنك مع _skip_journal
        withdrawal = BankTransaction(
            bank=from_account,
            transaction_type='withdrawal',
            amount=transfer_amount,
            description=f'تحويل إلى حساب {to_account.name} - رقم التحويل: {transfer_number}',
            reference_number=transfer_number,
            date=transfer.date,
            created_by=super_user
        )
        withdrawal._skip_journal = True
        withdrawal.save()

        deposit = BankTransaction(
            bank=to_account,
            transaction_type='deposit',
            amount=transfer_amount,
            description=f'تحويل من حساب {from_account.name} - رقم التحويل: {transfer_number}',
            reference_number=transfer_number,
            date=transfer.date,
            created_by=super_user
        )
        deposit._skip_journal = True
        deposit.save()

        # إنشاء القيد المحاسبي
        from journal.services import JournalService
        journal_entry = JournalService.create_bank_transfer_entry(transfer, super_user)

    print(f"✅ تم إنشاء التحويل رقم: {transfer.transfer_number}")
    print(f"✅ تم إنشاء القيد المحاسبي رقم: {journal_entry.entry_number}")

    # التحقق من الأرصدة بعد التحويل
    from_account.refresh_from_db()
    to_account.refresh_from_db()

    print(f"\n📊 الأرصدة بعد التحويل:")
    print(f"   {from_account.name}: {from_account.balance} (كان: {original_from_balance})")
    print(f"   {to_account.name}: {to_account.balance} (كان: {original_to_balance})")

    # التحقق من القيد المحاسبي
    print(f"\n📊 تفاصيل القيد المحاسبي:")
    for line in journal_entry.journalline_set.all():
        account = line.account
        print(f"   {account.code} - {account.name}: مدين={line.debit}, دائن={line.credit}")

    # التحقق من عدم وجود قيود إضافية في حساب 401
    sales_account = Account.objects.filter(code='401').first()
    if sales_account:
        sales_lines = JournalLine.objects.filter(account=sales_account, journal_entry__reference_type='manual')
        if sales_lines.exists():
            print(f"\n❌ تحذير: تم العثور على حركات في حساب المبيعات (401)!")
            for line in sales_lines:
                print(f"   قيد {line.journal_entry.entry_number}: مدين={line.debit}, دائن={line.credit}")
        else:
            print(f"\n✅ لا توجد حركات في حساب المبيعات (401)")
    else:
        print(f"\n✅ حساب المبيعات (401) غير موجود أو غير مستخدم")
    
    # عدد القيود بعد التحويل
    final_journal_count = JournalEntry.objects.count()
    print(f"\n📊 عدد القيود: قبل={initial_journal_count}, بعد={final_journal_count} (+{final_journal_count - initial_journal_count})")

    # تنظيف البيانات التجريبية
    print(f"\n🧹 تنظيف البيانات التجريبية...")
    transfer.delete()  # سيحذف القيد تلقائياً عبر الإشارة
    withdrawal.delete()
    deposit.delete()

    # إعادة الأرصدة
    from_account.balance = original_from_balance
    from_account.save()
    to_account.balance = original_to_balance
    to_account.save()

    print("✅ تم التنظيف")
    print("\n🎉 الاختبار مكتمل!")

    return True

if __name__ == '__main__':
    test_bank_transfer()
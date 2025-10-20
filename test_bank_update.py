"""
اختبار تعديل رصيد حساب بنكي موجود
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from banks.models import BankAccount, BankTransaction
from journal.models import Account, JournalEntry, JournalLine
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

def test_bank_balance_update():
    """اختبار تعديل رصيد حساب بنكي موجود"""

    print("اختبار تعديل رصيد حساب بنكي موجود")
    print("=" * 60)

    # الحصول على المستخدم super
    super_user = User.objects.filter(username='super').first()
    if not super_user:
        print("❌ لم يتم العثور على المستخدم 'super'")
        return False

    # الحصول على أول حساب بنكي موجود
    bank_account = BankAccount.objects.first()
    if not bank_account:
        print("❌ لا توجد حسابات بنكية في النظام")
        return False

    print(f"📋 سيتم اختبار تعديل رصيد الحساب: {bank_account.name} (ID: {bank_account.id})")
    print(f"   الرصيد الحالي: {bank_account.balance}")
    print(f"   الرصيد الفعلي المحسوب: {bank_account.calculate_actual_balance()}")

    # حفظ القيم الأصلية
    original_balance = bank_account.balance
    original_actual_balance = bank_account.calculate_actual_balance()

    # محاكاة تعديل الرصيد (زيادة بمقدار 200)
    new_balance = original_actual_balance + Decimal('200.000')
    balance_difference = new_balance - original_actual_balance

    print(f"\n🔄 محاكاة تعديل الرصيد:")
    print(f"   الرصيد الجديد: {new_balance}")
    print(f"   الفرق: {balance_difference}")

    # حفظ عدد المعاملات والقيود قبل التعديل
    transactions_before = BankTransaction.objects.count()
    journal_entries_before = JournalEntry.objects.count()

    print(f"\n📊 قبل التعديل:")
    print(f"   معاملات بنكية: {transactions_before}")
    print(f"   قيود محاسبية: {journal_entries_before}")

    # محاكاة إنشاء معاملة بنكية للتعديل
    try:
        bank_transaction = BankTransaction.objects.create(
            bank=bank_account,
            date=timezone.now().date(),
            transaction_type='deposit',  # زيادة
            amount=abs(balance_difference),
            description='اختبار تعديل يدوي للرصيد - زيادة',
            reference_number=f'TEST-ADJ-{bank_account.id}-{timezone.now().strftime("%Y%m%d%H%M%S")}',
            adjustment_type='capital',  # مساهمة رأسمالية
            is_manual_adjustment=True,
            created_by=super_user
        )
        print(f"✅ تم إنشاء المعاملة البنكية: {bank_transaction}")

        # محاكاة إنشاء القيد المحاسبي
        from journal.services import JournalService
        from core.utils import get_adjustment_account_code

        bank_account_obj = JournalService.get_or_create_bank_account(bank_account)
        adjustment_account_code = get_adjustment_account_code('capital', is_bank=True)
        adjustment_account = Account.objects.filter(code=adjustment_account_code).first()

        if bank_account_obj and adjustment_account:
            print(f"📊 إنشاء القيد المحاسبي:")
            print(f"   حساب البنك: {bank_account_obj.code} - {bank_account_obj.name}")
            print(f"   حساب التعديل: {adjustment_account.code} - {adjustment_account.name}")

            # إنشاء بنود القيد
            lines_data = [
                {
                    'account_id': bank_account_obj.id,
                    'debit': abs(balance_difference),
                    'credit': Decimal('0'),
                    'description': f'زيادة رصيد الحساب البنكي: {bank_account.name}'
                },
                {
                    'account_id': adjustment_account.id,
                    'debit': Decimal('0'),
                    'credit': abs(balance_difference),
                    'description': f'مساهمة رأسمالية - تعديل رصيد بنكي'
                }
            ]

            # إنشاء القيد المحاسبي
            journal_entry = JournalService.create_journal_entry(
                entry_date=timezone.now().date(),
                description=f'تعديل رصيد الحساب البنكي: {bank_account.name} - مساهمة رأسمالية',
                reference_type='bank_adjustment',
                reference_id=bank_account.id,
                lines_data=lines_data,
                user=super_user
            )

            if journal_entry:
                print(f"✅ تم إنشاء القيد المحاسبي رقم: {journal_entry.entry_number}")

                # عرض بنود القيد
                journal_lines = JournalLine.objects.filter(journal_entry=journal_entry)
                print(f"   عدد بنود القيد: {journal_lines.count()}")

                for line in journal_lines:
                    print(f"   - {line.account.code}: مدين={line.debit}, دائن={line.credit}")
                    print(f"     الوصف: {line.line_description}")

                # تحديث رصيد الحساب البنكي
                bank_account.sync_balance()
                print(f"   الرصيد الجديد للحساب البنكي: {bank_account.balance}")

                # التحقق من الرصيد الفعلي
                actual_balance_after = bank_account.calculate_actual_balance()
                print(f"   الرصيد الفعلي المحسوب: {actual_balance_after}")

                # فحص الحساب المحاسبي
                bank_account_obj.refresh_from_db()
                print(f"   رصيد الحساب المحاسبي: {bank_account_obj.balance}")

                # التحقق من نجاح العملية
                if abs(actual_balance_after - new_balance) < Decimal('0.001'):
                    print("✅ تم تعديل الرصيد بنجاح وإنشاء جميع المستندات المحاسبية!")

                    # فحص الأرقام النهائية
                    transactions_after = BankTransaction.objects.count()
                    journal_entries_after = JournalEntry.objects.count()

                    print(f"\n📊 بعد التعديل:")
                    print(f"   معاملات بنكية: {transactions_after} (+{transactions_after - transactions_before})")
                    print(f"   قيود محاسبية: {journal_entries_after} (+{journal_entries_after - journal_entries_before})")

                    return True
                else:
                    print(f"❌ خطأ في حساب الرصيد: المتوقع {new_balance}, الفعلي {actual_balance_after}")
                    return False
            else:
                print("❌ فشل في إنشاء القيد المحاسبي")
                return False
        else:
            print("❌ لم يتم العثور على حسابات البنك أو التعديل")
            if not bank_account_obj:
                print("   - حساب البنك غير موجود")
            if not adjustment_account:
                print(f"   - حساب التعديل {adjustment_account_code} غير موجود")
            return False

    except Exception as e:
        print(f"❌ خطأ أثناء الاختبار: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_data():
    """تنظيف البيانات التجريبية"""
    try:
        # حذف المعاملات البنكية التجريبية
        test_transactions = BankTransaction.objects.filter(
            description__startswith='اختبار تعديل يدوي للرصيد'
        )
        deleted_count = test_transactions.count()
        test_transactions.delete()

        # حذف القيود المحاسبية التجريبية
        test_entries = JournalEntry.objects.filter(
            description__contains='تعديل رصيد الحساب البنكي',
            reference_type='bank_adjustment'
        )
        entries_deleted = test_entries.count()
        test_entries.delete()

        print(f"\n🧹 تم تنظيف {deleted_count} معاملة بنكية و {entries_deleted} قيد محاسبي تجريبي")

    except Exception as e:
        print(f"⚠️  خطأ في التنظيف: {e}")

if __name__ == '__main__':
    success = test_bank_balance_update()

    print("\n" + "=" * 60)
    if success:
        print("🎉 الاختبار نجح! النظام يعمل بشكل صحيح")
        print("✅ يتم إنشاء المستندات المحاسبية عند تعديل الرصيد")
    else:
        print("❌ الاختبار فشل! هناك مشكلة في النظام")

    # تنظيف البيانات التجريبية
    cleanup_test_data()

    print("=" * 60)

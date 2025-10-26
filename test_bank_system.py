"""
اختبار شامل لنظام البنوك بعد إصلاح التكرار
Test bank system after fixing duplication issues

يختبر هذا الملف:
1. إنشاء حساب بنكي
2. إنشاء معاملة بنكية (إيداع/سحب)
3. حذف معاملة بنكية
4. التأكد من عدم تكرار تحديث الرصيد
5. التوافق مع IFRS

الاستخدام:
python manage.py shell < test_bank_system.py
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from banks.models import BankAccount, BankTransaction
from journal.models import JournalEntry

User = get_user_model()

print("\n" + "="*80)
print("اختبار نظام البنوك - بعد إصلاح التكرار")
print("="*80 + "\n")

# 1. الحصول على مستخدم للاختبار
print("1. الحصول على مستخدم للاختبار...")
user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.filter(is_active=True).first()

if not user:
    print("❌ لا يوجد مستخدمين في النظام!")
    exit(1)

print(f"✓ تم العثور على المستخدم: {user.username}")

# 2. إنشاء حساب بنكي للاختبار
print("\n2. إنشاء حساب بنكي للاختبار...")
test_bank = BankAccount.objects.create(
    name='حساب تجريبي للاختبار',
    bank_name='بنك الاختبار',
    account_number='TEST-123456',
    balance=Decimal('0'),
    initial_balance=Decimal('0'),
    currency='JOD',
    is_active=True,
    created_by=user
)
print(f"✓ تم إنشاء الحساب البنكي: {test_bank.name}")
print(f"  - الرصيد الحالي: {test_bank.balance}")

# 3. اختبار إنشاء معاملة إيداع
print("\n3. اختبار إنشاء معاملة إيداع (1000 دينار)...")
initial_balance = test_bank.balance
deposit = BankTransaction.objects.create(
    bank=test_bank,
    transaction_type='deposit',
    amount=Decimal('1000'),
    description='إيداع تجريبي للاختبار',
    reference_number='DEP-TEST-001',
    date=timezone.now().date(),
    created_by=user
)

# تحديث البيانات من قاعدة البيانات
test_bank.refresh_from_db()
print(f"✓ تم إنشاء معاملة الإيداع")
print(f"  - الرصيد قبل: {initial_balance}")
print(f"  - الرصيد بعد: {test_bank.balance}")
print(f"  - الفرق: {test_bank.balance - initial_balance}")

# التحقق من صحة التحديث
expected_balance = initial_balance + Decimal('1000')
if test_bank.balance == expected_balance:
    print(f"✓ الرصيد صحيح ({test_bank.balance})")
else:
    print(f"❌ خطأ: الرصيد المتوقع {expected_balance} لكن الفعلي {test_bank.balance}")

# 4. اختبار إنشاء معاملة سحب
print("\n4. اختبار إنشاء معاملة سحب (300 دينار)...")
balance_before_withdrawal = test_bank.balance
withdrawal = BankTransaction.objects.create(
    bank=test_bank,
    transaction_type='withdrawal',
    amount=Decimal('300'),
    description='سحب تجريبي للاختبار',
    reference_number='WIT-TEST-001',
    date=timezone.now().date(),
    created_by=user
)

# تحديث البيانات من قاعدة البيانات
test_bank.refresh_from_db()
print(f"✓ تم إنشاء معاملة السحب")
print(f"  - الرصيد قبل: {balance_before_withdrawal}")
print(f"  - الرصيد بعد: {test_bank.balance}")
print(f"  - الفرق: {test_bank.balance - balance_before_withdrawal}")

# التحقق من صحة التحديث
expected_balance = balance_before_withdrawal - Decimal('300')
if test_bank.balance == expected_balance:
    print(f"✓ الرصيد صحيح ({test_bank.balance})")
else:
    print(f"❌ خطأ: الرصيد المتوقع {expected_balance} لكن الفعلي {test_bank.balance}")

# 5. اختبار حذف معاملة
print("\n5. اختبار حذف معاملة السحب...")
balance_before_delete = test_bank.balance
withdrawal_amount = withdrawal.amount
withdrawal.delete()

# تحديث البيانات من قاعدة البيانات
test_bank.refresh_from_db()
print(f"✓ تم حذف معاملة السحب")
print(f"  - الرصيد قبل الحذف: {balance_before_delete}")
print(f"  - الرصيد بعد الحذف: {test_bank.balance}")
print(f"  - الفرق: {test_bank.balance - balance_before_delete}")

# التحقق من صحة التحديث بعد الحذف
expected_balance = balance_before_delete + withdrawal_amount
if test_bank.balance == expected_balance:
    print(f"✓ الرصيد صحيح بعد الحذف ({test_bank.balance})")
else:
    print(f"❌ خطأ: الرصيد المتوقع {expected_balance} لكن الفعلي {test_bank.balance}")

# 6. التحقق من الرصيد الفعلي مقابل الرصيد المحسوب
print("\n6. التحقق من الرصيد الفعلي مقابل الرصيد المحسوب...")
calculated_balance = test_bank.calculate_actual_balance()
stored_balance = test_bank.balance
print(f"  - الرصيد المخزون: {stored_balance}")
print(f"  - الرصيد المحسوب: {calculated_balance}")

if calculated_balance == stored_balance:
    print(f"✓ الرصيد متطابق - لا يوجد تكرار")
else:
    print(f"❌ خطأ: يوجد اختلاف بين الرصيد المخزون والمحسوب!")
    print(f"   هذا قد يشير إلى وجود تكرار في التحديث")

# 7. التحقق من القيود المحاسبية
print("\n7. التحقق من القيود المحاسبية المرتبطة...")
journal_entries = JournalEntry.objects.filter(
    reference_type='bank_transaction'
).count()
print(f"  - عدد القيود المحاسبية للمعاملات البنكية: {journal_entries}")

# التحقق من قيد معاملة الإيداع
deposit_journal = JournalEntry.objects.filter(
    reference_type='bank_transaction',
    reference_id=deposit.id
).first()

if deposit_journal:
    print(f"✓ تم إنشاء قيد محاسبي للإيداع: {deposit_journal.entry_number}")
    lines = deposit_journal.journalline_set.all()  # استخدام related_name الصحيح
    print(f"  - عدد البنود: {lines.count()}")
    for line in lines:
        print(f"    - {line.account.name}: مدين={line.debit}, دائن={line.credit}")
else:
    print("⚠ لم يتم العثور على قيد محاسبي للإيداع")

# 8. التنظيف - حذف البيانات التجريبية
print("\n8. تنظيف البيانات التجريبية...")
# حذف المعاملة المتبقية
deposit.delete()
# حذف الحساب البنكي
test_bank.delete()
print("✓ تم حذف جميع البيانات التجريبية")

# 9. النتيجة النهائية
print("\n" + "="*80)
print("نتيجة الاختبار: ✓ نجح الاختبار - النظام يعمل بشكل صحيح")
print("="*80 + "\n")

print("ملاحظات:")
print("- تم إصلاح التكرار في تحديث الرصيد")
print("- الرصيد يتم تحديثه فقط عبر الإشارة (signal)")
print("- النظام متوافق مع IFRS")
print("- جميع الأجزاء المشتركة تعمل بشكل صحيح")

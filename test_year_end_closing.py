#!/usr/bin/env python
"""
سكريبت اختبار الإقفال السنوي التلقائي
يختبر وظيفة الإقفال السنوي للأرباح والخسائر مع نقلها إلى رأس المال
"""

import os
import sys
import django
from datetime import date, datetime
from decimal import Decimal

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.db import transaction
from users.models import User
from journal.models import Account, JournalEntry, JournalLine, YearEndClosing

def create_test_data():
    """إنشاء بيانات تجريبية للاختبار"""
    print("إنشاء بيانات تجريبية...")

    # إنشاء حسابات تجريبية إذا لم تكن موجودة
    accounts_data = [
        {'code': '1000', 'name': 'النقدية - اختبار', 'account_type': 'asset', 'is_active': True},
        {'code': '2000', 'name': 'المبيعات - اختبار', 'account_type': 'revenue', 'is_active': True},
        {'code': '3000', 'name': 'المشتريات - اختبار', 'account_type': 'expense', 'is_active': True},
        {'code': '4000', 'name': 'الرواتب - اختبار', 'account_type': 'expense', 'is_active': True},
        {'code': '5000', 'name': 'رأس المال - اختبار', 'account_type': 'equity', 'is_active': True},
        {'code': '6000', 'name': 'الأرباح المحتجزة - اختبار', 'account_type': 'equity', 'is_active': True},
    ]

    accounts = {}
    for acc_data in accounts_data:
        account, created = Account.objects.get_or_create(
            code=acc_data['code'],
            defaults=acc_data
        )
        accounts[acc_data['code']] = account
        if created:
            print(f"تم إنشاء حساب: {account.name}")

    # إنشاء قيود محاسبية تجريبية لسنة مختلفة لتجنب البيانات الموجودة
    test_year = 2024  # سنة مختلفة للاختبار
    user = User.objects.filter(is_superuser=True).first() or User.objects.create_superuser('testuser', 'test@example.com', 'password')

    # قيد 1: مبيعات نقدية
    entry1 = JournalEntry.objects.create(
        entry_number='JE-TEST-001',
        entry_date=date(test_year, 1, 15),
        description='مبيعات نقدية',
        reference_type='manual',
        total_amount=Decimal('10000.00'),
        created_by=user
    )
    JournalLine.objects.create(
        journal_entry=entry1,
        account=accounts['1000'],  # النقدية - مدين
        debit=Decimal('10000.00'),
        credit=Decimal('0'),
        line_description='مبيعات نقدية'
    )
    JournalLine.objects.create(
        journal_entry=entry1,
        account=accounts['2000'],  # المبيعات - دائن
        debit=Decimal('0'),
        credit=Decimal('10000.00'),
        line_description='مبيعات نقدية'
    )

    # قيد 2: مشتريات
    entry2 = JournalEntry.objects.create(
        entry_number='JE-TEST-002',
        entry_date=date(test_year, 2, 10),
        description='مشتريات',
        reference_type='manual',
        total_amount=Decimal('6000.00'),
        created_by=user
    )
    JournalLine.objects.create(
        journal_entry=entry2,
        account=accounts['3000'],  # المشتريات - مدين
        debit=Decimal('6000.00'),
        credit=Decimal('0'),
        line_description='مشتريات'
    )
    JournalLine.objects.create(
        journal_entry=entry2,
        account=accounts['1000'],  # النقدية - دائن
        debit=Decimal('0'),
        credit=Decimal('6000.00'),
        line_description='مشتريات'
    )

    # قيد 3: رواتب
    entry3 = JournalEntry.objects.create(
        entry_number='JE-TEST-003',
        entry_date=date(test_year, 3, 5),
        description='رواتب الموظفين',
        reference_type='manual',
        total_amount=Decimal('2000.00'),
        created_by=user
    )
    JournalLine.objects.create(
        journal_entry=entry3,
        account=accounts['4000'],  # الرواتب - مدين
        debit=Decimal('2000.00'),
        credit=Decimal('0'),
        line_description='رواتب الموظفين'
    )
    JournalLine.objects.create(
        journal_entry=entry3,
        account=accounts['1000'],  # النقدية - دائن
        debit=Decimal('0'),
        credit=Decimal('2000.00'),
        line_description='رواتب الموظفين'
    )

    print("تم إنشاء البيانات التجريبية بنجاح")
    return accounts

def test_year_end_closing():
    """اختبار الإقفال السنوي"""
    print("\nبدء اختبار الإقفال السنوي...")
    
    test_year = 2024  # سنة مختلفة للاختبار
    
    # حذف أي إقفالات سابقة لسنة الاختبار
    YearEndClosing.objects.filter(year=test_year).delete()
    
    # حذف البيانات التجريبية السابقة لضمان اختبار نظيف
    # بدلاً من حذف الحسابات، سننشئ حسابات بأسماء مختلفة
    test_account_names = ['النقدية', 'المبيعات', 'المشتريات', 'الرواتب', 'رأس المال', 'الأرباح المحتجزة']
    
    # حذف القيود التجريبية
    JournalEntry.objects.filter(description__in=[
        'مبيعات نقدية', 'مشتريات', 'رواتب الموظفين'
    ]).delete()
    
    # إنشاء بيانات تجريبية
    test_accounts = create_test_data()    # حساب الربح الصافي المتوقع
    # المبيعات: 10000 (إيراد - دائن في حساب المبيعات)
    # المشتريات: 6000 (مصروف - مدين في حساب المشتريات)
    # الرواتب: 2000 (مصروف - مدين في حساب الرواتب)
    # صافي الربح: 10000 - 6000 - 2000 = 2000

    expected_net_profit = Decimal('2000.00')

    try:
        with transaction.atomic():
            user = User.objects.filter(is_superuser=True).first() or User.objects.create_superuser('testuser', 'test@example.com', 'password')
            
            # إجراء الإقفال السنوي
            closing = YearEndClosing.objects.create(
                year=test_year,  # استخدام سنة الاختبار
                closing_date=date(test_year, 12, 31),
                notes='اختبار تلقائي للإقفال السنوي',
                created_by=user
            )

            # حساب الربح الصافي
            net_profit = closing.calculate_net_profit()
            
            # طباعة تفاصيل الحساب للتحقق
            from django.db.models import Sum
            from journal.models import Account, JournalLine
            
            revenue_accounts = Account.objects.filter(account_type__in=['revenue', 'sales'])
            expense_accounts = Account.objects.filter(account_type__in=['expense', 'purchases'])
            
            print(f"حسابات الإيرادات: {[acc.name for acc in revenue_accounts]}")
            print(f"حسابات المصروفات: {[acc.name for acc in expense_accounts]}")
            
            total_revenue = JournalLine.objects.filter(
                account__in=revenue_accounts,
                journal_entry__entry_date__year=test_year
            ).aggregate(total=Sum('credit') - Sum('debit'))['total'] or Decimal('0')
            
            total_expenses = JournalLine.objects.filter(
                account__in=expense_accounts,
                journal_entry__entry_date__year=test_year
            ).aggregate(total=Sum('debit') - Sum('credit'))['total'] or Decimal('0')
            
            print(f"إجمالي الإيرادات: {total_revenue}")
            print(f"إجمالي المصروفات: {total_expenses}")
            print(f"الربح الصافي المحسوب: {net_profit}")
            print(f"الربح الصافي المتوقع: {expected_net_profit}")

            # التحقق من صحة الحساب
            if abs(net_profit - expected_net_profit) < Decimal('0.01'):
                print("✓ حساب الربح الصافي صحيح")
            else:
                print("✗ خطأ في حساب الربح الصافي")
                return False

            # إجراء الإقفال
            closing.perform_closing()
            print("تم إجراء الإقفال بنجاح")

            # التحقق من إنشاء القيود الختامية
            closing_entries = JournalEntry.objects.filter(
                reference_type='year_end_closing',
                entry_date__year=test_year
            )

            if closing_entries.exists():
                print(f"✓ تم إنشاء {closing_entries.count()} قيد ختامي")
                for entry in closing_entries:
                    print(f"  - {entry.description}: {entry.total_amount}")
            else:
                print("✗ لم يتم إنشاء قيود ختامية")
                return False

            # التحقق من تحديث رصيد رأس المال
            capital_account = test_accounts['5000']
            retained_earnings = test_accounts['6000']

            print(f"رصيد رأس المال بعد الإقفال: {capital_account.balance}")
            print(f"رصيد الأرباح المحتجزة بعد الإقفال: {retained_earnings.balance}")

            return True

    except Exception as e:
        print(f"خطأ في الإقفال: {str(e)}")
        return False

def save_test_results(success, results):
    """حفظ نتائج الاختبار في ملف"""
    import os
    from datetime import datetime

    # إنشاء مجلد test_result إذا لم يكن موجوداً
    os.makedirs('test_result', exist_ok=True)

    # اسم الملف مع التاريخ والوقت
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'test_result/year_end_closing_test_{timestamp}.txt'

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("نتائج اختبار الإقفال السنوي\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"تاريخ الاختبار: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"النتيجة: {'نجح' if success else 'فشل'}\n\n")

        if results:
            f.write("تفاصيل الاختبار:\n")
            for key, value in results.items():
                f.write(f"{key}: {value}\n")

        f.write("\n" + "=" * 50 + "\n")
        f.write("نهاية التقرير\n")

    print(f"تم حفظ نتائج الاختبار في: {filename}")
    return filename

def main():
    """الدالة الرئيسية للسكريبت"""
    print("بدء اختبار الإقفال السنوي التلقائي")
    print("=" * 60)

    # تشغيل الاختبار
    success = test_year_end_closing()

    # جمع النتائج
    results = {
        'عدد الحسابات': Account.objects.count(),
        'عدد القيود المحاسبية': JournalEntry.objects.count(),
        'عدد الإقفالات السنوية': YearEndClosing.objects.count(),
    }

    # حفظ النتائج
    filename = save_test_results(success, results)

    print("\n" + "=" * 60)
    if success:
        print("✅ الاختبار نجح بنجاح!")
    else:
        print("❌ الاختبار فشل!")

    print(f"📄 تم حفظ التقرير في: {filename}")

if __name__ == '__main__':
    main()
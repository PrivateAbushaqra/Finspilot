import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from journal.models import Account, JournalEntry, JournalLine
from django.contrib.auth import get_user_model
from datetime import date
from decimal import Decimal
from django.db.models import Sum

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()
if not user:
    print('لا يوجد superuser')
    exit()

# إنشاء حسابات تجريبية إذا لم تكن موجودة
acc1, created1 = Account.objects.get_or_create(
    code='1001',
    defaults={
        'name': 'الصندوق',
        'account_type': 'asset',
        'is_active': True
    }
)
acc2, created2 = Account.objects.get_or_create(
    code='2001',
    defaults={
        'name': 'المبيعات',
        'account_type': 'revenue',
        'is_active': True
    }
)

print(f'الحسابات: {acc1.name} ({acc1.code}), {acc2.name} ({acc2.code})')

# محاولة إنشاء قيد تجريبي
try:
    entry = JournalEntry.objects.create(
        entry_number='TEST001',
        entry_date=date.today(),
        description='قيد تجريبي للاختبار',
        entry_type='manual',
        reference_type='manual',
        total_amount=Decimal('100.000'),
        created_by=user
    )

    # إضافة البنود
    JournalLine.objects.create(
        journal_entry=entry,
        account=acc1,
        debit=Decimal('100.000'),
        credit=Decimal('0.000'),
        line_description='دفع نقدي'
    )
    JournalLine.objects.create(
        journal_entry=entry,
        account=acc2,
        debit=Decimal('0.000'),
        credit=Decimal('100.000'),
        line_description='إيرادات مبيعات'
    )

    print(f'تم إنشاء القيد التجريبي: {entry.entry_number}')

    # التحقق من التوازن
    total_debit = entry.lines.aggregate(total_debit=Sum('debit'))['total_debit'] or 0
    total_credit = entry.lines.aggregate(total_credit=Sum('credit'))['total_credit'] or 0
    print(f'الإجماليات: مدين={total_debit}, دائن={total_credit}')

except Exception as e:
    print(f'خطأ في إنشاء القيد: {e}')
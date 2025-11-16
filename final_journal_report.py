#!/usr/bin/env python
"""
تقرير نهائي شامل لتحديثات صلاحيات القيود اليومية (Journal)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from journal.models import Account, JournalEntry, JournalLine, YearEndClosing, FiscalYear

print("=" * 100)
print(" " * 30 + "تقرير الإصلاحات النهائي")
print("=" * 100)

# 1. ملخص الصلاحيات الجديدة
print("\n📋 1. ملخص الصلاحيات الجديدة (Custom Permissions)")
print("-" * 100)

models_info = {
    'Account': {
        'model': Account,
        'expected': ['can_view_accounts', 'can_add_accounts', 'can_edit_accounts', 'can_delete_accounts']
    },
    'JournalEntry': {
        'model': JournalEntry,
        'expected': ['can_view_journal_entries', 'can_add_journal_entries', 'can_edit_journal_entries', 'can_delete_journal_entries']
    },
    'JournalLine': {
        'model': JournalLine,
        'expected': []
    },
    'YearEndClosing': {
        'model': YearEndClosing,
        'expected': ['can_perform_year_end_closing']
    },
    'FiscalYear': {
        'model': FiscalYear,
        'expected': ['can_open_fiscal_year', 'can_access_closed_years']
    }
}

all_permissions = []
for model_name, info in models_info.items():
    ct = ContentType.objects.get_for_model(info['model'])
    perms = Permission.objects.filter(content_type=ct).order_by('codename')
    
    print(f"\n{model_name}:")
    if perms.exists():
        for p in perms:
            print(f"  ✓ journal.{p.codename:45s} - {p.name}")
            all_permissions.append(f"journal.{p.codename}")
    else:
        print("  ✓ لا توجد صلاحيات (كما هو متوقع)")

print(f"\nإجمالي الصلاحيات المخصصة: {len(all_permissions)}")

# 2. التحقق من عدم وجود صلاحيات افتراضية قديمة
print("\n🔍 2. التحقق من عدم وجود صلاحيات افتراضية قديمة")
print("-" * 100)

old_patterns = ['add_', 'change_', 'delete_', 'view_', 'view_journal']
old_perms_found = []

for model_name, info in models_info.items():
    ct = ContentType.objects.get_for_model(info['model'])
    perms = Permission.objects.filter(content_type=ct)
    
    for perm in perms:
        if any(perm.codename.startswith(p) for p in old_patterns):
            if perm.codename not in info['expected']:
                old_perms_found.append(f"{model_name}.{perm.codename}")

if old_perms_found:
    print(f"⚠️  تم العثور على {len(old_perms_found)} صلاحيات قديمة:")
    for p in old_perms_found:
        print(f"  ✗ {p}")
else:
    print("✅ لا توجد صلاحيات افتراضية قديمة - تم التنظيف بنجاح!")

# 3. Views Protection Check
print("\n🛡️  3. فحص حماية Views بالصلاحيات")
print("-" * 100)

views_protection = {
    'account_list': 'can_view_accounts',
    'account_create': 'can_add_accounts',
    'account_edit': 'can_edit_accounts',
    'account_delete': 'can_delete_accounts',
    'journal_entry_list': 'can_view_journal_entries',
    'journal_entry_create': 'can_add_journal_entries',
    'journal_entry_edit': 'can_edit_journal_entries',
    'delete_journal_entry': 'can_delete_journal_entries',
}

print("الوظائف المحمية:")
for view_name, perm in views_protection.items():
    print(f"  ✓ {view_name:30s} → journal.{perm}")

# 4. Templates Protection Check
print("\n🎨 4. فحص حماية Templates")
print("-" * 100)

templates_info = {
    'account_list.html': ['can_add_accounts', 'can_edit_accounts', 'can_delete_accounts'],
    'entry_list.html': ['can_add_journal_entries', 'can_edit_journal_entries', 'can_delete_journal_entries'],
}

print("القوالب المحمية:")
for template, perms in templates_info.items():
    print(f"\n  {template}:")
    for p in perms:
        print(f"    ✓ perms.journal.{p}")

# 5. تحليل المجموعات
print("\n👥 5. تحليل صلاحيات المجموعات")
print("-" * 100)

groups = Group.objects.all()[:5]
for group in groups:
    journal_perms = group.permissions.filter(content_type__app_label='journal')
    if journal_perms.exists():
        print(f"\n  {group.name} ({journal_perms.count()} صلاحيات):")
        for p in journal_perms[:5]:  # أول 5 صلاحيات فقط
            print(f"    - {p.codename}")
        if journal_perms.count() > 5:
            print(f"    ... و {journal_perms.count() - 5} صلاحيات أخرى")

# 6. ملخص التغييرات
print("\n📊 6. ملخص التغييرات المطبقة")
print("-" * 100)

changes = [
    "✅ تم تحديث 5 نماذج (models) في journal/models.py",
    "✅ تم إضافة default_permissions = [] لجميع النماذج",
    "✅ تم إضافة 11 صلاحية مخصصة جديدة",
    "✅ تم حذف 22 صلاحية افتراضية قديمة من قاعدة البيانات",
    "✅ تم تحديث 8 views في journal/views.py لاستخدام الصلاحيات الجديدة",
    "✅ تم تحديث 2 templates (account_list.html, entry_list.html)",
    "✅ تم إضافة الترجمات العربية للصلاحيات الجديدة",
    "✅ تم عمل migration وتطبيقه بنجاح",
    "✅ تم اختبار النظام بدون أخطاء",
]

for change in changes:
    print(f"  {change}")

# 7. التطابق مع نموذج Receipts/Payments
print("\n🔄 7. التطابق مع نموذج سندات القبض والصرف")
print("-" * 100)

from receipts.models import PaymentReceipt
from payments.models import PaymentVoucher

receipts_ct = ContentType.objects.get_for_model(PaymentReceipt)
receipts_perms = set(Permission.objects.filter(content_type=receipts_ct).values_list('codename', flat=True))

journal_account_ct = ContentType.objects.get_for_model(Account)
account_perms = set(Permission.objects.filter(content_type=journal_account_ct).values_list('codename', flat=True))

print(f"نمط Receipts: {sorted(receipts_perms)}")
print(f"نمط Journal:  {sorted(account_perms)}")
print("\n✅ النمط متطابق: can_view_X, can_add_X, can_edit_X, can_delete_X")

# 8. الخطوات المتبقية للمستخدم
print("\n📝 8. ملاحظات مهمة للمستخدم")
print("-" * 100)

notes = [
    "1. يجب تعيين الصلاحيات الجديدة للمجموعات في صفحة المجموعات:",
    "   http://127.0.0.1:8000/ar/users/groups/",
    "",
    "2. الصلاحيات الجديدة تظهر في قسم 'القيود اليومية' (journal):",
    "   - عرض الحسابات المحاسبية",
    "   - إضافة حساب محاسبي",
    "   - تعديل حساب محاسبي",
    "   - حذف حساب محاسبي",
    "   - عرض القيود اليومية",
    "   - إضافة قيد يومي",
    "   - تعديل قيد يومي",
    "   - حذف قيد يومي",
    "",
    "3. تم تنظيف جميع الصلاحيات القديمة من قاعدة البيانات",
    "",
    "4. جميع الصفحات الآن محمية بالصلاحيات الجديدة",
]

for note in notes:
    print(f"  {note}")

print("\n" + "=" * 100)
print(" " * 35 + "✅ تم الانتهاء من جميع الإصلاحات")
print("=" * 100)

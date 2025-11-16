#!/usr/bin/env python
"""Final report: Show all journal permissions for test1 group and test user menu"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import activate, gettext

User = get_user_model()
activate('ar')

print("\n" + "="*80)
print("تقرير نهائي: صلاحيات المستخدم test والقوائم المتاحة")
print("="*80)

# Get test user
test_user = User.objects.get(username='test')
test1_group = Group.objects.get(name='test1')

print(f"\n📊 معلومات المستخدم:")
print(f"   Username: {test_user.username}")
print(f"   المجموعة: {test1_group.name}")
print(f"   عدد الصلاحيات: {test1_group.permissions.count()}")

print(f"\n" + "-"*80)
print("صلاحيات Journal في المجموعة test1:")
print("-"*80)

journal_perms = test1_group.permissions.filter(
    content_type__app_label='journal'
).select_related('content_type').order_by('content_type__model', 'codename')

for perm in journal_perms:
    ct = perm.content_type
    model_class = ct.model_class()
    section = gettext(str(model_class._meta.verbose_name_plural))
    perm_name = gettext(perm.name)
    print(f"\n✓ [{section}] {perm_name}")
    print(f"  Codename: {perm.codename}")

print(f"\n" + "="*80)
print("البنود التي ستظهر للمستخدم test في القائمة:")
print("="*80)

menu_items = []

# Check each permission and corresponding menu item
if test_user.has_perm('journal.can_view_accounts'):
    menu_items.append("✅ دليل الحسابات (Chart of Accounts)")
else:
    menu_items.append("❌ دليل الحسابات - ليس لديه صلاحية")

if test_user.has_perm('journal.can_view_journal_entries'):
    menu_items.append("✅ القيود اليومية (Journal Entries)")
else:
    menu_items.append("❌ القيود اليومية - ليس لديه صلاحية")

if test_user.has_perm('journal.can_perform_year_end_closing'):
    menu_items.append("✅ إغلاق السنة المالية (Closing the Fiscal Year)")
else:
    menu_items.append("❌ إغلاق السنة المالية - ليس لديه صلاحية")

for item in menu_items:
    print(f"\n{item}")

print(f"\n" + "="*80)
print("✅ التقرير النهائي")
print("="*80)
print("\n🎯 لاختبار من المتصفح:")
print("   URL: http://127.0.0.1:8000/ar/")
print("   Username: test")
print("   Password: testadmin1234")
print("\n📋 الصلاحيات الرئيسية:")
print("   1. can_view_accounts → دليل الحسابات")
print("   2. can_view_journal_entries → القيود اليومية")
print("   3. can_perform_year_end_closing → إغلاق السنة المالية")
print("="*80 + "\n")

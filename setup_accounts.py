#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from journal.models import Account

# إنشاء الحسابات الأساسية إذا لم تكن موجودة
suppliers_account, created = Account.objects.get_or_create(
    code='2100',
    defaults={
        'name': 'حسابات الموردين',
        'account_type': 'liability',
        'description': 'حسابات الموردين الرئيسية'
    }
)
if created:
    print(f"تم إنشاء: {suppliers_account}")

expenses_account, created = Account.objects.get_or_create(
    code='4100',
    defaults={
        'name': 'مصروفات عامة',
        'account_type': 'expense',
        'description': 'المصروفات العامة والإدارية'
    }
)
if created:
    print(f"تم إنشاء: {expenses_account}")

print("✅ الحسابات الأساسية جاهزة")

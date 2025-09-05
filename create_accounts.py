#!/usr/bin/env python
"""
إنشاء الحسابات الأساسية المطلوبة لمذكرات الدين
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from journal.models import Account

def create_required_accounts():
    """إنشاء الحسابات المطلوبة إذا لم تكن موجودة"""
    
    # 1. حساب الموردين الرئيسي
    suppliers_account, created = Account.objects.get_or_create(
        code='2100',
        defaults={
            'name': 'حسابات الموردين',
            'account_type': 'liability',
            'description': 'حسابات الموردين الرئيسية'
        }
    )
    if created:
        print(f"✅ تم إنشاء حساب الموردين: {suppliers_account}")
    else:
        print(f"✅ حساب الموردين موجود: {suppliers_account}")
    
    # 2. حساب المصروفات العامة
    expenses_account, created = Account.objects.get_or_create(
        code='4100',
        defaults={
            'name': 'مصروفات عامة',
            'account_type': 'expense',
            'description': 'المصروفات العامة والإدارية'
        }
    )
    if created:
        print(f"✅ تم إنشاء حساب المصروفات: {expenses_account}")
    else:
        print(f"✅ حساب المصروفات موجود: {expenses_account}")
    
    print("\n✅ جميع الحسابات الأساسية جاهزة!")

if __name__ == "__main__":
    create_required_accounts()

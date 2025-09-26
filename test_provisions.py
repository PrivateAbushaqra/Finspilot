#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار نظام المخصصات المحاسبية
Test script for Accounting Provisions System
"""

import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from users.models import User
from django.test import TestCase
from provisions.models import ProvisionType, Provision, ProvisionEntry
from journal.models import Account
from backup.views import log_audit


def create_test_data():
    """إنشاء بيانات اختبار"""
    print("إنشاء بيانات الاختبار...")

    # إنشاء مستخدم اختبار
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@example.com', 'is_staff': True}
    )

    # إنشاء أنواع المخصصات
    provision_types_data = [
        {'name': 'مخصص الديون المشكوك في تحصيلها', 'description': 'مخصص للديون المشكوك في تحصيلها'},
        {'name': 'مخصص الاهلاك', 'description': 'مخصص لاهلاك الأصول الثابتة'},
        {'name': 'مخصص المخزون', 'description': 'مخصص لتلف المخزون'},
        {'name': 'مخصص الضمان', 'description': 'مخصص للضمانات'},
    ]

    provision_types = []
    for data in provision_types_data:
        pt, created = ProvisionType.objects.get_or_create(
            name=data['name'],
            defaults={
                'description': data['description'],
                'is_active': True,
                'created_by': user
            }
        )
        provision_types.append(pt)
        print(f"تم إنشاء نوع المخصص: {pt.name}")

    # إنشاء حسابات اختبار
    accounts_data = [
        {'name': 'حساب العملاء', 'account_type': 'asset', 'code': '101'},
        {'name': 'مخصص الديون المشكوك فيها', 'account_type': 'asset', 'code': '102'},
        {'name': 'الأصول الثابتة', 'account_type': 'asset', 'code': '103'},
        {'name': 'مخصص الاهلاك', 'account_type': 'asset', 'code': '104'},
        {'name': 'المخزون', 'account_type': 'asset', 'code': '105'},
        {'name': 'مخصص المخزون', 'account_type': 'asset', 'code': '106'},
    ]

    accounts = []
    for data in accounts_data:
        acc, created = Account.objects.get_or_create(
            code=data['code'],
            defaults={
                'name': data['name'],
                'account_type': data['account_type'],
                'is_active': True,
                'balance': Decimal('0'),
                'created_by': user
            }
        )
        accounts.append(acc)
        print(f"تم إنشاء الحساب: {acc.name}")

    return user, provision_types, accounts


def test_provision_creation():
    """اختبار إنشاء المخصصات"""
    print("\nاختبار إنشاء المخصصات...")

    user, provision_types, accounts = create_test_data()

    # إنشاء مخصص الديون
    provision1 = Provision.objects.create(
        provision_type=provision_types[0],  # مخصص الديون
        name='مخصص ديون العميل أحمد',
        description='مخصص لديون العميل أحمد المشكوك في تحصيلها',
        related_account=accounts[0],  # حساب العملاء
        provision_account=accounts[1],  # مخصص الديون
        amount=Decimal('5000.000'),
        fiscal_year=2024,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        is_active=True,
        created_by=user
    )
    print(f"تم إنشاء مخصص الديون: {provision1.name}")

    # إنشاء مخصص الاهلاك
    provision2 = Provision.objects.create(
        provision_type=provision_types[1],  # مخصص الاهلاك
        name='اهلاك السيارة رقم 1',
        description='مخصص اهلاك السيارة رقم 1',
        related_account=accounts[2],  # الأصول الثابتة
        provision_account=accounts[3],  # مخصص الاهلاك
        amount=Decimal('10000.000'),
        fiscal_year=2024,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        is_active=True,
        created_by=user
    )
    print(f"تم إنشاء مخصص الاهلاك: {provision2.name}")

    # إنشاء إدخالات للمخصصات
    entry1 = ProvisionEntry.objects.create(
        provision=provision1,
        date=date.today(),
        amount=Decimal('1000.000'),
        description='دفعة أولى من مخصص الديون',
        created_by=user
    )
    print(f"تم إنشاء إدخال مخصص: {entry1.description}")

    entry2 = ProvisionEntry.objects.create(
        provision=provision2,
        date=date.today(),
        amount=Decimal('2000.000'),
        description='دفعة أولى من مخصص الاهلاك',
        created_by=user
    )
    print(f"تم إنشاء إدخال مخصص: {entry2.description}")

    return provision1, provision2, entry1, entry2


def test_provision_calculations():
    """اختبار حسابات المخصصات"""
    print("\nاختبار حسابات المخصصات...")

    provisions = Provision.objects.filter(is_active=True)
    total_provisions = provisions.aggregate(total=Decimal('0'))['total'] or Decimal('0')

    print(f"إجمالي المخصصات: {total_provisions}")

    # تقرير حسب النوع
    type_report = provisions.values('provision_type__name').annotate(
        total_amount=Decimal('0')
    ).order_by('-total_amount')

    print("تقرير حسب النوع:")
    for item in type_report:
        print(f"  {item['provision_type__name']}: {item['total_amount']}")

    # تقرير حسب السنة المالية
    fiscal_year_report = provisions.values('fiscal_year').annotate(
        total_amount=Decimal('0')
    ).order_by('-fiscal_year')

    print("تقرير حسب السنة المالية:")
    for item in fiscal_year_report:
        print(f"  {item['fiscal_year']}: {item['total_amount']}")


def test_provision_balance():
    """اختبار رصيد المخصصات"""
    print("\nاختبار رصيد المخصصات...")

    for provision in Provision.objects.filter(is_active=True):
        total_entries = ProvisionEntry.objects.filter(provision=provision).aggregate(
            total=Decimal('0')
        )['total'] or Decimal('0')
        balance = provision.amount - total_entries
        print(f"مخصص '{provision.name}': المبلغ={provision.amount}, الإدخالات={total_entries}, الرصيد={balance}")


def cleanup_test_data():
    """تنظيف بيانات الاختبار"""
    print("\nتنظيف بيانات الاختبار...")

    ProvisionEntry.objects.all().delete()
    Provision.objects.all().delete()
    ProvisionType.objects.filter(name__startswith='مخصص').delete()
    Account.objects.filter(code__in=['101', '102', '103', '104', '105', '106']).delete()

    print("تم تنظيف بيانات الاختبار")


def run_tests():
    """تشغيل جميع الاختبارات"""
    print("بدء اختبار نظام المخصصات المحاسبية")
    print("=" * 50)

    try:
        # إنشاء البيانات وتشغيل الاختبارات
        test_provision_creation()
        test_provision_calculations()
        test_provision_balance()

        print("\n" + "=" * 50)
        print("✅ تم إنجاز جميع الاختبارات بنجاح!")

    except Exception as e:
        print(f"\n❌ خطأ في الاختبارات: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        # تنظيف البيانات
        cleanup_test_data()


if __name__ == '__main__':
    run_tests()
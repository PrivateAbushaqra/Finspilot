#!/usr/bin/env python
"""
سكريبت لإنشاء الحسابات المحاسبية الافتراضية
يتم تشغيله عن طريق: python manage.py shell < create_default_accounts.py
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'triangle.settings')
django.setup()

from journal.models import Account

def create_default_accounts():
    """إنشاء الحسابات المحاسبية الافتراضية"""
    
    # قائمة الحسابات الافتراضية
    default_accounts = [
        # الأصول
        {'code': '1010', 'name': 'الصندوق', 'type': 'asset', 'description': 'النقدية في الصندوق'},
        {'code': '1020', 'name': 'البنوك', 'type': 'asset', 'description': 'الأرصدة البنكية'},
        {'code': '1050', 'name': 'العملاء', 'type': 'asset', 'description': 'الذمم المدينة - العملاء'},
        {'code': '1070', 'name': 'ضريبة القيمة المضافة مستحقة القبض', 'type': 'asset', 'description': 'ضريبة القيمة المضافة على المشتريات'},
        {'code': '1080', 'name': 'المخزون', 'type': 'asset', 'description': 'مخزون البضائع'},
        {'code': '1500', 'name': 'الأصول الثابتة', 'type': 'asset', 'description': 'الأصول الثابتة'},
        
        # المطلوبات
        {'code': '2010', 'name': 'الدائنون', 'type': 'liability', 'description': 'الالتزامات قصيرة المدى'},
        {'code': '2030', 'name': 'ضريبة القيمة المضافة مستحقة الدفع', 'type': 'liability', 'description': 'ضريبة القيمة المضافة على المبيعات'},
        {'code': '2050', 'name': 'الموردون', 'type': 'liability', 'description': 'الذمم الدائنة - الموردون'},
        
        # حقوق الملكية
        {'code': '3010', 'name': 'رأس المال', 'type': 'equity', 'description': 'رأس المال المدفوع'},
        {'code': '3020', 'name': 'الأرباح المحتجزة', 'type': 'equity', 'description': 'الأرباح المحتجزة'},
        
        # الإيرادات
        {'code': '4010', 'name': 'المبيعات', 'type': 'sales', 'description': 'إيرادات المبيعات'},
        {'code': '4020', 'name': 'مردود المبيعات', 'type': 'sales', 'description': 'مردود وخصومات المبيعات'},
        {'code': '4100', 'name': 'إيرادات أخرى', 'type': 'revenue', 'description': 'الإيرادات الأخرى'},
        
        # المشتريات
        {'code': '5010', 'name': 'المشتريات', 'type': 'purchases', 'description': 'مشتريات البضائع'},
        {'code': '5020', 'name': 'مردود المشتريات', 'type': 'purchases', 'description': 'مردود وخصومات المشتريات'},
        
        # المصاريف
        {'code': '6010', 'name': 'المصاريف العامة', 'type': 'expense', 'description': 'المصاريف العامة والإدارية'},
        {'code': '6020', 'name': 'مصاريف البيع', 'type': 'expense', 'description': 'مصاريف البيع والتسويق'},
        {'code': '6030', 'name': 'الرواتب والأجور', 'type': 'expense', 'description': 'رواتب وأجور الموظفين'},
        {'code': '6040', 'name': 'الإيجارات', 'type': 'expense', 'description': 'إيجارات المباني والمعدات'},
        {'code': '6050', 'name': 'الكهرباء والماء', 'type': 'expense', 'description': 'فواتير الكهرباء والماء'},
        {'code': '6060', 'name': 'الاتصالات', 'type': 'expense', 'description': 'مصاريف الهاتف والإنترنت'},
        {'code': '6070', 'name': 'الصيانة والإصلاح', 'type': 'expense', 'description': 'مصاريف الصيانة والإصلاح'},
        {'code': '6080', 'name': 'الوقود والمحروقات', 'type': 'expense', 'description': 'تكلفة الوقود والمحروقات'},
        {'code': '6090', 'name': 'القرطاسية واللوازم', 'type': 'expense', 'description': 'قرطاسية ولوازم مكتبية'},
        {'code': '6100', 'name': 'الاستهلاك', 'type': 'expense', 'description': 'استهلاك الأصول الثابتة'},
    ]
    
    created_count = 0
    updated_count = 0
    
    print("بدء إنشاء الحسابات الافتراضية...")
    
    for account_data in default_accounts:
        account, created = Account.objects.get_or_create(
            code=account_data['code'],
            defaults={
                'name': account_data['name'],
                'account_type': account_data['type'],
                'description': account_data['description'],
                'is_active': True
            }
        )
        
        if created:
            created_count += 1
            print(f"تم إنشاء الحساب: {account.code} - {account.name}")
        else:
            # تحديث البيانات إذا كان الحساب موجوداً
            account.name = account_data['name']
            account.account_type = account_data['type']
            account.description = account_data['description']
            account.save()
            updated_count += 1
            print(f"تم تحديث الحساب: {account.code} - {account.name}")
    
    print(f"\nتم الانتهاء من إعداد الحسابات:")
    print(f"- الحسابات المنشأة: {created_count}")
    print(f"- الحسابات المحدثة: {updated_count}")
    print(f"- إجمالي الحسابات: {Account.objects.count()}")

if __name__ == "__main__":
    create_default_accounts()

#!/usr/bin/env python
"""
سكريبت إعداد البيانات الأولية على Render.com
يتم تشغيله بعد نشر التطبيق لأول مرة
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.contrib.auth import get_user_model
from settings.models import Currency, CompanySettings
from journal.models import Account
from django.contrib.auth.models import Group, Permission

User = get_user_model()

def create_superuser():
    """إنشاء المستخدم الرئيسي"""
    print("🔐 إنشاء المستخدم الرئيسي...")
    
    if not User.objects.filter(username='superadmin').exists():
        user = User.objects.create_user(
            username='superadmin',
            email='admin@finspilot.com',
            password='Finspilot@2025',
            first_name='Super',
            last_name='Admin',
            user_type='superadmin',
            is_superuser=True,
            is_staff=True,
            can_access_sales=True,
            can_access_purchases=True,
            can_access_inventory=True,
            can_access_banks=True,
            can_access_reports=True,
            can_delete_invoices=True,
            can_edit_dates=True,
            can_edit_invoice_numbers=True,
            can_see_low_stock_alerts=True,
        )
        print(f'✅ تم إنشاء المستخدم: {user.username}')
        print(f'📧 البريد الإلكتروني: {user.email}')
        print(f'🔑 كلمة المرور: Finspilot@2025')
    else:
        print('ℹ️ المستخدم superadmin موجود بالفعل')

def create_currencies():
    """إنشاء العملات الافتراضية"""
    print("\n💱 إنشاء العملات الافتراضية...")
    
    default_currencies = [
        {
            'code': 'SAR',
            'name': 'الريال السعودي',
            'symbol': 'ر.س',
            'exchange_rate': 1.0000,
            'is_base_currency': True,
            'is_active': True,
            'decimal_places': 2
        },
        {
            'code': 'USD',
            'name': 'الدولار الأمريكي',
            'symbol': '$',
            'exchange_rate': 3.7500,
            'is_base_currency': False,
            'is_active': True,
            'decimal_places': 2
        },
        {
            'code': 'EUR',
            'name': 'اليورو',
            'symbol': '€',
            'exchange_rate': 4.0800,
            'is_base_currency': False,
            'is_active': True,
            'decimal_places': 2
        },
        {
            'code': 'AED',
            'name': 'الدرهم الإماراتي',
            'symbol': 'د.إ',
            'exchange_rate': 1.0204,
            'is_base_currency': False,
            'is_active': True,
            'decimal_places': 2
        },
        {
            'code': 'KWD',
            'name': 'الدينار الكويتي',
            'symbol': 'د.ك',
            'exchange_rate': 0.3058,
            'is_base_currency': False,
            'is_active': True,
            'decimal_places': 3
        },
        {
            'code': 'EGP',
            'name': 'الجنيه المصري',
            'symbol': 'ج.م',
            'exchange_rate': 18.3750,
            'is_base_currency': False,
            'is_active': True,
            'decimal_places': 2
        },
        {
            'code': 'JOD',
            'name': 'الدينار الأردني',
            'symbol': 'د.أ',
            'exchange_rate': 2.6546,
            'is_base_currency': False,
            'is_active': True,
            'decimal_places': 3
        }
    ]
    
    created_count = 0
    for currency_data in default_currencies:
        currency, created = Currency.objects.get_or_create(
            code=currency_data['code'],
            defaults=currency_data
        )
        
        if created:
            created_count += 1
            print(f"✅ تم إنشاء عملة: {currency.name} ({currency.code})")
        else:
            print(f"ℹ️ العملة موجودة: {currency.name} ({currency.code})")
    
    print(f"📊 إجمالي العملات المُنشأة: {created_count}")

def create_accounts():
    """إنشاء الحسابات المحاسبية الافتراضية"""
    print("\n🏦 إنشاء الحسابات المحاسبية الافتراضية...")
    
    default_accounts = [
        # الأصول
        {'code': '1010', 'name': 'الصندوق', 'account_type': 'asset', 'description': 'النقدية في الصندوق'},
        {'code': '1020', 'name': 'البنوك', 'account_type': 'asset', 'description': 'الأرصدة البنكية'},
        {'code': '1050', 'name': 'العملاء', 'account_type': 'asset', 'description': 'الذمم المدينة - العملاء'},
        {'code': '1070', 'name': 'ضريبة القيمة المضافة مستحقة القبض', 'account_type': 'asset', 'description': 'ضريبة القيمة المضافة على المشتريات'},
        {'code': '1080', 'name': 'المخزون', 'account_type': 'asset', 'description': 'مخزون البضائع'},
        
        # المطلوبات
        {'code': '2030', 'name': 'ضريبة القيمة المضافة مستحقة الدفع', 'account_type': 'liability', 'description': 'ضريبة القيمة المضافة على المبيعات'},
        {'code': '2050', 'name': 'الموردون', 'account_type': 'liability', 'description': 'الذمم الدائنة - الموردون'},
        
        # حقوق الملكية
        {'code': '3010', 'name': 'رأس المال', 'account_type': 'equity', 'description': 'رأس المال المدفوع'},
        {'code': '3020', 'name': 'الأرباح المحتجزة', 'account_type': 'equity', 'description': 'الأرباح المحتجزة'},
        
        # الإيرادات
        {'code': '4010', 'name': 'المبيعات', 'account_type': 'sales', 'description': 'إيرادات المبيعات'},
        {'code': '4020', 'name': 'مردود المبيعات', 'account_type': 'sales', 'description': 'مردود وخصومات المبيعات'},
        
        # المشتريات
        {'code': '5010', 'name': 'المشتريات', 'account_type': 'purchases', 'description': 'مشتريات البضائع'},
        {'code': '5020', 'name': 'مردود المشتريات', 'account_type': 'purchases', 'description': 'مردود وخصومات المشتريات'},
        
        # المصاريف
        {'code': '6010', 'name': 'المصاريف العامة', 'account_type': 'expense', 'description': 'المصاريف العامة والإدارية'},
        {'code': '6020', 'name': 'مصاريف البيع', 'account_type': 'expense', 'description': 'مصاريف البيع والتسويق'},
    ]
    
    created_count = 0
    for account_data in default_accounts:
        account, created = Account.objects.get_or_create(
            code=account_data['code'],
            defaults={
                'name': account_data['name'],
                'account_type': account_data['account_type'],
                'description': account_data['description'],
                'is_active': True
            }
        )
        
        if created:
            created_count += 1
            print(f"✅ تم إنشاء حساب: {account.code} - {account.name}")
        else:
            print(f"ℹ️ الحساب موجود: {account.code} - {account.name}")
    
    print(f"📊 إجمالي الحسابات المُنشأة: {created_count}")

def create_company_settings():
    """إنشاء إعدادات الشركة الافتراضية"""
    print("\n🏢 إنشاء إعدادات الشركة...")
    
    settings, created = CompanySettings.objects.get_or_create(
        pk=1,
        defaults={
            'company_name': 'Finspilot Accounting System',
            'currency': 'SAR',
            'address': 'المملكة العربية السعودية',
            'phone': '+966-XX-XXX-XXXX',
            'email': 'info@finspilot.com'
        }
    )
    
    if created:
        print(f"✅ تم إنشاء إعدادات الشركة: {settings.company_name}")
    else:
        print(f"ℹ️ إعدادات الشركة موجودة: {settings.company_name}")

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء إعداد البيانات الأولية لنظام Finspilot")
    print("=" * 60)
    
    try:
        create_superuser()
        create_currencies()
        create_accounts()
        create_company_settings()
        
        print("\n" + "=" * 60)
        print("🎉 تم الانتهاء من إعداد البيانات الأولية بنجاح!")
        print("=" * 60)
        
        print("\n📝 معلومات تسجيل الدخول:")
        print("   اسم المستخدم: superadmin")
        print("   كلمة المرور: Finspilot@2025")
        print("\n⚠️ مهم: غيّر كلمة المرور فوراً بعد تسجيل الدخول!")
        
    except Exception as e:
        print(f"\n❌ خطأ في إعداد البيانات: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    if not success:
        sys.exit(1)

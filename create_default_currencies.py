#!/usr/bin/env python
"""
إضافة العملات الافتراضية إلى النظام
"""
import os
import sys
import django

# إعداد مسار Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'triangle.settings')
django.setup()

from settings.models import Currency, CompanySettings

def create_default_currencies():
    """إنشاء العملات الافتراضية"""
    
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
        },
        {
            'code': 'QAR',
            'name': 'الريال القطري',
            'symbol': 'ر.ق',
            'exchange_rate': 3.6400,
            'is_base_currency': False,
            'is_active': True,
            'decimal_places': 2
        },
        {
            'code': 'BHD',
            'name': 'الدينار البحريني',
            'symbol': 'د.ب',
            'exchange_rate': 1.4125,
            'is_base_currency': False,
            'is_active': True,
            'decimal_places': 3
        },
        {
            'code': 'OMR',
            'name': 'الريال العماني',
            'symbol': 'ر.ع',
            'exchange_rate': 1.4419,
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
            print(f"تم إنشاء العملة: {currency.code} - {currency.name}")
            created_count += 1
        else:
            print(f"العملة موجودة بالفعل: {currency.code} - {currency.name}")
    
    # التأكد من وجود عملة أساسية
    base_currency = Currency.get_base_currency()
    if not base_currency:
        sar_currency = Currency.objects.filter(code='SAR').first()
        if sar_currency:
            sar_currency.is_base_currency = True
            sar_currency.save()
            print(f"تم تعيين {sar_currency.code} كعملة أساسية")
    
    print(f"\nتم إنشاء {created_count} عملة جديدة")
    print(f"العملة الأساسية: {Currency.get_base_currency()}")
    
    # إنشاء إعدادات الشركة الافتراضية إذا لم تكن موجودة
    if not CompanySettings.objects.exists():
        base_currency = Currency.get_base_currency()
        if base_currency:
            company_settings = CompanySettings.objects.create(
                company_name='Triangle Accounting Software',
                company_name_en='Triangle Accounting Software',
                base_currency=base_currency,
                show_currency_symbol=True
            )
            print(f"تم إنشاء إعدادات الشركة الافتراضية")

if __name__ == '__main__':
    try:
        create_default_currencies()
        print("\nتم إنشاء العملات الافتراضية بنجاح!")
    except Exception as e:
        print(f"حدث خطأ: {e}")

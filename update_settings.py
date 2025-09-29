#!/usr/bin/env python
import os
import django
import sys

# إعداد Django
sys.path.append('C:\\Accounting_soft\\finspilot')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from settings.models import CompanySettings, Currency

# الحصول على إعدادات الشركة
cs = CompanySettings.objects.first()
if cs:
    # الحصول على العملة الأساسية
    base_curr = Currency.get_base_currency()
    if base_curr:
        cs.base_currency = base_curr
        cs.save()
        print(f'Updated CompanySettings with base_currency: {base_curr}')
    else:
        print('No base currency found')
else:
    print('No CompanySettings found')
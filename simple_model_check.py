#!/usr/bin/env python
import os
import sys

# إضافة مسار المشروع
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings.production')

import django
django.setup()

from django.apps import apps

# الحصول على نموذج AccountTransaction
AccountTransaction = apps.get_model('accounts', 'AccountTransaction')

print("فحص نموذج AccountTransaction:")
print(f"اسم الجدول: {AccountTransaction._meta.db_table}")

# فحص الحقول
for field in AccountTransaction._meta.fields:
    if 'customer' in field.name or 'supplier' in field.name:
        print(f"  حقل: {field.name}")
        print(f"  نوع الحقل: {type(field).__name__}")
        if hasattr(field, 'related_model'):
            print(f"  النموذج المرتبط: {field.related_model}")
        if hasattr(field, 'db_column') and field.db_column:
            print(f"  اسم العمود في DB: {field.db_column}")
        else:
            print(f"  اسم العمود في DB: {field.name}")
        print()

# محاولة إنشاء SQL لعرض كيف يتم إنشاؤه
from django.db import connection
from accounts.models import AccountTransaction

print("محاولة إنشاء SQL:")
qs = AccountTransaction.objects.filter(customer_supplier_id=15)
print(f"SQL Query: {qs.query}")

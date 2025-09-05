import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings.production')
django.setup()

from accounts.models import AccountTransaction
from customers.models import CustomerSupplier

# طباعة معلومات عن الحقول
print("معلومات نموذج AccountTransaction:")
for field in AccountTransaction._meta.fields:
    print(f"  {field.name} -> {field.db_column if field.db_column else field.name}")

print("\nمعلومات نموذج CustomerSupplier:")
for field in CustomerSupplier._meta.fields:
    print(f"  {field.name} -> {field.db_column if field.db_column else field.name}")

# التحقق من حقل customer_supplier في AccountTransaction
customer_supplier_field = AccountTransaction._meta.get_field('customer_supplier')
print(f"\nحقل customer_supplier في AccountTransaction:")
print(f"  الاسم: {customer_supplier_field.name}")
print(f"  اسم العمود في DB: {customer_supplier_field.db_column or customer_supplier_field.name}")
print(f"  اسم العمود الأجنبي: {customer_supplier_field.name}_id")

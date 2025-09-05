#!/usr/bin/env python
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from purchases.models import PurchaseReturn
from customers.models import CustomerSupplier
from accounts.models import AccountTransaction

print("تشخيص حالة النظام:")
print("=" * 50)

# فحص مردود المشتريات
try:
    purchase_return = PurchaseReturn.objects.get(id=2)
    print(f"✓ مردود المشتريات موجود: {purchase_return.return_number}")
    print(f"  - المورد الأصلي: {purchase_return.original_invoice.supplier.name}")
    print(f"  - معرف المورد: {purchase_return.original_invoice.supplier.id}")
    print(f"  - نوع المورد: {purchase_return.original_invoice.supplier.type}")
except PurchaseReturn.DoesNotExist:
    print("✗ مردود المشتريات غير موجود")
    exit()

# فحص العميل رقم 14
try:
    customer = CustomerSupplier.objects.get(id=14)
    print(f"✓ العميل موجود: {customer.name}")
    print(f"  - نوع العميل: {customer.type}")
except CustomerSupplier.DoesNotExist:
    print("✗ العميل غير موجود")
    exit()

# فحص إذا كان المورد والعميل متطابقان
supplier = purchase_return.original_invoice.supplier
if supplier.id == customer.id:
    print("✓ المورد والعميل نفس الكيان")
elif supplier.name == customer.name:
    print(f"⚠ المورد والعميل لهما نفس الاسم ولكن معرفات مختلفة:")
    print(f"  - المورد: {supplier.name} (ID: {supplier.id})")
    print(f"  - العميل: {customer.name} (ID: {customer.id})")
else:
    print(f"✗ المورد والعميل مختلفان تماماً")
    print(f"  - المورد: {supplier.name} (ID: {supplier.id})")
    print(f"  - العميل: {customer.name} (ID: {customer.id})")

# فحص معاملات الحساب
print(f"\nمعاملات الحساب:")

# معاملات المورد
supplier_transactions = AccountTransaction.objects.filter(customer_supplier=supplier)
print(f"  - معاملات المورد: {supplier_transactions.count()}")
for t in supplier_transactions:
    if t.transaction_type == 'purchase_return' and str(t.reference_id) == str(purchase_return.id):
        print(f"    ✓ معاملة مردود المشتريات: {t.transaction_number}")

# معاملات العميل
customer_transactions = AccountTransaction.objects.filter(customer_supplier=customer)
print(f"  - معاملات العميل: {customer_transactions.count()}")
for t in customer_transactions:
    if t.transaction_type == 'purchase_return' and str(t.reference_id) == str(purchase_return.id):
        print(f"    ✓ معاملة مردود المشتريات للعميل: {t.transaction_number}")

# فحص معاملات مردود المشتريات تحديداً
return_transactions = AccountTransaction.objects.filter(
    transaction_type='purchase_return',
    reference_id=purchase_return.id
)
print(f"\nجميع معاملات مردود المشتريات رقم {purchase_return.id}: {return_transactions.count()}")
for t in return_transactions:
    print(f"  - {t.transaction_number}: {t.customer_supplier.name} (ID: {t.customer_supplier.id}) - {t.amount}")

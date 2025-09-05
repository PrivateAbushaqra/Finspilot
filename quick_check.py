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

# فحص مردود المشتريات رقم 2
pr = PurchaseReturn.objects.get(id=2)
print(f"مردود المشتريات: {pr.return_number}")
print(f"المورد: {pr.original_invoice.supplier.name} (ID: {pr.original_invoice.supplier.id})")

# فحص العميل رقم 14
customer = CustomerSupplier.objects.get(id=14)
print(f"العميل: {customer.name} (ID: {customer.id})")

# فحص معاملات مردود المشتريات
transactions = AccountTransaction.objects.filter(
    transaction_type='purchase_return', 
    reference_id=str(pr.id)
)
print(f"معاملات مردود المشتريات: {transactions.count()}")
for t in transactions:
    print(f"  - المرتبط بـ: {t.customer_supplier.name} (ID: {t.customer_supplier.id})")

# هل المورد والعميل نفس الشخص؟
supplier = pr.original_invoice.supplier
if supplier.id == customer.id:
    print("✓ المورد والعميل نفس الكيان")
else:
    print(f"✗ المورد (ID: {supplier.id}) مختلف عن العميل (ID: {customer.id})")
    # البحث عن عميل/مورد بنفس الاسم
    same_name = CustomerSupplier.objects.filter(name=supplier.name)
    print(f"كيانات بنفس الاسم: {same_name.count()}")
    for entity in same_name:
        print(f"  - {entity.name} (ID: {entity.id}, نوع: {entity.type})")

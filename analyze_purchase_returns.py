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

print("فحص مردودات المشتريات ومعاملات العميل رقم 14:")
print("=" * 60)

# فحص العميل رقم 14
try:
    customer = CustomerSupplier.objects.get(id=14)
    print(f"العميل: {customer.name} (ID: {customer.id}, نوع: {customer.type})")
except CustomerSupplier.DoesNotExist:
    print("العميل رقم 14 غير موجود")
    exit()

# فحص جميع مردودات المشتريات
print(f"\nجميع مردودات المشتريات:")
purchase_returns = PurchaseReturn.objects.all()
print(f"عدد مردودات المشتريات: {purchase_returns.count()}")

for pr in purchase_returns:
    supplier = pr.original_invoice.supplier
    print(f"\nمردود رقم {pr.id}: {pr.return_number}")
    print(f"  - المورد: {supplier.name} (ID: {supplier.id}, نوع: {supplier.type})")
    print(f"  - التاريخ: {pr.date}")
    print(f"  - المبلغ: {pr.total_amount}")
    
    # فحص إذا كان المورد هو نفس العميل أو يشاركه الاسم
    if supplier.id == customer.id:
        print(f"  ✓ المورد هو نفس العميل")
    elif supplier.name == customer.name:
        print(f"  ⚠ المورد والعميل لهما نفس الاسم ولكن معرفات مختلفة")
    else:
        print(f"  ✗ المورد مختلف عن العميل")
    
    # فحص معاملات الحساب لهذا المردود
    return_transactions = AccountTransaction.objects.filter(
        transaction_type='purchase_return',
        reference_id=pr.id
    )
    print(f"  - معاملات الحساب: {return_transactions.count()}")
    
    for trans in return_transactions:
        print(f"    * {trans.transaction_number}: {trans.customer_supplier.name} (ID: {trans.customer_supplier.id})")
        if trans.customer_supplier.id == customer.id:
            print(f"      ✓ معاملة مرتبطة بالعميل")

# فحص معاملات العميل
print(f"\nمعاملات العميل رقم 14:")
customer_transactions = AccountTransaction.objects.filter(customer_supplier=customer)
print(f"عدد المعاملات: {customer_transactions.count()}")

purchase_return_transactions = customer_transactions.filter(transaction_type='purchase_return')
print(f"معاملات مردود المشتريات: {purchase_return_transactions.count()}")

for trans in purchase_return_transactions:
    print(f"  - {trans.transaction_number}: مرجع {trans.reference_id} - {trans.amount}")

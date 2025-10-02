#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
فحص البيانات الحالية
"""

import os
import sys
import django

# إعداد Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesInvoice
from purchases.models import PurchaseInvoice
from receipts.models import PaymentReceipt
from payments.models import PaymentVoucher
from customers.models import CustomerSupplier
from products.models import Product
from users.models import User
from cashboxes.models import Cashbox
from banks.models import BankAccount

print('=== البيانات الحالية ===')
print(f'فواتير المبيعات: {SalesInvoice.objects.count()}')
print(f'فواتير المشتريات: {PurchaseInvoice.objects.count()}')
print(f'سندات القبض: {PaymentReceipt.objects.count()}')
print(f'سندات الصرف: {PaymentVoucher.objects.count()}')
print(f'العملاء: {CustomerSupplier.objects.filter(type__in=["customer", "both"]).count()}')
print(f'الموردون: {CustomerSupplier.objects.filter(type__in=["supplier", "both"]).count()}')
print(f'المنتجات: {Product.objects.count()}')
print(f'المستخدمون: {User.objects.count()}')
print(f'الصناديق: {Cashbox.objects.count()}')
print(f'الحسابات البنكية: {BankAccount.objects.count()}')

# فحص المستخدمين
print('\n=== المستخدمون ===')
for user in User.objects.all():
    print(f'- {user.username}: {user.first_name} {user.last_name}')

# فحص المنتجات
print('\n=== عينة من المنتجات ===')
for product in Product.objects.all()[:5]:
    print(f'- {product.code}: {product.name} - سعر البيع: {product.sale_price}')

# فحص العملاء والموردين
print('\n=== عينة من العملاء ===')
for customer in CustomerSupplier.objects.filter(type__in=["customer", "both"])[:3]:
    print(f'- {customer.name}')

print('\n=== عينة من الموردين ===')
for supplier in CustomerSupplier.objects.filter(type__in=["supplier", "both"])[:3]:
    print(f'- {supplier.name}')
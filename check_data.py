#!/usr/bin/env python
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from customers.models import CustomerSupplier
from products.models import Product

print(f'عدد العملاء: {CustomerSupplier.objects.filter(type__in=["customer", "both"]).count()}')
print(f'عدد المنتجات النشطة: {Product.objects.filter(is_active=True).count()}')
print(f'عدد المنتجات الإجمالي: {Product.objects.count()}')

# عرض أول عميل
first_customer = CustomerSupplier.objects.filter(type__in=["customer", "both"]).first()
if first_customer:
    print(f'أول عميل: {first_customer.name}')
else:
    print('لا يوجد عملاء')

# عرض أول منتج
first_product = Product.objects.filter(is_active=True).first()
if first_product:
    print(f'أول منتج: {first_product.name}')
else:
    print('لا يوجد منتجات نشطة')

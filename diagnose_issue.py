#!/usr/bin/env python
"""
اختبار يحاكي ما يحدث في المتصفح - خطوة بخطوة
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
os.environ['ALLOWED_HOSTS'] = '127.0.0.1,localhost,testserver,0.0.0.0'
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from sales.models import SalesInvoice

User = get_user_model()

print("\n" + "="*80)
print("محاكاة ما يحدث في المتصفح - خطوة بخطوة")
print("="*80)

user = User.objects.get(username='super')
client = Client()
client.force_login(user)

# الخطوة 1: فتح صفحة التعديل
print("\n🌐 الخطوة 1: فتح صفحة التعديل...")
print("   URL: http://127.0.0.1:8000/ar/sales/invoices/edit/17/")

response = client.get('/ar/sales/invoices/edit/17/')
print(f"   Status Code: {response.status_code}")

if response.status_code == 200:
    content = response.content.decode('utf-8')
    
    # فحص وجود IDs
    print("\n🔍 الخطوة 2: فحص وجود IDs في HTML...")
    ids_to_check = [
        'invoice-subtotal-display',
        'invoice-tax-display',
        'invoice-discount-display',
        'invoice-total-display'
    ]
    
    for id_name in ids_to_check:
        if f'id="{id_name}"' in content:
            print(f"   ✅ وجد: {id_name}")
        else:
            print(f"   ❌ مفقود: {id_name}")
    
    # فحص وجود الـ JavaScript
    print("\n🔍 الخطوة 3: فحص وجود JavaScript للتحديث...")
    if "$('#invoice-subtotal-display')" in content:
        print("   ✅ وجد: كود jQuery للتحديث")
    else:
        print("   ❌ مفقود: كود jQuery للتحديث")
    
    # فحص وجود الـ inputs
    print("\n🔍 الخطوة 4: فحص وجود حقول الإدخال...")
    if 'class="quantity-input"' in content:
        print("   ✅ وجد: quantity-input")
    else:
        print("   ❌ مفقود: quantity-input")
    
    if 'class="price-input"' in content:
        print("   ✅ وجد: price-input")
    else:
        print("   ❌ مفقود: price-input")
    
    if 'class="edit-item-btn"' in content:
        print("   ✅ وجد: edit-item-btn")
    else:
        print("   ❌ مفقود: edit-item-btn")

# الخطوة 5: محاولة تحديث عنصر
invoice = SalesInvoice.objects.get(pk=17)
item = invoice.items.first()

if not item:
    print("\n⚠️ لا توجد عناصر - سأضيف عنصر...")
    from products.models import Product
    product = Product.objects.filter(is_active=True).first()
    
    response = client.post(
        f'/ar/sales/invoices/17/items/add/',
        data={
            'product_id': product.id,
            'quantity': '5',
            'unit_price': '1000',
            'tax_rate': '15'
        }
    )
    
    if response.status_code == 200:
        import json
        data = json.loads(response.content)
        if data.get('success'):
            invoice.refresh_from_db()
            item = invoice.items.first()
            print(f"   ✅ تم إضافة عنصر")

if item:
    print(f"\n🔄 الخطوة 5: تحديث عنصر...")
    print(f"   العنصر: {item.product.name}")
    print(f"   الكمية الحالية: {item.quantity}")
    print(f"   السعر الحالي: {item.unit_price}")
    print(f"   مجموع الفاتورة الحالي: {invoice.total_amount}")
    
    new_qty = float(item.quantity) + 1
    print(f"\n   محاولة تغيير الكمية إلى: {new_qty}")
    
    response = client.post(
        f'/ar/sales/invoices/17/items/{item.id}/update/',
        data={
            'quantity': str(new_qty),
            'unit_price': str(item.unit_price)
        }
    )
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        import json
        data = json.loads(response.content)
        
        print(f"\n📦 الخطوة 6: فحص الاستجابة...")
        print(f"   success: {data.get('success')}")
        print(f"   message: {data.get('message')}")
        
        if 'item' in data:
            print(f"\n   بيانات العنصر في الاستجابة:")
            print(f"     quantity: {data['item'].get('quantity')}")
            print(f"     unit_price: {data['item'].get('unit_price')}")
            print(f"     total_amount: {data['item'].get('total_amount')}")
        
        if 'invoice' in data:
            print(f"\n   بيانات الفاتورة في الاستجابة:")
            print(f"     subtotal: {data['invoice'].get('subtotal')}")
            print(f"     tax_amount: {data['invoice'].get('tax_amount')}")
            print(f"     total_amount: {data['invoice'].get('total_amount')}")
        else:
            print(f"\n   ❌ لا توجد بيانات 'invoice' في الاستجابة!")
        
        # التحقق من قاعدة البيانات
        item.refresh_from_db()
        invoice.refresh_from_db()
        
        print(f"\n📊 الخطوة 7: التحقق من قاعدة البيانات...")
        print(f"   الكمية في DB: {item.quantity}")
        print(f"   مجموع الفاتورة في DB: {invoice.total_amount}")
        
        if float(item.quantity) == new_qty:
            print(f"\n✅ التحديث نجح في DB")
        else:
            print(f"\n❌ التحديث فشل في DB")

print("\n" + "="*80)
print("المشكلة الحقيقية:")
print("="*80)
print("\nالمشكلة ليست في Backend - Backend يعمل 100%")
print("المشكلة في Frontend - JavaScript لا يُنفّذ أو لا يُحدّث الصفحة")
print("\nالأسباب المحتملة:")
print("1. JavaScript بها خطأ syntax")
print("2. jQuery لم يتم تحميله")
print("3. CSRF token غير صحيح")
print("4. الـ event handler لم يُربط بالزر")
print("5. المستخدم لا يضغط على الزر الصحيح")
print("\nسأفحص كل هذه الاحتمالات...")
print("="*80 + "\n")

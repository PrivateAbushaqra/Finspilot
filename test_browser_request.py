#!/usr/bin/env python
"""
Simulate browser request to test send_invoice_to_jofotara view
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from sales.models import SalesInvoice
import json

User = get_user_model()

print("=" * 70)
print("محاكاة طلب المتصفح لاختبار send_invoice_to_jofotara")
print("=" * 70)

# Get invoice
try:
    invoice = SalesInvoice.objects.get(invoice_number='SALES-000005')
    print(f"\n✅ الفاتورة: {invoice.invoice_number}")
    print(f"   Current UUID: {invoice.jofotara_uuid or 'غير موجود'}")
    print(f"   Current QR: {' موجود' if invoice.jofotara_qr_code else 'غير موجود'}")
except SalesInvoice.DoesNotExist:
    print("❌ الفاتورة غير موجودة!")
    exit(1)

# Get user
user = User.objects.filter(is_superuser=True).first()
if not user:
    print("❌ لا يوجد مستخدم!")
    exit(1)

print(f"\n👤 المستخدم: {user.username}")

# Create client
client = Client()
client.force_login(user)

print("\n📤 إرسال POST request إلى /ar/sales/invoices/{}/send-to-jofotara/".format(invoice.pk))

# Send request
response = client.post(
    f'/ar/sales/invoices/{invoice.pk}/send-to-jofotara/',
    content_type='application/json',
    HTTP_X_REQUESTED_WITH='XMLHttpRequest'
)

print(f"\n📬 الاستجابة:")
print(f"   Status Code: {response.status_code}")
print(f"   Content-Type: {response.get('Content-Type')}")

if response.status_code == 200:
    try:
        data = json.loads(response.content)
        print(f"\n   Success: {data.get('success')}")
        
        if data.get('success'):
            print(f"   ✅ UUID: {data.get('uuid')}")
            print(f"   ✅ QR Code: {'موجود' if data.get('qr_code') else '❌ غير موجود'}")
            print(f"   ✅ Verification URL: {data.get('verification_url')}")
        else:
            print(f"   ❌ Error: {data.get('error')}")
            
        print(f"\n   الاستجابة الكاملة:")
        print(f"   {json.dumps(data, indent=2, ensure_ascii=False)}")
        
    except json.JSONDecodeError:
        print(f"   Response body: {response.content[:500]}")
else:
    print(f"   ❌ HTTP Error: {response.status_code}")
    print(f"   Response: {response.content[:500]}")

# Check invoice again
invoice.refresh_from_db()
print(f"\n🔍 حالة الفاتورة بعد الطلب:")
print(f"   UUID: {invoice.jofotara_uuid or 'غير موجود'}")
print(f"   QR Code: {'✅ موجود (' + str(len(invoice.jofotara_qr_code)) + ' حرف)' if invoice.jofotara_qr_code else '❌ غير موجود'}")
print(f"   Posted: {invoice.is_posted_to_tax}")

print("\n" + "=" * 70)

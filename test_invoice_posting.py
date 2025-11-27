#!/usr/bin/env python
"""
Test posting invoice TEST-TAX-2 to JoFotara
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesInvoice
from settings.utils import send_invoice_to_jofotara as send_invoice_api
from settings.models import CompanySettings

print("=" * 70)
print("اختبار ترحيل فاتورة TEST-TAX-2")
print("=" * 70)

# Get invoice
try:
    invoice = SalesInvoice.objects.get(invoice_number='TEST-TAX-2')
except SalesInvoice.DoesNotExist:
    print("❌ الفاتورة TEST-TAX-2 غير موجودة!")
    exit(1)

print(f"\n✅ وجدت الفاتورة: {invoice.invoice_number}")
print(f"   Customer: {invoice.customer.name}")
print(f"   Total: {invoice.total_amount}")
print(f"   Current Posted Status: {invoice.is_posted_to_tax}")
print(f"   Current UUID: {invoice.jofotara_uuid or 'غير موجود'}")
print(f"   Current QR Code: {'موجود' if invoice.jofotara_qr_code else 'غير موجود'}")

# Get company
company = CompanySettings.objects.first()

# Prepare data
print("\n🔄 تحضير البيانات للإرسال...")
invoice_data = {
    'invoice_number': invoice.invoice_number,
    'issue_date': invoice.date.isoformat(),
    'issue_time': invoice.created_at.time().isoformat(),
    'seller': {
        'name': company.company_name if company else 'Test Company',
        'tax_number': company.tax_number if company else '123456789',
    },
    'buyer': {
        'name': invoice.customer.name,
        'tax_number': getattr(invoice.customer, 'tax_number', ''),
    },
    'lines': [
        {
            'product_name': item.product.name,
            'quantity': float(item.quantity),
            'unit_price': float(item.unit_price),
            'tax_percent': float(item.tax_rate),
            'total': float(item.total_amount),
        } for item in invoice.items.all()
    ],
    'currency': 'JOD',
}

print(f"   ✅ عدد المنتجات: {len(invoice_data['lines'])}")

# Send to JoFotara
print("\n📤 إرسال إلى JoFotara API...")
result = send_invoice_api(invoice_data, 'sales')

print("\n📬 النتيجة:")
print(f"   Success: {result.get('success')}")

if result.get('success'):
    print(f"   ✅ UUID: {result.get('uuid')}")
    print(f"   ✅ QR Code: {'موجود' if result.get('qr_code') else '❌ غير موجود'}")
    
    if result.get('qr_code'):
        qr_len = len(result['qr_code'])
        qr_preview = result['qr_code'][:60]
        print(f"   ✅ QR Code Length: {qr_len}")
        print(f"   ✅ QR Code Preview: {qr_preview}...")
    
    print(f"   ✅ Verification URL: {result.get('verification_url')}")
    
    # Update invoice
    print("\n💾 تحديث الفاتورة...")
    invoice.jofotara_uuid = result.get('uuid')
    invoice.jofotara_verification_url = result.get('verification_url')
    invoice.jofotara_qr_code = result.get('qr_code')
    invoice.is_posted_to_tax = True if result.get('qr_code') else False
    invoice.save()
    
    print("   ✅ تم الحفظ بنجاح!")
    
    # Verify
    invoice.refresh_from_db()
    print("\n🔍 التحقق من الحفظ:")
    print(f"   UUID: {invoice.jofotara_uuid}")
    print(f"   QR Code: {'✅ موجود (' + str(len(invoice.jofotara_qr_code)) + ' حرف)' if invoice.jofotara_qr_code else '❌ غير موجود'}")
    print(f"   Posted: {invoice.is_posted_to_tax}")
else:
    print(f"   ❌ Error: {result.get('error')}")

print("\n" + "=" * 70)

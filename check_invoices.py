#!/usr/bin/env python
"""
Check posted invoices in database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesInvoice

print("=" * 70)
print("فحص الفواتير المرحلة في قاعدة البيانات")
print("=" * 70)

invoices = SalesInvoice.objects.filter(is_posted_to_tax=True).order_by('-created_at')[:5]

if not invoices:
    print("\n❌ لا توجد فواتير مرحلة في قاعدة البيانات!")
else:
    print(f"\n✅ وجدت {invoices.count()} فاتورة مرحلة:\n")
    
    for inv in invoices:
        print(f"📄 {inv.invoice_number}")
        print(f"   Posted to Tax: {inv.is_posted_to_tax}")
        print(f"   UUID: {inv.jofotara_uuid or 'غير موجود'}")
        print(f"   Sent At: {inv.jofotara_sent_at or 'غير موجود'}")
        
        if inv.jofotara_qr_code:
            qr_len = len(inv.jofotara_qr_code)
            qr_preview = inv.jofotara_qr_code[:50]
            print(f"   QR Code: ✅ موجود ({qr_len} حرف)")
            print(f"   QR Preview: {qr_preview}...")
        else:
            print(f"   QR Code: ❌ غير موجود")
        
        print()

print("=" * 70)

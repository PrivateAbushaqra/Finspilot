import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesReturn

try:
    sr = SalesReturn.objects.get(id=4)
    print(f"📦 Return Number: {sr.return_number}")
    print(f"   Posted to Tax: {sr.is_posted_to_tax}")
    print(f"   UUID: {sr.jofotara_uuid or 'غير موجود'}")
    
    if sr.jofotara_qr_code:
        print(f"   QR Code: ✅ موجود ({len(sr.jofotara_qr_code)} حرف)")
    else:
        print(f"   QR Code: ❌ غير موجود")
        print(f"\n⚠️ المستند مرحل لكن لا يوجد QR Code!")
        
    # Check customer
    print(f"\n👤 Customer: {sr.customer.name}")
    if sr.original_invoice:
        print(f"📄 Original Invoice: {sr.original_invoice.invoice_number}")
    
except SalesReturn.DoesNotExist:
    print("❌ المستند رقم 4 غير موجود")

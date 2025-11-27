import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesReturn
from settings.utils import send_return_to_jofotara

try:
    sr = SalesReturn.objects.get(id=4)
    print(f"📦 Testing Return: {sr.return_number}")
    print(f"   Current Status - Posted: {sr.is_posted_to_tax}, UUID: {sr.jofotara_uuid or 'غير موجود'}")
    
    # Reset posting status to test again
    sr.is_posted_to_tax = False
    sr.jofotara_uuid = None
    sr.jofotara_qr_code = None
    sr.jofotara_verification_url = None
    sr.jofotara_sent_at = None
    sr.save()
    print(f"\n🔄 Reset posting status...")
    
    # Try posting
    print(f"\n📤 Attempting to post to JoFotara...")
    result = send_return_to_jofotara(sr)
    
    # Refresh from database
    sr.refresh_from_db()
    
    print(f"\n✅ Result:")
    print(f"   Success: {result.get('success')}")
    print(f"   Posted: {sr.is_posted_to_tax}")
    print(f"   UUID: {sr.jofotara_uuid or 'غير موجود'}")
    
    if sr.jofotara_qr_code:
        print(f"   QR Code: ✅ موجود ({len(sr.jofotara_qr_code)} حرف)")
        print(f"   First 50 chars: {sr.jofotara_qr_code[:50]}")
    else:
        print(f"   QR Code: ❌ غير موجود")
        print(f"\n⚠️ ERROR: {result.get('error', 'Unknown error')}")
        
except SalesReturn.DoesNotExist:
    print("❌ المستند رقم 4 غير موجود")
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

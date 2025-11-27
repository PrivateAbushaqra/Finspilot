import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesReturn
from settings.utils import send_return_to_jofotara

try:
    sr = SalesReturn.objects.get(id=4)
    print(f"📦 Testing Return: {sr.return_number}")
    
    # Call the API function directly
    print(f"\n📤 Calling send_return_to_jofotara...")
    result = send_return_to_jofotara(sr)
    
    print(f"\n📋 Full Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print(f"\n🔍 Checking fields:")
    print(f"   'success' in result: {'success' in result}")
    print(f"   result['success']: {result.get('success')}")
    print(f"   'uuid' in result: {'uuid' in result}")
    print(f"   'qr_code' in result: {'qr_code' in result}")
    
    if 'qr_code' in result:
        qr = result['qr_code']
        print(f"   QR Code length: {len(qr)}")
        print(f"   QR Code starts with: {qr[:50] if qr else 'None'}")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

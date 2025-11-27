import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesReturn
from settings.utils import send_return_to_jofotara

try:
    sr = SalesReturn.objects.get(id=4)
    print(f"📦 Return: {sr.return_number}")
    
    # Call API
    result = send_return_to_jofotara(sr)
    
    print(f"\n🔍 Type checking:")
    print(f"   type(result): {type(result)}")
    print(f"   type(result['success']): {type(result.get('success'))}")
    print(f"   result['success'] value: {result.get('success')}")
    print(f"   result['success'] == True: {result.get('success') == True}")
    print(f"   result['success'] is True: {result.get('success') is True}")
    
    # Test the condition
    if result['success']:
        print(f"\n✅ if result['success']: PASSED")
        
        if 'uuid' in result:
            print(f"✅ if 'uuid' in result: PASSED")
            print(f"   UUID: {result['uuid']}")
            print(f"   QR Code length: {len(result.get('qr_code', ''))}")
            
            # Try to save
            sr.jofotara_uuid = result['uuid']
            sr.jofotara_qr_code = result.get('qr_code')
            sr.is_posted_to_tax = True
            sr.save()
            
            # Verify
            sr.refresh_from_db()
            print(f"\n✅ Saved to database:")
            print(f"   UUID in DB: {sr.jofotara_uuid}")
            print(f"   QR Code in DB: {'موجود' if sr.jofotara_qr_code else '❌ غير موجود'}")
            print(f"   Posted: {sr.is_posted_to_tax}")
        else:
            print(f"❌ if 'uuid' in result: FAILED")
    else:
        print(f"❌ if result['success']: FAILED")
        
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

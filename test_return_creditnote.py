#!/usr/bin/env python
"""
Test posting sales return and credit note to JoFotara
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesReturn, SalesCreditNote
from settings.utils import send_return_to_jofotara, send_credit_note_to_jofotara
from settings.models import CompanySettings
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 70)
print("اختبار ترحيل المردود والإشعار الدائن")
print("=" * 70)

user = User.objects.filter(is_superuser=True).first()

# Test Sales Return
print("\n📦 اختبار مردود المبيعات:")
try:
    sales_return = SalesReturn.objects.first()
    if sales_return:
        print(f"  ✅ المردود: {sales_return.return_number}")
        print(f"  Current Posted: {sales_return.is_posted_to_tax}")
        print(f"  Current QR: {'موجود' if sales_return.jofotara_qr_code else 'غير موجود'}")
        
        print("\n  🔄 إرسال إلى JoFotara...")
        result = send_return_to_jofotara(sales_return, user)
        
        print(f"\n  📬 النتيجة:")
        print(f"     Success: {result.get('success')}")
        
        if result.get('success'):
            print(f"     ✅ UUID: {result.get('uuid')}")
            print(f"     ✅ QR Code: {'موجود' if result.get('qr_code') else '❌ غير موجود'}")
            
            if result.get('qr_code'):
                print(f"     ✅ QR Length: {len(result['qr_code'])}")
                print(f"     ✅ QR Preview: {result['qr_code'][:60]}...")
            
            # Save
            sales_return.jofotara_uuid = result.get('uuid')
            sales_return.jofotara_verification_url = result.get('verification_url')
            sales_return.jofotara_qr_code = result.get('qr_code')
            sales_return.is_posted_to_tax = True if result.get('qr_code') else False
            sales_return.save()
            
            print("     ✅ تم الحفظ!")
            
            # Verify
            sales_return.refresh_from_db()
            print(f"\n  🔍 التحقق:")
            print(f"     UUID: {sales_return.jofotara_uuid}")
            print(f"     QR: {'✅ موجود (' + str(len(sales_return.jofotara_qr_code)) + ')' if sales_return.jofotara_qr_code else '❌ غير موجود'}")
        else:
            print(f"     ❌ Error: {result.get('error')}")
    else:
        print("  ❌ لا توجد مردودات")
except Exception as e:
    print(f"  ❌ خطأ: {str(e)}")
    import traceback
    traceback.print_exc()

# Test Credit Note
print("\n" + "=" * 70)
print("\n💳 اختبار الإشعار الدائن:")
try:
    credit_note = SalesCreditNote.objects.first()
    if credit_note:
        print(f"  ✅ الإشعار: {credit_note.note_number}")
        print(f"  Current Posted: {credit_note.is_posted_to_tax}")
        print(f"  Current QR: {'موجود' if credit_note.jofotara_qr_code else 'غير موجود'}")
        
        print("\n  🔄 إرسال إلى JoFotara...")
        result = send_credit_note_to_jofotara(credit_note, user)
        
        print(f"\n  📬 النتيجة:")
        print(f"     Success: {result.get('success')}")
        
        if result.get('success'):
            print(f"     ✅ UUID: {result.get('uuid')}")
            print(f"     ✅ QR Code: {'موجود' if result.get('qr_code') else '❌ غير موجود'}")
            
            if result.get('qr_code'):
                print(f"     ✅ QR Length: {len(result['qr_code'])}")
                print(f"     ✅ QR Preview: {result['qr_code'][:60]}...")
            
            # Save
            credit_note.jofotara_uuid = result.get('uuid')
            credit_note.jofotara_verification_url = result.get('verification_url')
            credit_note.jofotara_qr_code = result.get('qr_code')
            credit_note.is_posted_to_tax = True if result.get('qr_code') else False
            credit_note.save()
            
            print("     ✅ تم الحفظ!")
            
            # Verify
            credit_note.refresh_from_db()
            print(f"\n  🔍 التحقق:")
            print(f"     UUID: {credit_note.jofotara_uuid}")
            print(f"     QR: {'✅ موجود (' + str(len(credit_note.jofotara_qr_code)) + ')' if credit_note.jofotara_qr_code else '❌ غير موجود'}")
        else:
            print(f"     ❌ Error: {result.get('error')}")
    else:
        print("  ❌ لا توجد إشعارات دائنة")
except Exception as e:
    print(f"  ❌ خطأ: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("اكتمل الاختبار!")
print("=" * 70)

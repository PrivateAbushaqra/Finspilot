import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from purchases.models import PurchaseInvoice, PurchaseReturn, PurchaseDebitNote
from settings.utils import send_purchase_invoice_to_jofotara, send_purchase_return_to_jofotara, send_purchase_debit_note_to_jofotara
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(username='super')

# Read IDs from file
ids = {}
try:
    with open('test_purchases_ids.txt', 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=')
                ids[key] = int(value) if value != 'None' else None
except FileNotFoundError:
    print("❌ لم يتم العثور على ملف test_purchases_ids.txt")
    exit(1)

print("=" * 60)
print("📤 اختبار ترحيل المستندات إلى JoFotara")
print("=" * 60)

# Test Invoice
if ids.get('invoice_id'):
    print(f"\n1️⃣ اختبار ترحيل فاتورة المشتريات ID={ids['invoice_id']}...")
    try:
        invoice = PurchaseInvoice.objects.get(id=ids['invoice_id'])
        result = send_purchase_invoice_to_jofotara(invoice, user)
        
        if result['success']:
            invoice.refresh_from_db()
            print(f"   ✅ تم الترحيل بنجاح")
            print(f"   UUID: {invoice.jofotara_uuid}")
            print(f"   Posted: {invoice.is_posted_to_tax}")
            print(f"   QR Code: {'موجود (' + str(len(invoice.jofotara_qr_code)) + ' حرف)' if invoice.jofotara_qr_code else 'غير موجود'}")
        else:
            print(f"   ❌ فشل الترحيل: {result.get('error')}")
    except Exception as e:
        print(f"   ❌ خطأ: {e}")

# Test Return
if ids.get('return_id'):
    print(f"\n2️⃣ اختبار ترحيل مردود المشتريات ID={ids['return_id']}...")
    try:
        purchase_return = PurchaseReturn.objects.get(id=ids['return_id'])
        result = send_purchase_return_to_jofotara(purchase_return, user)
        
        if result['success']:
            purchase_return.refresh_from_db()
            print(f"   ✅ تم الترحيل بنجاح")
            print(f"   UUID: {purchase_return.jofotara_uuid}")
            print(f"   Posted: {purchase_return.is_posted_to_tax}")
            print(f"   QR Code: {'موجود (' + str(len(purchase_return.jofotara_qr_code)) + ' حرف)' if purchase_return.jofotara_qr_code else 'غير موجود'}")
        else:
            print(f"   ❌ فشل الترحيل: {result.get('error')}")
    except Exception as e:
        print(f"   ❌ خطأ: {e}")
        import traceback
        traceback.print_exc()

# Test Debit Note
if ids.get('debit_id'):
    print(f"\n3️⃣ اختبار ترحيل الإشعار المدين ID={ids['debit_id']}...")
    try:
        debit_note = PurchaseDebitNote.objects.get(id=ids['debit_id'])
        result = send_purchase_debit_note_to_jofotara(debit_note, user)
        
        if result['success']:
            debit_note.refresh_from_db()
            print(f"   ✅ تم الترحيل بنجاح")
            print(f"   UUID: {debit_note.jofotara_uuid}")
            print(f"   Posted: {debit_note.is_posted_to_tax}")
            print(f"   QR Code: {'موجود (' + str(len(debit_note.jofotara_qr_code)) + ' حرف)' if debit_note.jofotara_qr_code else 'غير موجود'}")
        else:
            print(f"   ❌ فشل الترحيل: {result.get('error')}")
    except Exception as e:
        print(f"   ❌ خطأ: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("✅ اكتمل الاختبار")
print("=" * 60)

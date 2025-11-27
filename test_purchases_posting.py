import os
import django
import requests
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

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

# Login and get session
session = requests.Session()
login_url = 'http://127.0.0.1:8000/ar/accounts/login/'
login_data = {
    'username': 'super',
    'password': 'password'
}

# Get CSRF token
response = session.get(login_url)
csrf_token = session.cookies.get('csrftoken')

# Login
login_data['csrfmiddlewaretoken'] = csrf_token
response = session.post(login_url, data=login_data, headers={'Referer': login_url})

if response.status_code == 200:
    print("✅ تم تسجيل الدخول بنجاح")
else:
    print(f"❌ فشل تسجيل الدخول: {response.status_code}")
    exit(1)

print("\n" + "=" * 60)
print("📤 اختبار ترحيل المستندات إلى JoFotara")
print("=" * 60)

# Test Invoice
if ids.get('invoice_id'):
    print(f"\n1️⃣ اختبار ترحيل فاتورة المشتريات ID={ids['invoice_id']}...")
    url = f"http://127.0.0.1:8000/ar/purchases/invoices/{ids['invoice_id']}/send-to-jofotara/"
    
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': session.cookies.get('csrftoken'),
        'Content-Type': 'application/json'
    }
    
    response = session.post(url, headers=headers, json={})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"   ✅ تم الترحيل بنجاح")
            print(f"   UUID: {data.get('uuid')}")
            print(f"   QR Code: {'موجود' if data.get('qr_code') else 'غير موجود'}")
            print(f"   QR Length: {len(data.get('qr_code', ''))} حرف")
        else:
            print(f"   ❌ فشل الترحيل: {data.get('error')}")
    else:
        print(f"   ❌ خطأ HTTP: {response.status_code}")

# Test Return
if ids.get('return_id'):
    print(f"\n2️⃣ اختبار ترحيل مردود المشتريات ID={ids['return_id']}...")
    url = f"http://127.0.0.1:8000/ar/purchases/returns/{ids['return_id']}/send-to-jofotara/"
    
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': session.cookies.get('csrftoken'),
        'Content-Type': 'application/json'
    }
    
    response = session.post(url, headers=headers, json={})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"   ✅ تم الترحيل بنجاح")
            print(f"   UUID: {data.get('uuid')}")
            print(f"   QR Code: {'موجود' if data.get('qr_code') else 'غير موجود'}")
            print(f"   QR Length: {len(data.get('qr_code', ''))} حرف")
        else:
            print(f"   ❌ فشل الترحيل: {data.get('error')}")
    else:
        print(f"   ❌ خطأ HTTP: {response.status_code}")

# Test Debit Note
if ids.get('debit_id'):
    print(f"\n3️⃣ اختبار ترحيل الإشعار المدين ID={ids['debit_id']}...")
    url = f"http://127.0.0.1:8000/ar/purchases/debit-notes/{ids['debit_id']}/send-to-jofotara/"
    
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': session.cookies.get('csrftoken'),
        'Content-Type': 'application/json'
    }
    
    response = session.post(url, headers=headers, json={})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"   ✅ تم الترحيل بنجاح")
            print(f"   UUID: {data.get('uuid')}")
            print(f"   QR Code: {'موجود' if data.get('qr_code') else 'غير موجود'}")
            print(f"   QR Length: {len(data.get('qr_code', ''))} حرف")
        else:
            print(f"   ❌ فشل الترحيل: {data.get('error')}")
    else:
        print(f"   ❌ خطأ HTTP: {response.status_code}")

print("\n" + "=" * 60)
print("✅ اكتمل الاختبار")
print("=" * 60)

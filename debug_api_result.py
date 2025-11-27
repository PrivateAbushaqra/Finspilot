import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from purchases.models import PurchaseInvoice
from settings.utils import send_purchase_invoice_to_jofotara
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(username='super')

ids = {}
with open('test_purchases_ids.txt', 'r') as f:
    for line in f:
        if '=' in line:
            key, value = line.strip().split('=')
            ids[key] = int(value) if value != 'None' else None

invoice = PurchaseInvoice.objects.get(id=ids['invoice_id'])
result = send_purchase_invoice_to_jofotara(invoice, user)

print("Full Result:")
print(json.dumps(result, indent=2, ensure_ascii=False))

print(f"\n'success' in result: {'success' in result}")
print(f"result['success']: {result.get('success')}")
print(f"'uuid' in result: {'uuid' in result}")
print(f"'qr_code' in result: {'qr_code' in result}")

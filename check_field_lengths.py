import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from purchases.models import PurchaseInvoice

# Read IDs
ids = {}
with open('test_purchases_ids.txt', 'r') as f:
    for line in f:
        if '=' in line:
            key, value = line.strip().split('=')
            ids[key] = int(value) if value != 'None' else None

invoice = PurchaseInvoice.objects.get(id=ids['invoice_id'])
print(f"Invoice Number: '{invoice.invoice_number}' (Length: {len(invoice.invoice_number)})")
print(f"Supplier Invoice Number: '{invoice.supplier_invoice_number}' (Length: {len(invoice.supplier_invoice_number)})")
print(f"Payment Type: '{invoice.payment_type}' (Length: {len(invoice.payment_type)})")
print(f"Payment Method: '{invoice.payment_method}' (Length: {len(invoice.payment_method)})")

# Check if any field is too long
for field in invoice._meta.fields:
    if field.name in ['invoice_number', 'supplier_invoice_number', 'payment_type', 'payment_method']:
        value = getattr(invoice, field.name)
        if value and hasattr(field, 'max_length') and field.max_length:
            print(f"\nField: {field.name}")
            print(f"  Value: '{value}'")
            print(f"  Length: {len(str(value))}")
            print(f"  Max Length: {field.max_length}")
            if len(str(value)) > field.max_length:
                print(f"  ⚠️ TOO LONG!")

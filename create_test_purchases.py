import os
import django
from datetime import date
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.contrib.auth import get_user_model
from customers.models import CustomerSupplier
from purchases.models import PurchaseInvoice, PurchaseInvoiceItem, PurchaseReturn, PurchaseReturnItem, PurchaseDebitNote
from products.models import Product
from inventory.models import Warehouse
from cashboxes.models import Cashbox

User = get_user_model()

# Get super user
user = User.objects.get(username='super')

# Get or create supplier
supplier, _ = CustomerSupplier.objects.get_or_create(
    name='Test Supplier For JoFotara',
    defaults={
        'type': 'supplier',
        'phone': '0799123456',
        'email': 'test@supplier.com',
        'address': 'Test Address',
        'tax_number': '123456789'
    }
)

# Get products
try:
    product1 = Product.objects.first()
    if not product1:
        print("❌ لا توجد منتجات في النظام")
        exit(1)
except Exception as e:
    print(f"❌ خطأ: {e}")
    exit(1)

# Get warehouse
warehouse = Warehouse.objects.first()

# Get cashbox
cashbox = Cashbox.objects.first()

print("=" * 60)
print("📦 إنشاء مستندات اختبار للمشتريات")
print("=" * 60)

# 1. Create Purchase Invoice
print("\n1️⃣ إنشاء فاتورة مشتريات...")
try:
    invoice = PurchaseInvoice.objects.create(
        invoice_number='TEST-PURCH-001',
        supplier_invoice_number='SUPP-INV-001',
        date=date.today(),
        supplier=supplier,
        warehouse=warehouse,
        payment_type='cash',
        payment_method='cash',
        cashbox=cashbox,
        is_tax_inclusive=True,
        subtotal=Decimal('100.000'),
        tax_amount=Decimal('16.000'),
        total_amount=Decimal('116.000'),
        created_by=user
    )
    
    # Add item
    PurchaseInvoiceItem.objects.create(
        invoice=invoice,
        product=product1,
        quantity=Decimal('10'),
        unit_price=Decimal('10.000'),
        tax_rate=Decimal('16.00'),
        total_amount=Decimal('116.000')
    )
    
    # Store the invoice item for use in return
    invoice_item = invoice.items.first()
    
    print(f"   ✅ تم إنشاء فاتورة: {invoice.invoice_number} (ID: {invoice.id})")
    invoice_id = invoice.id
except Exception as e:
    print(f"   ❌ خطأ: {e}")
    invoice_id = None
    invoice_item = None

# 2. Create Purchase Return
print("\n2️⃣ إنشاء مردود مشتريات...")
try:
    if invoice_id and invoice_item:
        purchase_return = PurchaseReturn.objects.create(
            return_number='TEST-PRET-001',
            supplier_return_number='SUPP-RET-001',
            original_invoice=invoice,
            date=date.today(),
            return_type='partial',
            return_reason='defective',
            subtotal=Decimal('50.000'),
            tax_amount=Decimal('8.000'),
            total_amount=Decimal('58.000'),
            created_by=user
        )
        
        # Add item
        PurchaseReturnItem.objects.create(
            return_invoice=purchase_return,
            original_item=invoice_item,
            product=product1,
            returned_quantity=Decimal('5'),
            unit_price=Decimal('10.000'),
            tax_rate=Decimal('16.00'),
            total_amount=Decimal('58.000')
        )
        
        print(f"   ✅ تم إنشاء مردود: {purchase_return.return_number} (ID: {purchase_return.id})")
        return_id = purchase_return.id
    else:
        print("   ⚠️ تخطي إنشاء المردود - لا توجد فاتورة")
        return_id = None
except Exception as e:
    print(f"   ❌ خطأ: {e}")
    import traceback
    traceback.print_exc()
    return_id = None

# 3. Create Debit Note
print("\n3️⃣ إنشاء إشعار مدين...")
try:
    debit_note = PurchaseDebitNote.objects.create(
        note_number='TEST-DEBIT-001',
        supplier_debit_note_number='SUPP-DEBIT-001',
        date=date.today(),
        supplier=supplier,
        subtotal=Decimal('30.000'),
        total_amount=Decimal('30.000'),
        notes='إشعار مدين تجريبي',
        created_by=user
    )
    
    print(f"   ✅ تم إنشاء إشعار مدين: {debit_note.note_number} (ID: {debit_note.id})")
    debit_id = debit_note.id
except Exception as e:
    print(f"   ❌ خطأ: {e}")
    debit_id = None

print("\n" + "=" * 60)
print("📋 ملخص المستندات المُنشأة:")
print("=" * 60)
if invoice_id:
    print(f"✅ فاتورة مشتريات: ID={invoice_id}, URL: http://127.0.0.1:8000/ar/purchases/invoices/{invoice_id}/")
if return_id:
    print(f"✅ مردود مشتريات: ID={return_id}, URL: http://127.0.0.1:8000/ar/purchases/returns/{return_id}/")
if debit_id:
    print(f"✅ إشعار مدين: ID={debit_id}, URL: http://127.0.0.1:8000/ar/purchases/debit-notes/{debit_id}/")

# Save IDs to file for cleanup later
with open('test_purchases_ids.txt', 'w') as f:
    f.write(f"invoice_id={invoice_id}\n")
    f.write(f"return_id={return_id}\n")
    f.write(f"debit_id={debit_id}\n")
    f.write(f"supplier_id={supplier.id}\n")

print("\n✅ تم حفظ IDs في ملف test_purchases_ids.txt")

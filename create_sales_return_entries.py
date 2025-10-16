import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesReturn
from sales.views import create_sales_return_journal_entry, create_sales_return_account_transaction
from inventory.models import InventoryMovement
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date

User = get_user_model()

print("=== إنشاء القيود والحركات لمردود المبيعات ===")

# الحصول على مردود المبيعات
sales_return = SalesReturn.objects.filter(return_number='TEST-SALES-RET-001').first()
if not sales_return:
    print("لا يوجد مردود مبيعات")
    exit()

print(f"مردود المبيعات: {sales_return.return_number}")
print(f"القيمة الإجمالية: {sales_return.total_amount}")

# إنشاء حركة المخزون إذا لم تكن موجودة
inventory_movements = InventoryMovement.objects.filter(reference_type='sales_return', reference_id=sales_return.id)
if not inventory_movements.exists():
    sales_return_item = sales_return.items.first()
    if sales_return_item:
        inventory_movement = InventoryMovement.objects.create(
            movement_number=f'MOV-{sales_return.id:04d}',
            date=date.today(),
            product=sales_return_item.product,
            warehouse=sales_return.original_invoice.warehouse,
            movement_type='in',
            reference_type='sales_return',
            reference_id=sales_return.id,
            quantity=sales_return_item.quantity,
            unit_cost=sales_return_item.unit_price,
            total_cost=sales_return_item.total_amount,
            notes=f'مردود مبيعات {sales_return.return_number}',
            created_by=sales_return.created_by
        )
        print("تم إنشاء حركة المخزون (in)")
else:
    print("حركة المخزون موجودة بالفعل")

# إنشاء القيد المحاسبي
try:
    journal_entry = create_sales_return_journal_entry(sales_return, sales_return.created_by)
    print(f"تم إنشاء القيد المحاسبي: {journal_entry.entry_number}")
except Exception as e:
    print(f"خطأ في إنشاء القيد المحاسبي: {e}")

# إنشاء حركة الحساب
try:
    account_transaction = create_sales_return_account_transaction(sales_return, sales_return.created_by)
    print("تم إنشاء حركة الحساب")
except Exception as e:
    print(f"خطأ في إنشاء حركة الحساب: {e}")

print("\n=== فحص النتائج ===")

# فحص القيود والحركات
from journal.models import JournalEntry
from accounts.models import AccountTransaction

journal_entries = JournalEntry.objects.filter(reference_type='sales_return', reference_id=sales_return.id)
account_transactions = AccountTransaction.objects.filter(reference_type='sales_return', reference_id=sales_return.id)
inventory_movements = InventoryMovement.objects.filter(reference_type='sales_return', reference_id=sales_return.id)

print(f"قيود محاسبية: {journal_entries.count()}")
print(f"حركات حساب: {account_transactions.count()}")
print(f"حركات مخزون: {inventory_movements.count()}")

if journal_entries.exists():
    je = journal_entries.first()
    print(f"رقم القيد: {je.entry_number}")
    print("تفاصيل القيد:")
    for detail in je.lines.all():
        print(f"  {detail.account.name}: {'مدين' if detail.debit > 0 else 'دائن'} {detail.debit or detail.credit}")

print("\n=== الانتهاء ===")
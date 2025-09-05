import os
import sys
import django

# إعداد Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from purchases.models import PurchaseReturn
from customers.models import CustomerSupplier
from accounts.models import AccountTransaction

print("تحليل المشكلة:")
print("=" * 50)

try:
    # فحص مردود المشتريات
    purchase_return = PurchaseReturn.objects.get(id=2)
    supplier = purchase_return.original_invoice.supplier
    
    print(f"مردود المشتريات رقم 2:")
    print(f"  - رقم المردود: {purchase_return.return_number}")
    print(f"  - تاريخ: {purchase_return.date}")
    print(f"  - المبلغ: {purchase_return.total_amount}")
    print(f"  - المورد: {supplier.name} (معرف: {supplier.id})")
    print(f"  - نوع المورد: {supplier.type}")
    
    # فحص العميل رقم 14
    customer = CustomerSupplier.objects.get(id=14)
    print(f"\nالعميل رقم 14:")
    print(f"  - الاسم: {customer.name}")
    print(f"  - النوع: {customer.type}")
    
    # هل هما نفس الكيان؟
    if supplier.id == customer.id:
        print("\n✓ المورد والعميل هما نفس الكيان")
    else:
        print(f"\n✗ المورد والعميل كيانان منفصلان")
        print(f"  - معرف المورد: {supplier.id}")
        print(f"  - معرف العميل: {customer.id}")
    
    # فحص معاملات الحساب لمردود المشتريات
    return_transactions = AccountTransaction.objects.filter(
        transaction_type='purchase_return',
        reference_id=str(purchase_return.id)
    )
    
    print(f"\nمعاملات مردود المشتريات:")
    print(f"  - عدد المعاملات: {return_transactions.count()}")
    
    for trans in return_transactions:
        print(f"  - المرتبط بالكيان: {trans.customer_supplier.name} (معرف: {trans.customer_supplier.id})")
        print(f"  - نوع الكيان: {trans.customer_supplier.type}")
        print(f"  - المبلغ: {trans.amount}")
        print(f"  - الاتجاه: {trans.direction}")
    
    # فحص معاملات العميل رقم 14
    customer_transactions = AccountTransaction.objects.filter(customer_supplier=customer)
    print(f"\nمعاملات العميل رقم 14:")
    print(f"  - عدد المعاملات: {customer_transactions.count()}")
    
    for trans in customer_transactions:
        print(f"  - {trans.transaction_type}: {trans.reference_id} - {trans.amount}")

except Exception as e:
    print(f"خطأ: {e}")
    import traceback
    traceback.print_exc()

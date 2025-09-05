import os
import sys
import django

# إعداد Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from purchases.models import PurchaseReturn
from customers.models import Customer
from accounts.models import AccountTransaction

print("فحص مردود المشتريات رقم 2:")
print("=" * 50)

try:
    purchase_return = PurchaseReturn.objects.get(id=2)
    print(f"رقم المردود: {purchase_return.id}")
    print(f"رقم المردود: {purchase_return.return_number}")
    print(f"المورد: {purchase_return.supplier}")
    print(f"التاريخ: {purchase_return.return_date}")
    print(f"المبلغ الإجمالي: {purchase_return.total_amount}")
    
    # فحص إذا كان المورد هو عميل أيضاً
    try:
        customer = Customer.objects.get(id=14)
        print(f"\nالعميل رقم 14: {customer.name}")
        
        # فحص العلاقة بين المورد والعميل
        if purchase_return.supplier.name == customer.name:
            print("✓ المورد هو نفسه العميل")
        else:
            print(f"✗ المورد ({purchase_return.supplier.name}) مختلف عن العميل ({customer.name})")
            
    except Customer.DoesNotExist:
        print("✗ العميل رقم 14 غير موجود")
    
    # فحص معاملات الحساب المرتبطة
    print(f"\nفحص معاملات الحساب للعميل رقم 14:")
    transactions = AccountTransaction.objects.filter(customer_id=14)
    print(f"عدد المعاملات: {transactions.count()}")
    
    for trans in transactions:
        print(f"- {trans.transaction_type}: {trans.reference_id} - {trans.amount}")
        
    # فحص إذا كان هناك معاملة لمردود المشتريات
    purchase_return_transactions = AccountTransaction.objects.filter(
        transaction_type='purchase_return',
        reference_id=str(purchase_return.id)
    )
    print(f"\nمعاملات مردود المشتريات رقم 2: {purchase_return_transactions.count()}")
    for trans in purchase_return_transactions:
        print(f"- العميل: {trans.customer_id}, المبلغ: {trans.amount}")

except PurchaseReturn.DoesNotExist:
    print("✗ مردود المشتريات رقم 2 غير موجود")

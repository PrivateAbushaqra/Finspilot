#!/usr/bin/env python
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from accounts.models import AccountTransaction
from customers.models import CustomerSupplier

# فحص سريع للمعاملات
customer = CustomerSupplier.objects.get(id=14)
transactions = AccountTransaction.objects.filter(customer_supplier=customer)

print(f"العميل: {customer.name}")
print(f"عدد المعاملات: {transactions.count()}")

for t in transactions:
    print(f"- {t.transaction_type}: {t.reference_id} ({t.amount}) - {t.description}")
    
# فحص معاملات مردود المشتريات
purchase_return_trans = transactions.filter(transaction_type='purchase_return')
print(f"\nمعاملات مردود المشتريات: {purchase_return_trans.count()}")

if purchase_return_trans.exists():
    print("✓ تم العثور على معاملات مردود المشتريات")
else:
    print("✗ لم يتم العثور على معاملات مردود المشتريات")
    
    # إنشاء المعاملة إذا لم تكن موجودة
    from purchases.models import PurchaseReturn
    from decimal import Decimal
    import uuid
    
    try:
        purchase_return = PurchaseReturn.objects.get(id=2)
        
        # حساب الرصيد السابق
        last_transaction = AccountTransaction.objects.filter(
            customer_supplier=customer
        ).order_by('-created_at').first()
        
        previous_balance = last_transaction.balance_after if last_transaction else Decimal('0')
        new_balance = previous_balance + purchase_return.total_amount
        
        # إنشاء المعاملة
        transaction = AccountTransaction.objects.create(
            transaction_number=f"PRET-C-{uuid.uuid4().hex[:8].upper()}",
            date=purchase_return.date,
            customer_supplier=customer,
            transaction_type='purchase_return',
            direction='credit',
            amount=purchase_return.total_amount,
            reference_type='purchase_return',
            reference_id=purchase_return.id,
            description=f'مردود مشتريات - فاتورة رقم {purchase_return.return_number}',
            balance_after=new_balance,
            created_by_id=1
        )
        
        print(f"✓ تم إنشاء معاملة جديدة: {transaction.transaction_number}")
        
    except Exception as e:
        print(f"✗ خطأ في إنشاء المعاملة: {e}")

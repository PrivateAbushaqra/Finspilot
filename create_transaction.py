#!/usr/bin/env python
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from purchases.models import PurchaseReturn
from customers.models import CustomerSupplier
from accounts.models import AccountTransaction
from decimal import Decimal
import uuid

# إنشاء معاملة للعميل رقم 14 مرتبطة بمردود المشتريات رقم 2
try:
    purchase_return = PurchaseReturn.objects.get(id=2)
    customer = CustomerSupplier.objects.get(id=14)
    
    # فحص إذا كانت المعاملة موجودة
    existing = AccountTransaction.objects.filter(
        customer_supplier=customer,
        transaction_type='purchase_return',
        reference_id=purchase_return.id
    ).exists()
    
    if not existing:
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
        
        print(f"تم إنشاء معاملة: {transaction.transaction_number}")
        print(f"العميل: {customer.name}")
        print(f"المبلغ: {transaction.amount}")
        print(f"الرصيد بعد: {transaction.balance_after}")
    else:
        print("المعاملة موجودة مسبقاً")
        
except Exception as e:
    print(f"خطأ: {e}")
    import traceback
    traceback.print_exc()

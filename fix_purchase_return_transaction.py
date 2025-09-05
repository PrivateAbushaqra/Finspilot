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

print("إنشاء معاملة حساب لمردود المشتريات رقم 2:")
print("=" * 50)

try:
    # الحصول على مردود المشتريات
    purchase_return = PurchaseReturn.objects.get(id=2)
    supplier = purchase_return.original_invoice.supplier
    
    print(f"مردود المشتريات: {purchase_return.return_number}")
    print(f"المورد: {supplier.name} (ID: {supplier.id}, نوع: {supplier.type})")
    print(f"المبلغ: {purchase_return.total_amount}")
    
    # البحث عن عميل بنفس الاسم
    matching_customers = CustomerSupplier.objects.filter(
        name=supplier.name,
        type__in=['customer', 'both']
    ).exclude(id=supplier.id)
    
    print(f"عملاء مطابقون: {matching_customers.count()}")
    
    for customer in matching_customers:
        print(f"عميل مطابق: {customer.name} (ID: {customer.id}, نوع: {customer.type})")
        
        # فحص إذا كانت المعاملة موجودة مسبقاً
        existing_transaction = AccountTransaction.objects.filter(
            customer_supplier=customer,
            transaction_type='purchase_return',
            reference_id=purchase_return.id
        ).first()
        
        if existing_transaction:
            print(f"  - المعاملة موجودة مسبقاً: {existing_transaction.transaction_number}")
        else:
            # إنشاء معاملة جديدة للعميل
            customer_transaction_number = f"PRET-C-{uuid.uuid4().hex[:8].upper()}"
            
            # حساب الرصيد السابق للعميل
            last_customer_transaction = AccountTransaction.objects.filter(
                customer_supplier=customer
            ).order_by('-created_at').first()
            
            customer_previous_balance = last_customer_transaction.balance_after if last_customer_transaction else Decimal('0')
            customer_new_balance = customer_previous_balance + purchase_return.total_amount  # دائن للعميل
            
            new_transaction = AccountTransaction.objects.create(
                transaction_number=customer_transaction_number,
                date=purchase_return.date,
                customer_supplier=customer,
                transaction_type='purchase_return',
                direction='credit',  # دائن للعميل (استرداد مبلغ)
                amount=purchase_return.total_amount,
                reference_type='purchase_return',
                reference_id=purchase_return.id,
                description=f'مردود مشتريات - فاتورة رقم {purchase_return.return_number} (عميل مرتبط)',
                balance_after=customer_new_balance,
                created_by_id=1  # افتراض أن admin user له ID = 1
            )
            
            print(f"  ✓ تم إنشاء معاملة: {new_transaction.transaction_number}")
            print(f"    - المبلغ: {new_transaction.amount}")
            print(f"    - الاتجاه: {new_transaction.direction}")
            print(f"    - الرصيد بعد: {new_transaction.balance_after}")

except Exception as e:
    print(f"خطأ: {e}")
    import traceback
    traceback.print_exc()

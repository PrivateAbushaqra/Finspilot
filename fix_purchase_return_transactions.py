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

print("فحص وإصلاح معاملات مردود المشتريات:")
print("=" * 50)

# فحص جميع مردودات المشتريات
purchase_returns = PurchaseReturn.objects.all()
print(f"عدد مردودات المشتريات: {purchase_returns.count()}")

for pr in purchase_returns:
    supplier = pr.original_invoice.supplier
    print(f"\nمردود {pr.id}: {pr.return_number}")
    print(f"  المورد: {supplier.name} (ID: {supplier.id}, نوع: {supplier.type})")
    
    # فحص إذا كانت هناك معاملة حساب لهذا المردود
    existing_transactions = AccountTransaction.objects.filter(
        transaction_type='purchase_return',
        reference_id=pr.id
    )
    
    print(f"  معاملات موجودة: {existing_transactions.count()}")
    
    if existing_transactions.count() == 0:
        print("  ⚠ لا توجد معاملة حساب لهذا المردود - سيتم إنشاؤها")
        
        # إنشاء معاملة للمورد
        transaction_number = f"PRET-{uuid.uuid4().hex[:8].upper()}"
        
        # حساب الرصيد السابق للمورد
        last_transaction = AccountTransaction.objects.filter(
            customer_supplier=supplier
        ).order_by('-created_at').first()
        
        previous_balance = last_transaction.balance_after if last_transaction else Decimal('0')
        new_balance = previous_balance - pr.total_amount
        
        # إنشاء معاملة للمورد
        supplier_transaction = AccountTransaction.objects.create(
            transaction_number=transaction_number,
            date=pr.date,
            customer_supplier=supplier,
            transaction_type='purchase_return',
            direction='debit',
            amount=pr.total_amount,
            reference_type='purchase_return',
            reference_id=pr.id,
            description=f'مردود مشتريات - فاتورة رقم {pr.return_number}',
            balance_after=new_balance,
            created_by_id=1
        )
        
        print(f"  ✓ تم إنشاء معاملة للمورد: {supplier_transaction.transaction_number}")
        
        # البحث عن عميل بنفس الاسم
        matching_customers = CustomerSupplier.objects.filter(
            name=supplier.name,
            type__in=['customer', 'both']
        ).exclude(id=supplier.id)
        
        print(f"  عملاء مطابقون: {matching_customers.count()}")
        
        for customer in matching_customers:
            print(f"    العميل: {customer.name} (ID: {customer.id})")
            
            # فحص إذا كانت هناك معاملة للعميل
            customer_existing = AccountTransaction.objects.filter(
                customer_supplier=customer,
                transaction_type='purchase_return',
                reference_id=pr.id
            ).exists()
            
            if not customer_existing:
                # إنشاء معاملة للعميل
                customer_transaction_number = f"PRET-C-{uuid.uuid4().hex[:8].upper()}"
                
                # حساب الرصيد السابق للعميل
                last_customer_transaction = AccountTransaction.objects.filter(
                    customer_supplier=customer
                ).order_by('-created_at').first()
                
                customer_previous_balance = last_customer_transaction.balance_after if last_customer_transaction else Decimal('0')
                customer_new_balance = customer_previous_balance + pr.total_amount
                
                customer_transaction = AccountTransaction.objects.create(
                    transaction_number=customer_transaction_number,
                    date=pr.date,
                    customer_supplier=customer,
                    transaction_type='purchase_return',
                    direction='credit',
                    amount=pr.total_amount,
                    reference_type='purchase_return',
                    reference_id=pr.id,
                    description=f'مردود مشتريات - فاتورة رقم {pr.return_number} (عميل مرتبط)',
                    balance_after=customer_new_balance,
                    created_by_id=1
                )
                
                print(f"    ✓ تم إنشاء معاملة للعميل: {customer_transaction.transaction_number}")
            else:
                print(f"    ✓ معاملة العميل موجودة مسبقاً")
    else:
        print("  ✓ معاملات موجودة:")
        for trans in existing_transactions:
            print(f"    - {trans.transaction_number}: {trans.customer_supplier.name}")

print("\nتم الانتهاء من الفحص والإصلاح")

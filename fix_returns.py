#!/usr/bin/env python
"""
اختبار سريع لتصحيح معاملات مردود المشتريات الموجودة
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from accounts.models import AccountTransaction
from purchases.models import PurchaseReturn

def fix_existing_return_transactions():
    """تصحيح معاملات المردود الموجودة"""
    
    # البحث عن معاملات مردود المشتريات بالاتجاه الخاطئ
    wrong_direction_transactions = AccountTransaction.objects.filter(
        transaction_type='purchase_return',
        direction='debit'  # الاتجاه الخاطئ
    )
    
    print(f"عدد المعاملات التي تحتاج تصحيح: {wrong_direction_transactions.count()}")
    
    for transaction in wrong_direction_transactions:
        print(f"تصحيح معاملة: {transaction.transaction_number}")
        
        # تغيير الاتجاه إلى credit
        transaction.direction = 'credit'
        
        # إعادة حساب الرصيد
        from decimal import Decimal
        
        # البحث عن المعاملة السابقة
        previous_transaction = AccountTransaction.objects.filter(
            customer_supplier=transaction.customer_supplier,
            created_at__lt=transaction.created_at
        ).order_by('-created_at').first()
        
        previous_balance = previous_transaction.balance_after if previous_transaction else Decimal('0')
        new_balance = previous_balance - transaction.amount  # طرح لأنه مردود
        
        transaction.balance_after = new_balance
        transaction.save()
        
        print(f"✅ تم تصحيح: {transaction.transaction_number}")
    
    print("✅ تم الانتهاء من التصحيح")

if __name__ == "__main__":
    fix_existing_return_transactions()

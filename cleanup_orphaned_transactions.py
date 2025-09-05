#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from accounts.models import AccountTransaction
from payments.models import PaymentVoucher
from purchases.models import PurchaseInvoice, PurchaseReturn, PurchaseDebitNote
from receipts.models import PaymentReceipt
from sales.models import SalesInvoice, SalesReturn

print("=== تنظيف المعاملات اليتيمة ===")

try:
    # جمع جميع المعاملات التي تحتوي على مراجع
    orphaned_transactions = []
    all_transactions = AccountTransaction.objects.filter(
        reference_type__isnull=False,
        reference_id__isnull=False
    ).exclude(reference_type='')
    
    print(f'فحص {all_transactions.count()} معاملة...')
    
    for transaction in all_transactions:
        document_exists = False
        
        try:
            if transaction.reference_type == 'payment':
                PaymentVoucher.objects.get(id=transaction.reference_id)
                document_exists = True
                
            elif transaction.reference_type == 'purchase_invoice':
                PurchaseInvoice.objects.get(id=transaction.reference_id)
                document_exists = True
                
            elif transaction.reference_type == 'purchase_return':
                PurchaseReturn.objects.get(id=transaction.reference_id)
                document_exists = True
                
            elif transaction.reference_type == 'debit_note':
                PurchaseDebitNote.objects.get(id=transaction.reference_id)
                document_exists = True
                
            elif transaction.reference_type == 'receipt':
                PaymentReceipt.objects.get(id=transaction.reference_id)
                document_exists = True
                
            elif transaction.reference_type == 'sales_invoice':
                SalesInvoice.objects.get(id=transaction.reference_id)
                document_exists = True
                
            elif transaction.reference_type == 'sales_return':
                SalesReturn.objects.get(id=transaction.reference_id)
                document_exists = True
                
        except:
            document_exists = False
        
        if not document_exists:
            orphaned_transactions.append(transaction)
            print(f'❌ معاملة يتيمة: {transaction.transaction_number} - {transaction.reference_type} #{transaction.reference_id}')
    
    print(f'\nوُجد {len(orphaned_transactions)} معاملة يتيمة')
    
    if orphaned_transactions:
        print(f'\nحذف المعاملات اليتيمة...')
        
        # تحديث أرصدة العملاء قبل الحذف
        customers_to_update = set()
        for transaction in orphaned_transactions:
            customers_to_update.add(transaction.customer_supplier)
        
        # حذف المعاملات اليتيمة
        deleted_count = 0
        for transaction in orphaned_transactions:
            print(f'حذف: {transaction.transaction_number}')
            transaction.delete()
            deleted_count += 1
        
        print(f'✅ تم حذف {deleted_count} معاملة يتيمة')
        
        # إعادة حساب أرصدة العملاء
        print(f'\nإعادة حساب أرصدة العملاء...')
        for customer in customers_to_update:
            transactions = AccountTransaction.objects.filter(customer_supplier=customer).order_by('date', 'created_at')
            balance = 0
            for t in transactions:
                if t.direction == 'debit':
                    balance += t.amount
                else:
                    balance -= t.amount
                t.balance_after = balance
                t.save()
            
            customer.balance = balance
            customer.save()
            print(f'✅ تم تحديث رصيد {customer.name}: {balance}')
    
    # عرض النتيجة النهائية
    remaining_transactions = AccountTransaction.objects.filter(customer_supplier_id=14)
    print(f'\n=== النتيجة النهائية ===')
    print(f'المعاملات المتبقية للعميل 14: {remaining_transactions.count()}')
    
    for t in remaining_transactions:
        print(f'✅ {t.transaction_number}: {t.transaction_type}')

except Exception as e:
    print(f'خطأ: {e}')
    import traceback
    traceback.print_exc()

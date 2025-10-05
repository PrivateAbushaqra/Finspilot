"""
إصلاح جميع الفواتير النقدية بدون معاملة صندوق
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesInvoice
from cashboxes.models import CashboxTransaction
from django.db import transaction

print("=" * 70)
print("🔧 إصلاح الفواتير النقدية بدون معاملة صندوق")
print("=" * 70)

# البحث عن الفواتير النقدية مع صندوق محدد
cash_invoices = SalesInvoice.objects.filter(
    payment_type='cash',
    cashbox__isnull=False
)

print(f"\n📊 إجمالي الفواتير النقدية مع صندوق: {cash_invoices.count()}")

# البحث عن الفواتير بدون معاملة صندوق
invoices_without_transaction = []

for invoice in cash_invoices:
    has_transaction = CashboxTransaction.objects.filter(
        cashbox=invoice.cashbox,
        description__icontains=invoice.invoice_number
    ).exists()
    
    if not has_transaction:
        invoices_without_transaction.append(invoice)

count = len(invoices_without_transaction)
total_amount = sum(inv.total_amount for inv in invoices_without_transaction)

print(f"\n⚠️  فواتير بدون معاملة صندوق: {count}")
print(f"💰 المبلغ الإجمالي: {total_amount:.3f} دينار")

if count == 0:
    print("\n✅ جميع الفواتير النقدية لديها معاملات صندوق!")
    print("=" * 70)
else:
    print(f"\n📋 تفاصيل الفواتير:")
    for inv in invoices_without_transaction[:10]:
        print(f"   • {inv.invoice_number} | {inv.date} | {inv.total_amount:.3f} د | {inv.cashbox.name}")
    
    if count > 10:
        print(f"   ... و {count - 10} فاتورة أخرى")
    
    print("\n" + "=" * 70)
    confirm = input("\n⚠️  هل تريد إصلاح جميع هذه الفواتير؟ (نعم/لا): ").strip().lower()
    
    if confirm in ['نعم', 'yes', 'y']:
        print("\n🔄 جاري الإصلاح...")
        
        fixed_count = 0
        total_added = 0
        
        with transaction.atomic():
            for invoice in invoices_without_transaction:
                try:
                    # إنشاء معاملة صندوق
                    trans = CashboxTransaction.objects.create(
                        cashbox=invoice.cashbox,
                        transaction_type='deposit',
                        amount=invoice.total_amount,
                        date=invoice.date,
                        description=f'مبيعات نقدية - فاتورة رقم {invoice.invoice_number}',
                        created_by=invoice.created_by
                    )
                    
                    # تحديث رصيد الصندوق
                    invoice.cashbox.balance += invoice.total_amount
                    invoice.cashbox.save(update_fields=['balance'])
                    
                    fixed_count += 1
                    total_added += invoice.total_amount
                    
                    print(f"   ✅ {invoice.invoice_number} | +{invoice.total_amount:.3f} د → {invoice.cashbox.name}")
                    
                except Exception as e:
                    print(f"   ❌ {invoice.invoice_number} | خطأ: {str(e)}")
        
        print(f"\n" + "=" * 70)
        print(f"✅ تم الإصلاح!")
        print(f"=" * 70)
        print(f"📊 النتائج:")
        print(f"   • الفواتير المُصلحة: {fixed_count}")
        print(f"   • المبلغ المضاف: {total_added:.3f} دينار")
        print("=" * 70)
    else:
        print("\n❌ تم الإلغاء")
        print("=" * 70)

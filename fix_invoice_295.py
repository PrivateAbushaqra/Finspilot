"""
إصلاح الفاتورة SALES-000295 يدوياً
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesInvoice
from cashboxes.models import CashboxTransaction
from django.db import transaction

print("=" * 70)
print("🔧 إصلاح الفاتورة SALES-000295")
print("=" * 70)

try:
    invoice = SalesInvoice.objects.get(invoice_number='SALES-000295')
    
    print(f"\n📋 الفاتورة: {invoice.invoice_number}")
    print(f"   المبلغ: {invoice.total_amount:.3f} دينار")
    print(f"   الصندوق: {invoice.cashbox.name if invoice.cashbox else 'غير محدد'}")
    
    if not invoice.cashbox:
        print(f"\n❌ لا يمكن الإصلاح: الصندوق غير محدد!")
    elif invoice.payment_type != 'cash':
        print(f"\n❌ لا يمكن الإصلاح: الفاتورة ليست نقدية!")
    else:
        # التحقق من عدم وجود معاملة مسبقاً
        existing = CashboxTransaction.objects.filter(
            cashbox=invoice.cashbox,
            description__icontains=invoice.invoice_number
        ).exists()
        
        if existing:
            print(f"\n⚠️  المعاملة موجودة مسبقاً!")
        else:
            confirm = input(f"\n⚠️  هل تريد إنشاء معاملة صندوق وتحديث الرصيد؟ (نعم/لا): ").strip().lower()
            
            if confirm in ['نعم', 'yes', 'y']:
                with transaction.atomic():
                    # إنشاء معاملة الصندوق
                    trans = CashboxTransaction.objects.create(
                        cashbox=invoice.cashbox,
                        transaction_type='deposit',
                        amount=invoice.total_amount,
                        date=invoice.date,
                        description=f'مبيعات نقدية - فاتورة رقم {invoice.invoice_number}',
                        created_by=invoice.created_by
                    )
                    
                    # تحديث رصيد الصندوق
                    old_balance = invoice.cashbox.balance
                    invoice.cashbox.balance += invoice.total_amount
                    invoice.cashbox.save(update_fields=['balance'])
                    
                    print(f"\n✅ تم الإصلاح بنجاح!")
                    print(f"   • المعاملة: {trans.id}")
                    print(f"   • الرصيد القديم: {old_balance:.3f} دينار")
                    print(f"   • الرصيد الجديد: {invoice.cashbox.balance:.3f} دينار")
                    print(f"   • الفرق: +{invoice.total_amount:.3f} دينار")
            else:
                print(f"\n❌ تم الإلغاء")
    
    print("\n" + "=" * 70)
    
except SalesInvoice.DoesNotExist:
    print("\n❌ الفاتورة غير موجودة!")
except Exception as e:
    print(f"\n❌ خطأ: {str(e)}")
    import traceback
    traceback.print_exc()

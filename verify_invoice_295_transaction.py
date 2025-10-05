"""
التحقق من نوع معاملة الصندوق للفاتورة SALES-000295
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesInvoice
from cashboxes.models import CashboxTransaction

print("=" * 70)
print("🔍 التحقق من معاملة الصندوق - الفاتورة SALES-000295")
print("=" * 70)

try:
    invoice = SalesInvoice.objects.get(invoice_number='SALES-000295')
    
    print(f"\n📋 الفاتورة: {invoice.invoice_number}")
    print(f"   المبلغ: {invoice.total_amount:.3f} دينار")
    print(f"   الصندوق: {invoice.cashbox.name}")
    
    # البحث عن المعاملة
    transactions = CashboxTransaction.objects.filter(
        description__icontains=invoice.invoice_number
    ).order_by('-date', '-id')
    
    if transactions.exists():
        print(f"\n💰 معاملات الصندوق المرتبطة:")
        for trans in transactions:
            print(f"\n   معاملة ID: {trans.id}")
            print(f"   • الصندوق: {trans.cashbox.name}")
            print(f"   • النوع: {trans.transaction_type}")
            
            if trans.transaction_type == 'deposit':
                print(f"   • الحالة: ✅ إيداع (deposit) - صحيح")
                print(f"   • المبلغ: +{trans.amount:.3f} دينار")
            elif trans.transaction_type == 'withdrawal':
                print(f"   • الحالة: ❌ سحب (withdrawal) - خطأ!")
                print(f"   • المبلغ: -{trans.amount:.3f} دينار")
            else:
                print(f"   • الحالة: ⚠️  نوع غير معروف: {trans.transaction_type}")
                print(f"   • المبلغ: {trans.amount:.3f} دينار")
            
            print(f"   • التاريخ: {trans.date}")
            print(f"   • الوصف: {trans.description}")
    else:
        print(f"\n❌ لا توجد معاملات!")
    
    # التحقق من رصيد الصندوق
    print(f"\n📊 رصيد الصندوق الحالي:")
    print(f"   • الصندوق: {invoice.cashbox.name}")
    print(f"   • الرصيد: {invoice.cashbox.balance:.3f} دينار")
    
    # التحقق من صحة الرصيد
    print(f"\n✅ التأكيد:")
    if transactions.exists() and transactions.first().transaction_type == 'deposit':
        print(f"   ✅ المعاملة صحيحة: إيداع (deposit)")
        print(f"   ✅ المبلغ تم إضافته للصندوق (وليس خصمه)")
    else:
        print(f"   ⚠️  قد تكون هناك مشكلة!")
    
    print("\n" + "=" * 70)
    
except SalesInvoice.DoesNotExist:
    print("\n❌ الفاتورة غير موجودة!")
except Exception as e:
    print(f"\n❌ خطأ: {str(e)}")
    import traceback
    traceback.print_exc()

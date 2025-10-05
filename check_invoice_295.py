"""
فحص الفاتورة SALES-000295 والصندوق المرتبط
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesInvoice
from cashboxes.models import Cashbox, CashboxTransaction

print("=" * 70)
print("🔍 فحص الفاتورة SALES-000295")
print("=" * 70)

# البحث عن الفاتورة
try:
    invoice = SalesInvoice.objects.get(invoice_number='SALES-000295')
    
    print(f"\n📋 تفاصيل الفاتورة:")
    print(f"   • رقم الفاتورة: {invoice.invoice_number}")
    print(f"   • التاريخ: {invoice.date}")
    print(f"   • العميل: {invoice.customer.name}")
    print(f"   • طريقة الدفع: {invoice.payment_type}")
    print(f"   • المبلغ الإجمالي: {invoice.total_amount:.3f} دينار")
    
    # الصندوق
    if invoice.cashbox:
        print(f"\n💰 الصندوق المُحدد:")
        print(f"   • اسم الصندوق: {invoice.cashbox.name}")
        print(f"   • ID: {invoice.cashbox.id}")
        print(f"   • الرصيد الحالي: {invoice.cashbox.balance:.3f} دينار")
    else:
        print(f"\n⚠️  الصندوق: غير محدد!")
    
    # البحث عن معاملة الصندوق
    print(f"\n🔍 البحث عن معاملة الصندوق...")
    transactions = CashboxTransaction.objects.filter(
        description__icontains=invoice.invoice_number
    )
    
    if transactions.exists():
        print(f"   ✅ تم العثور على {transactions.count()} معاملة:")
        for i, trans in enumerate(transactions, 1):
            print(f"\n   معاملة {i}:")
            print(f"      • الصندوق: {trans.cashbox.name}")
            print(f"      • النوع: {trans.transaction_type}")
            print(f"      • المبلغ: {trans.amount:.3f} دينار")
            print(f"      • التاريخ: {trans.date}")
            print(f"      • الوصف: {trans.description}")
    else:
        print(f"   ❌ لم يتم العثور على أي معاملة للفاتورة!")
    
    # البحث عن جميع معاملات الصندوق
    if invoice.cashbox:
        print(f"\n📊 جميع معاملات الصندوق '{invoice.cashbox.name}':")
        all_trans = CashboxTransaction.objects.filter(
            cashbox=invoice.cashbox
        ).order_by('-date', '-id')[:10]
        
        if all_trans.exists():
            print(f"   (آخر 10 معاملات)")
            for trans in all_trans:
                print(f"   • {trans.date} | {trans.transaction_type} | {trans.amount:.3f} | {trans.description[:50]}")
        else:
            print(f"   ⚠️  لا توجد معاملات في هذا الصندوق!")
    
    # حساب الرصيد المتوقع
    if invoice.cashbox and invoice.payment_type == 'cash':
        print(f"\n🧮 التحليل:")
        print(f"   • الفاتورة نقدية: نعم")
        print(f"   • المبلغ: {invoice.total_amount:.3f} دينار")
        print(f"   • الصندوق محدد: نعم ({invoice.cashbox.name})")
        
        # التحقق من وجود معاملة
        trans_exists = CashboxTransaction.objects.filter(
            cashbox=invoice.cashbox,
            description__icontains=invoice.invoice_number
        ).exists()
        
        if trans_exists:
            print(f"   • معاملة الصندوق: ✅ موجودة")
        else:
            print(f"   • معاملة الصندوق: ❌ مفقودة!")
            print(f"\n🔴 المشكلة: لم يتم إنشاء معاملة صندوق للفاتورة!")
    
    print("\n" + "=" * 70)
    
except SalesInvoice.DoesNotExist:
    print("\n❌ الفاتورة SALES-000295 غير موجودة!")
except Exception as e:
    print(f"\n❌ خطأ: {str(e)}")
    import traceback
    traceback.print_exc()

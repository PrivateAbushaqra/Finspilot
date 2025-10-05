"""
فحص الفاتورة SALES-000298 وتتبع النقد
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesInvoice
from cashboxes.models import CashboxTransaction
from receipts.models import PaymentReceipt

print("=" * 70)
print("🔍 تتبع النقد - الفاتورة SALES-000298")
print("=" * 70)

try:
    invoice = SalesInvoice.objects.get(invoice_number='SALES-000298')
    
    print(f"\n📋 تفاصيل الفاتورة:")
    print(f"   • رقم الفاتورة: {invoice.invoice_number}")
    print(f"   • التاريخ: {invoice.date}")
    print(f"   • العميل: {invoice.customer.name}")
    print(f"   • طريقة الدفع: {invoice.payment_type}")
    print(f"   • المبلغ الإجمالي: {invoice.total_amount:.3f} دينار")
    
    # الصندوق
    if invoice.cashbox:
        print(f"\n💰 الصندوق المُحدد في الفاتورة:")
        print(f"   • اسم الصندوق: {invoice.cashbox.name}")
        print(f"   • ID: {invoice.cashbox.id}")
        print(f"   • الرصيد الحالي: {invoice.cashbox.balance:.3f} دينار")
    else:
        print(f"\n⚠️  الصندوق: غير محدد في الفاتورة!")
    
    # البحث في معاملات الصندوق
    print(f"\n🔍 البحث في معاملات الصناديق...")
    cashbox_trans = CashboxTransaction.objects.filter(
        description__icontains=invoice.invoice_number
    )
    
    if cashbox_trans.exists():
        print(f"   ✅ تم العثور على {cashbox_trans.count()} معاملة صندوق:")
        for trans in cashbox_trans:
            print(f"\n   📦 معاملة صندوق ID: {trans.id}")
            print(f"      • الصندوق: {trans.cashbox.name}")
            print(f"      • النوع: {trans.transaction_type}")
            print(f"      • المبلغ: {trans.amount:.3f} دينار")
            print(f"      • التاريخ: {trans.date}")
            print(f"      • الوصف: {trans.description}")
    else:
        print(f"   ❌ لا توجد معاملات صندوق!")
    
    # البحث في سندات القبض
    print(f"\n🔍 البحث في سندات القبض...")
    payment_receipts = PaymentReceipt.objects.filter(
        notes__icontains=invoice.invoice_number
    )
    
    if payment_receipts.exists():
        print(f"   ✅ تم العثور على {payment_receipts.count()} سند قبض:")
        for receipt in payment_receipts:
            print(f"\n   📄 سند قبض: {receipt.receipt_number}")
            print(f"      • المبلغ: {receipt.amount:.3f} دينار")
            print(f"      • التاريخ: {receipt.date}")
            print(f"      • الصندوق: {receipt.cashbox.name if receipt.cashbox else 'غير محدد'}")
            print(f"      • الملاحظات: {receipt.notes[:100] if receipt.notes else 'لا يوجد'}")
    else:
        print(f"   ❌ لا توجد سندات قبض!")
    
    # التحليل
    print(f"\n" + "=" * 70)
    print(f"📊 التحليل:")
    print(f"=" * 70)
    
    if invoice.payment_type == 'cash':
        print(f"✅ الفاتورة نقدية")
        
        if invoice.cashbox:
            print(f"✅ الصندوق محدد: {invoice.cashbox.name}")
        else:
            print(f"❌ الصندوق غير محدد!")
        
        if cashbox_trans.exists():
            print(f"✅ معاملة صندوق موجودة")
            trans = cashbox_trans.first()
            print(f"   📍 الموقع: صندوق '{trans.cashbox.name}'")
            print(f"   💰 المبلغ: {trans.amount:.3f} دينار")
        else:
            print(f"❌ معاملة صندوق مفقودة!")
        
        if payment_receipts.exists():
            print(f"✅ سند قبض موجود")
            receipt = payment_receipts.first()
            if receipt.cashbox:
                print(f"   📍 الموقع: صندوق '{receipt.cashbox.name}'")
                print(f"   💰 المبلغ: {receipt.amount:.3f} دينار")
        else:
            print(f"⚠️  سند قبض غير موجود")
    else:
        print(f"⚠️  الفاتورة ليست نقدية (طريقة الدفع: {invoice.payment_type})")
    
    print(f"\n" + "=" * 70)
    print(f"🎯 الخلاصة:")
    print(f"=" * 70)
    
    if invoice.payment_type == 'cash':
        if cashbox_trans.exists():
            trans = cashbox_trans.first()
            print(f"✅ النقد موجود في صندوق: {trans.cashbox.name}")
            print(f"   المبلغ: {trans.amount:.3f} دينار")
        elif invoice.cashbox:
            print(f"⚠️  الصندوق محدد ({invoice.cashbox.name}) لكن المعاملة مفقودة!")
            print(f"   يحتاج إصلاح!")
        else:
            print(f"❌ الصندوق غير محدد والمعاملة مفقودة!")
            print(f"   يحتاج إصلاح!")
    
    print(f"=" * 70)
    
except SalesInvoice.DoesNotExist:
    print("\n❌ الفاتورة SALES-000298 غير موجودة!")
except Exception as e:
    print(f"\n❌ خطأ: {str(e)}")
    import traceback
    traceback.print_exc()

"""
اختبار إنشاء فاتورة جديدة والتحقق من ترحيل النقد تلقائياً
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.contrib.auth import get_user_model
from sales.models import SalesInvoice
from customers.models import CustomerSupplier
from cashboxes.models import Cashbox, CashboxTransaction
from inventory.models import Warehouse
from datetime import date

User = get_user_model()

print("=" * 70)
print("🧪 اختبار إنشاء فاتورة نقدية جديدة")
print("=" * 70)

# الحصول على البيانات المطلوبة
user = User.objects.filter(is_active=True).first()
customer = CustomerSupplier.objects.filter(type='customer').first()
warehouse = Warehouse.objects.first()
cashbox = Cashbox.objects.filter(is_active=True, name='Cash Main').first()

if not cashbox:
    cashbox = Cashbox.objects.filter(is_active=True).first()

print(f"\n📋 البيانات:")
print(f"   • المستخدم: {user.username}")
print(f"   • العميل: {customer.name}")
print(f"   • المستودع: {warehouse.name}")
print(f"   • الصندوق المختار: {cashbox.name}")

# حفظ الرصيد قبل الإنشاء
initial_balance = cashbox.balance
print(f"\n💰 رصيد الصندوق قبل الإنشاء: {initial_balance:.3f} دينار")

# إنشاء الفاتورة
print(f"\n🔄 إنشاء فاتورة نقدية جديدة...")

invoice = SalesInvoice.objects.create(
    invoice_number='TEST-AUTO-001',
    date=date.today(),
    customer=customer,
    warehouse=warehouse,
    payment_type='cash',  # نقدي
    cashbox=cashbox,      # تحديد الصندوق
    discount_amount=0,
    notes='اختبار تلقائي - فاتورة جديدة',
    created_by=user,
    inclusive_tax=True,
    subtotal=100,
    tax_amount=16,
    total_amount=116
)

print(f"✅ تم إنشاء الفاتورة: {invoice.invoice_number}")

# الانتظار قليلاً للسيجنالات
import time
time.sleep(1)

# إعادة تحميل البيانات
invoice.refresh_from_db()
cashbox.refresh_from_db()

# التحقق من الصندوق
print(f"\n📋 تفاصيل الفاتورة بعد الحفظ:")
print(f"   • رقم الفاتورة: {invoice.invoice_number}")
print(f"   • طريقة الدفع: {invoice.payment_type}")
print(f"   • الصندوق: {invoice.cashbox.name if invoice.cashbox else '❌ غير محدد'}")
print(f"   • المبلغ: {invoice.total_amount:.3f} دينار")

# التحقق من معاملة الصندوق
print(f"\n🔍 البحث عن معاملة الصندوق...")
transaction = CashboxTransaction.objects.filter(
    description__icontains=invoice.invoice_number
).first()

if transaction:
    print(f"✅ تم إنشاء معاملة صندوق تلقائياً:")
    print(f"   • ID: {transaction.id}")
    print(f"   • الصندوق: {transaction.cashbox.name}")
    print(f"   • النوع: {transaction.transaction_type}")
    print(f"   • المبلغ: {transaction.amount:.3f} دينار")
    print(f"   • الوصف: {transaction.description}")
else:
    print(f"❌ معاملة الصندوق غير موجودة!")

# التحقق من الرصيد
print(f"\n💰 رصيد الصندوق بعد الإنشاء: {cashbox.balance:.3f} دينار")
print(f"   الفرق: {cashbox.balance - initial_balance:.3f} دينار")

# النتيجة
print(f"\n" + "=" * 70)
print(f"🎯 النتيجة:")
print(f"=" * 70)

success = True

if not invoice.cashbox:
    print(f"❌ فشل: الصندوق غير محفوظ في الفاتورة!")
    success = False
elif invoice.cashbox.id != cashbox.id:
    print(f"❌ فشل: الصندوق تم تغييره!")
    print(f"   المتوقع: {cashbox.name} (ID: {cashbox.id})")
    print(f"   الفعلي: {invoice.cashbox.name} (ID: {invoice.cashbox.id})")
    success = False
else:
    print(f"✅ نجح: الصندوق محفوظ بشكل صحيح")

if not transaction:
    print(f"❌ فشل: معاملة الصندوق لم يتم إنشاؤها!")
    success = False
else:
    print(f"✅ نجح: معاملة الصندوق تم إنشاؤها تلقائياً")

if cashbox.balance != initial_balance + invoice.total_amount:
    print(f"❌ فشل: رصيد الصندوق غير صحيح!")
    print(f"   المتوقع: {initial_balance + invoice.total_amount:.3f} دينار")
    print(f"   الفعلي: {cashbox.balance:.3f} دينار")
    success = False
else:
    print(f"✅ نجح: رصيد الصندوق تم تحديثه بشكل صحيح")

if success:
    print(f"\n🎉 🎉 🎉 الاختبار نجح بالكامل!")
    print(f"✅ الفواتير الجديدة تعمل تلقائياً بشكل صحيح")
else:
    print(f"\n⚠️  ⚠️  ⚠️  هناك مشاكل تحتاج إصلاح!")

# تنظيف
print(f"\n🗑️  تنظيف...")
invoice.delete()
cashbox.balance = initial_balance
cashbox.save()
print(f"✅ تم حذف الفاتورة التجريبية وإعادة الرصيد")
print("=" * 70)

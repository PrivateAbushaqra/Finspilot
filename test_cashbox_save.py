"""
سكريبت اختبار لإنشاء فاتورة نقدية وتحديد صندوق
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.contrib.auth import get_user_model
from sales.models import SalesInvoice
from customers.models import CustomerSupplier
from cashboxes.models import Cashbox
from inventory.models import Warehouse
from datetime import date

User = get_user_model()

# الحصول على أول مستخدم
user = User.objects.filter(is_active=True).first()

# الحصول على أول عميل
customer = CustomerSupplier.objects.filter(type='customer').first()

# الحصول على أول مستودع
warehouse = Warehouse.objects.first()

# الحصول على أي صندوق نشط
cashbox = Cashbox.objects.filter(is_active=True).first()

print("=" * 70)
print("🧪 اختبار إنشاء فاتورة نقدية مع تحديد صندوق")
print("=" * 70)

if not user:
    print("❌ لا يوجد مستخدمين في النظام")
    exit(1)

if not customer:
    print("❌ لا يوجد عملاء في النظام")
    exit(1)

if not warehouse:
    print("❌ لا يوجد مستودعات في النظام")
    exit(1)

if not cashbox:
    print("❌ لا يوجد صناديق نشطة في النظام")
    exit(1)

print(f"\n✅ المستخدم: {user.username}")
print(f"✅ العميل: {customer.name}")
print(f"✅ المستودع: {warehouse.name}")
print(f"✅ الصندوق المختار: {cashbox.name}")

# حفظ الرصيد الأولي للصندوق
initial_balance = cashbox.balance

print(f"\n📊 رصيد الصندوق قبل الإنشاء: {initial_balance:.3f} دينار")

# إنشاء الفاتورة
print("\n🔄 إنشاء فاتورة اختبار...")

invoice = SalesInvoice.objects.create(
    invoice_number='TEST-001',
    date=date.today(),
    customer=customer,
    warehouse=warehouse,
    payment_type='cash',
    cashbox=cashbox,  # ✅ تحديد الصندوق
    discount_amount=0,
    notes='فاتورة اختبار',
    created_by=user,
    inclusive_tax=True,
    subtotal=100,
    tax_amount=16,
    total_amount=116
)

print(f"\n✅ تم إنشاء الفاتورة: {invoice.invoice_number}")

# إعادة تحميل الفاتورة من قاعدة البيانات
invoice.refresh_from_db()

print(f"\n📋 تفاصيل الفاتورة بعد الحفظ:")
print(f"   • رقم الفاتورة: {invoice.invoice_number}")
print(f"   • طريقة الدفع: {invoice.payment_type}")
print(f"   • الصندوق: {invoice.cashbox.name if invoice.cashbox else '⚠️ غير محدد'}")
print(f"   • المبلغ: {invoice.total_amount:.3f} دينار")

# إعادة تحميل الصندوق من قاعدة البيانات
cashbox.refresh_from_db()

print(f"\n📊 رصيد الصندوق بعد الإنشاء: {cashbox.balance:.3f} دينار")
print(f"📊 الفرق: {cashbox.balance - initial_balance:.3f} دينار")

# التحقق من النتيجة
if invoice.cashbox and invoice.cashbox.id == cashbox.id:
    print("\n✅ ✅ ✅ النتيجة: الصندوق محفوظ بشكل صحيح!")
else:
    print(f"\n❌ ❌ ❌ النتيجة: الصندوق غير صحيح!")
    if invoice.cashbox:
        print(f"   الصندوق المتوقع: {cashbox.name} (ID: {cashbox.id})")
        print(f"   الصندوق الفعلي: {invoice.cashbox.name} (ID: {invoice.cashbox.id})")

# حذف الفاتورة الاختبارية
print("\n🗑️  حذف الفاتورة الاختبارية...")
invoice.delete()

# إعادة الرصيد كما كان
cashbox.balance = initial_balance
cashbox.save()

print("✅ تم حذف الفاتورة وإعادة الرصيد")
print("=" * 70)

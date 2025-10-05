"""
اختبار شامل لحفظ الصندوق في الفاتورة
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
from products.models import Product
from datetime import date

User = get_user_model()

print("=" * 70)
print("🔍 تشخيص شامل لمشكلة حفظ الصندوق")
print("=" * 70)

# 1. الحصول على المستخدم
user = User.objects.filter(is_active=True).first()
print(f"\n👤 المستخدم: {user.username}")
print(f"   لديه صلاحية POS: {user.has_perm('users.can_access_pos')}")

# 2. الحصول على العميل
customer = CustomerSupplier.objects.filter(type='customer').first()
print(f"\n👥 العميل: {customer.name}")

# 3. الحصول على المستودع
warehouse = Warehouse.objects.first()
print(f"\n📦 المستودع: {warehouse.name}")

# 4. عرض الصناديق المتاحة
cashboxes = Cashbox.objects.filter(is_active=True)
print(f"\n💰 الصناديق النشطة ({cashboxes.count()}):")
for cb in cashboxes:
    print(f"   - {cb.name} (ID: {cb.id}) - الرصيد: {cb.balance:.3f}")

# 5. اختيار صندوق للاختبار
test_cashbox = cashboxes.first()
print(f"\n🎯 الصندوق المختار للاختبار: {test_cashbox.name} (ID: {test_cashbox.id})")
initial_balance = test_cashbox.balance
print(f"   الرصيد قبل الاختبار: {initial_balance:.3f} دينار")

# 6. محاكاة إنشاء فاتورة كما يفعل الـ View
print("\n" + "=" * 70)
print("📝 محاكاة إنشاء فاتورة (كما في sales_invoice_create)")
print("=" * 70)

# محاكاة البيانات من POST request
payment_type = 'cash'
cashbox_id = str(test_cashbox.id)  # كما يأتي من request.POST.get('cashbox')

print(f"\n📥 البيانات المُرسلة:")
print(f"   payment_type: {payment_type}")
print(f"   cashbox_id: {cashbox_id}")

# محاكاة كود View (من sales/views.py سطر 461)
cashbox = None
if payment_type == 'cash':
    if user.has_perm('users.can_access_pos'):
        cashbox = Cashbox.objects.filter(responsible_user=user).first()
        print(f"\n🔍 المستخدم له صلاحية POS:")
        if cashbox:
            print(f"   ✅ تم العثور على صندوقه: {cashbox.name}")
        else:
            print(f"   ⚠️  لم يتم العثور على صندوق للمستخدم")
    elif cashbox_id:
        try:
            cashbox = Cashbox.objects.get(id=cashbox_id, is_active=True)
            print(f"\n🔍 المستخدم عادي:")
            print(f"   ✅ تم العثور على الصندوق المُختار: {cashbox.name}")
        except Cashbox.DoesNotExist:
            print(f"\n🔍 المستخدم عادي:")
            print(f"   ❌ الصندوق المُختار غير موجود!")

print(f"\n💾 الصندوق الذي سيُحفظ في الفاتورة: {cashbox.name if cashbox else '❌ None'}")

# 7. إنشاء الفاتورة فعلياً
print("\n" + "=" * 70)
print("🔄 إنشاء الفاتورة...")
print("=" * 70)

invoice = SalesInvoice.objects.create(
    invoice_number='TEST-DIAG-001',
    date=date.today(),
    customer=customer,
    warehouse=warehouse,
    payment_type='cash',
    cashbox=cashbox,  # هذا هو المهم!
    discount_amount=0,
    notes='فاتورة تشخيص',
    created_by=user,
    inclusive_tax=True,
    subtotal=100,
    tax_amount=16,
    total_amount=116
)

print(f"\n✅ تم إنشاء الفاتورة: {invoice.invoice_number}")

# 8. إعادة تحميل الفاتورة من DB
invoice.refresh_from_db()

print(f"\n📋 تفاصيل الفاتورة بعد الحفظ:")
print(f"   • رقم الفاتورة: {invoice.invoice_number}")
print(f"   • طريقة الدفع: {invoice.payment_type}")
print(f"   • الصندوق في DB: {invoice.cashbox.name if invoice.cashbox else '❌ NULL'}")
print(f"   • الصندوق ID: {invoice.cashbox.id if invoice.cashbox else 'NULL'}")
print(f"   • المبلغ: {invoice.total_amount:.3f} دينار")

# 9. التحقق من رصيد الصندوق
test_cashbox.refresh_from_db()
print(f"\n💰 رصيد الصندوق بعد الإنشاء: {test_cashbox.balance:.3f} دينار")
print(f"   الفرق: {test_cashbox.balance - initial_balance:.3f} دينار")

# 10. النتيجة النهائية
print("\n" + "=" * 70)
print("🎯 النتيجة:")
print("=" * 70)

if invoice.cashbox and invoice.cashbox.id == test_cashbox.id:
    print("✅ ✅ ✅ النجاح: الصندوق محفوظ بشكل صحيح!")
    print(f"   الصندوق المتوقع: {test_cashbox.name} (ID: {test_cashbox.id})")
    print(f"   الصندوق الفعلي: {invoice.cashbox.name} (ID: {invoice.cashbox.id})")
elif invoice.cashbox:
    print("⚠️  ⚠️  ⚠️  تحذير: الصندوق تم تغييره!")
    print(f"   الصندوق المتوقع: {test_cashbox.name} (ID: {test_cashbox.id})")
    print(f"   الصندوق الفعلي: {invoice.cashbox.name} (ID: {invoice.cashbox.id})")
else:
    print("❌ ❌ ❌ فشل: الصندوق NULL!")
    print(f"   الصندوق المتوقع: {test_cashbox.name} (ID: {test_cashbox.id})")
    print(f"   الصندوق الفعلي: None")

# 11. تنظيف
print("\n🗑️  تنظيف...")
invoice.delete()
test_cashbox.balance = initial_balance
test_cashbox.save()
print("✅ تم حذف الفاتورة التجريبية")

print("\n" + "=" * 70)

"""
اختبار محاكاة دقيقة للـ View - اختيار صندوق مختلف
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

print("=" * 70)
print("🧪 اختبار اختيار صندوق مختلف عن صندوق المستخدم")
print("=" * 70)

user = User.objects.filter(is_active=True).first()
customer = CustomerSupplier.objects.filter(type='customer').first()
warehouse = Warehouse.objects.first()

# اختيار صندوق ليس صندوق المستخدم
all_cashboxes = Cashbox.objects.filter(is_active=True).exclude(responsible_user=user)
if all_cashboxes.exists():
    test_cashbox = all_cashboxes.first()
else:
    # إنشاء صندوق جديد للاختبار
    test_cashbox = Cashbox.objects.create(
        name='Test Cashbox 123',
        balance=5000,
        is_active=True
    )

print(f"\n👤 المستخدم: {user.username}")
print(f"   صلاحية POS: {user.has_perm('users.can_access_pos')}")

# صندوق المستخدم
user_cashbox = Cashbox.objects.filter(responsible_user=user).first()
if user_cashbox:
    print(f"   صندوقه الخاص: {user_cashbox.name} (ID: {user_cashbox.id})")
else:
    print(f"   صندوقه الخاص: ❌ ليس له صندوق")

print(f"\n💰 الصندوق المُختار: {test_cashbox.name} (ID: {test_cashbox.id})")
initial_balance = test_cashbox.balance
print(f"   الرصيد قبل: {initial_balance:.3f} دينار")

# محاكاة الكود من View (الكود الجديد)
payment_type = 'cash'
cashbox_id = str(test_cashbox.id)

print(f"\n📥 البيانات:")
print(f"   payment_type: {payment_type}")
print(f"   cashbox_id: {cashbox_id}")

# الكود الجديد (بعد التعديل)
cashbox = None
if payment_type == 'cash':
    # 🔧 إعطاء الأولوية للصندوق المُختار
    if cashbox_id:
        try:
            cashbox = Cashbox.objects.get(id=cashbox_id, is_active=True)
            print(f"\n✅ تم اختيار الصندوق المُحدد: {cashbox.name}")
        except Cashbox.DoesNotExist:
            print(f"\n❌ الصندوق غير موجود")
    # إذا لم يتم اختيار صندوق، استخدم صندوق المستخدم
    elif user.has_perm('users.can_access_pos'):
        cashbox = Cashbox.objects.filter(responsible_user=user).first()
        if cashbox:
            print(f"\n✅ استخدام صندوق المستخدم: {cashbox.name}")
        else:
            print(f"\n⚠️  المستخدم ليس له صندوق")

print(f"\n💾 الصندوق النهائي: {cashbox.name if cashbox else '❌ None'}")

# إنشاء الفاتورة
print("\n🔄 إنشاء الفاتورة...")
invoice = SalesInvoice.objects.create(
    invoice_number='TEST-DIAG-002',
    date=date.today(),
    customer=customer,
    warehouse=warehouse,
    payment_type='cash',
    cashbox=cashbox,
    discount_amount=0,
    notes='اختبار صندوق مختلف',
    created_by=user,
    inclusive_tax=True,
    subtotal=200,
    tax_amount=32,
    total_amount=232
)

invoice.refresh_from_db()
test_cashbox.refresh_from_db()

print(f"\n📋 النتيجة:")
print(f"   الفاتورة: {invoice.invoice_number}")
print(f"   الصندوق في DB: {invoice.cashbox.name if invoice.cashbox else '❌ NULL'}")
print(f"   الصندوق ID: {invoice.cashbox.id if invoice.cashbox else 'NULL'}")
print(f"   رصيد الصندوق: {test_cashbox.balance:.3f} دينار")
print(f"   الفرق: {test_cashbox.balance - initial_balance:.3f} دينار")

if invoice.cashbox and invoice.cashbox.id == test_cashbox.id:
    print(f"\n✅ ✅ ✅ نجح: الصندوق المُختار تم حفظه بشكل صحيح!")
else:
    print(f"\n❌ ❌ ❌ فشل: الصندوق تم تغييره!")
    if invoice.cashbox:
        print(f"   المتوقع: {test_cashbox.name} (ID: {test_cashbox.id})")
        print(f"   الفعلي: {invoice.cashbox.name} (ID: {invoice.cashbox.id})")

# تنظيف
invoice.delete()
test_cashbox.balance = initial_balance
test_cashbox.save()
print(f"\n🗑️  تم التنظيف")
print("=" * 70)

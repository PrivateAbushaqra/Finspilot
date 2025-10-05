# ═══════════════════════════════════════════════════════════════════════
# كود سريع للصق في Django Shell على الخادم المباشر
# ═══════════════════════════════════════════════════════════════════════
# 
# الخطوات:
# 1. افتح Django Shell على الخادم: python manage.py shell
# 2. انسخ والصق الكود التالي بالكامل
# 3. اضغط Enter
# 
# ═══════════════════════════════════════════════════════════════════════

from django.db import transaction
from sales.models import SalesInvoice
from cashboxes.models import Cashbox
from django.contrib.auth import get_user_model

User = get_user_model()

# الحصول على الفواتير النقدية بدون صندوق
invoices = SalesInvoice.objects.filter(payment_type='cash', cashbox__isnull=True)
count = invoices.count()
total_amount = sum(invoice.total_amount for invoice in invoices)

print("=" * 70)
print(f"📊 تم العثور على {count} فاتورة نقدية بدون صندوق")
print(f"💰 المبلغ الإجمالي: {total_amount:.3f} دينار")
print("=" * 70)

if count == 0:
    print("✅ جميع الفواتير النقدية محددة بصندوق! لا يوجد شيء للإصلاح.")
else:
    # تنفيذ الإصلاح
    with transaction.atomic():
        # الحصول على أول مستخدم نشط
        default_user = User.objects.filter(is_active=True).first()
        
        if not default_user:
            print("❌ خطأ: لا يوجد مستخدمين نشطين في النظام")
        else:
            # إنشاء أو الحصول على الصندوق
            cashbox, created = Cashbox.objects.get_or_create(
                name='مبيعات نقدية سابقة',
                defaults={
                    'balance': total_amount,
                    'currency': 'JOD',
                    'responsible_user': default_user,
                    'is_active': True,
                    'description': 'صندوق تاريخي للفواتير النقدية السابقة التي لم يتم تحديد صندوق لها'
                }
            )
            
            if created:
                print(f"📦 تم إنشاء صندوق جديد: {cashbox.name}")
            else:
                print(f"📦 تم العثور على الصندوق: {cashbox.name}")
                cashbox.balance += total_amount
                cashbox.save()
            
            # تحديث الفواتير
            updated = invoices.update(cashbox=cashbox)
            
            print(f"🔄 تم تحديث {updated} فاتورة")
            print(f"💰 رصيد الصندوق النهائي: {cashbox.balance:.3f} دينار")
            print("=" * 70)
            print("✅ تم الإصلاح بنجاح!")
            print("=" * 70)

# ═══════════════════════════════════════════════════════════════════════
# انتهى الكود - يمكنك الخروج الآن بكتابة: exit()
# ═══════════════════════════════════════════════════════════════════════

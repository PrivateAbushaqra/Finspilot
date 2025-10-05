# دليل إصلاح الفواتير النقدية على الخادم المباشر

## المشكلة
توجد فواتير نقدية على الخادم المباشر بدون صندوق نقدي محدد

## الحل (بدون رفع كود على Git)

### الطريقة 1: عبر SSH (الأسهل والأسرع) ⭐

#### الخطوات:

1. **الاتصال بالخادم عبر SSH**
   ```bash
   ssh username@your-server.com
   ```

2. **الانتقال لمجلد المشروع**
   ```bash
   cd /path/to/finspilot
   ```

3. **إنشاء السكريبت مباشرة على الخادم**
   
   استخدم محرر نصوص (nano أو vim):
   ```bash
   nano fix_remote_cash_invoices.py
   ```
   
   ثم انسخ والصق محتوى الملف `fix_remote_cash_invoices.py` من جهازك المحلي

4. **تشغيل السكريبت**
   ```bash
   python fix_remote_cash_invoices.py
   ```
   
   أو إذا كنت تستخدم virtual environment:
   ```bash
   source venv/bin/activate  # أو .venv/bin/activate
   python fix_remote_cash_invoices.py
   ```

5. **التأكيد والمتابعة**
   - سيعرض السكريبت عدد الفواتير والمبلغ الإجمالي
   - اكتب "نعم" للتأكيد
   - سيتم الإصلاح تلقائياً

6. **التحقق من النتيجة**
   - افتح صفحة الفواتير على الخادم
   - تأكد من أن جميع الفواتير النقدية مرتبطة بصندوق

---

### الطريقة 2: عبر Django Shell (إذا لم يتوفر SSH)

#### الخطوات:

1. **الدخول إلى Django Shell على الخادم**
   ```bash
   python manage.py shell
   ```

2. **نسخ ولصق الكود التالي**

   ```python
   from django.db import transaction
   from sales.models import SalesInvoice
   from cashboxes.models import Cashbox
   from django.contrib.auth import get_user_model
   
   User = get_user_model()
   
   # الحصول على الفواتير النقدية بدون صندوق
   invoices = SalesInvoice.objects.filter(payment_type='cash', cashbox__isnull=True)
   count = invoices.count()
   total_amount = sum(invoice.total_amount for invoice in invoices)
   
   print(f"عدد الفواتير: {count}")
   print(f"المبلغ الإجمالي: {total_amount}")
   
   # الإصلاح
   with transaction.atomic():
       default_user = User.objects.filter(is_active=True).first()
       
       cashbox, created = Cashbox.objects.get_or_create(
           name='مبيعات نقدية سابقة',
           defaults={
               'balance': total_amount,
               'currency': 'JOD',
               'responsible_user': default_user,
               'is_active': True,
               'description': 'صندوق تاريخي للفواتير النقدية السابقة'
           }
       )
       
       if not created:
           cashbox.balance += total_amount
           cashbox.save()
       
       updated = invoices.update(cashbox=cashbox)
       
       print(f"✅ تم تحديث {updated} فاتورة")
       print(f"💰 رصيد الصندوق: {cashbox.balance}")
   ```

3. **اضغط Enter** لتنفيذ الكود

---

### الطريقة 3: عبر لوحة التحكم (Render/Heroku/etc)

إذا كنت تستخدم منصة استضافة مثل Render:

1. **افتح لوحة التحكم**
   - انتقل إلى Dashboard → Your App → Shell

2. **شغل Django Shell**
   ```bash
   python manage.py shell
   ```

3. **استخدم نفس الكود من الطريقة 2**

---

### الطريقة 4: رفع السكريبت عبر SFTP (بدون Git)

إذا كان لديك وصول SFTP:

1. **افتح برنامج SFTP** (FileZilla, WinSCP, etc)

2. **اتصل بالخادم**

3. **ارفع الملف `fix_remote_cash_invoices.py`** إلى مجلد المشروع

4. **شغل السكريبت عبر SSH** كما في الطريقة 1

---

## التحقق من نجاح الإصلاح

بعد تنفيذ الإصلاح، تحقق من:

1. ✅ **صفحة الفواتير**: جميع الفواتير النقدية يجب أن تظهر اسم الصندوق
2. ✅ **صفحة الصناديق**: يجب أن يظهر صندوق "مبيعات نقدية سابقة" برصيد صحيح
3. ✅ **التقارير**: تقارير الصناديق يجب أن تشمل المبلغ الكامل

---

## ملاحظات مهمة

⚠️ **قبل التنفيذ:**
- تأكد من أخذ نسخة احتياطية من قاعدة البيانات
- يفضل التنفيذ في وقت قليل الاستخدام

✅ **بعد التنفيذ:**
- لن يحتاج المستخدمون لأي إعدادات إضافية
- الفواتير الجديدة ستستمر في طلب تحديد الصندوق
- السكريبت آمن ويمكن تشغيله عدة مرات (idempotent)

---

## استكشاف الأخطاء

### خطأ: "No module named 'sales'"
**الحل:** تأكد من أنك في مجلد المشروع الصحيح وأن Django settings صحيح

### خطأ: "Permission denied"
**الحل:** تأكد من صلاحيات الملف:
```bash
chmod +x fix_remote_cash_invoices.py
```

### خطأ: "No active users found"
**الحل:** تأكد من وجود مستخدم نشط في النظام:
```bash
python manage.py createsuperuser
```

---

## محتوى السكريبت

السكريبت `fix_remote_cash_invoices.py` موجود في مجلد المشروع المحلي.
يمكنك فتحه ونسخ محتواه لرفعه على الخادم بأي طريقة تناسبك.

---

## الدعم

إذا واجهت أي مشكلة أثناء التنفيذ، يمكنك:
1. التحقق من سجلات الأخطاء (logs)
2. التأكد من اتصال قاعدة البيانات
3. تشغيل السكريبت في وضع Django Shell للتحكم الأفضل

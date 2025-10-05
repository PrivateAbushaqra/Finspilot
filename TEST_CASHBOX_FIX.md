# اختبار إصلاح عرض الصناديق النقدية

## المشكلة الأصلية
عند إنشاء فاتورة مبيعات نقدية من صفحة `/ar/sales/invoices/add/`:
- ❌ المستخدمين العاديين (بدون صلاحية POS) لا يرون قائمة الصناديق
- ❌ لا توجد طريقة لاختيار الصندوق الذي سيستقبل النقد

## الإصلاحات المطبقة

### 1. ملف `templates/sales/invoice_add.html`

#### التغيير الأول (السطور 343-379):
**قبل:**
```html
{% if can_change_cashbox %}
<div id="cashbox_container" style="display: none;">
    <!-- القائمة المنسدلة هنا -->
</div>
{% endif %}
```

**بعد:**
```html
<div id="cashbox_container" style="display: none;">
    {% if can_change_cashbox %}
        <!-- المستخدم العادي: قائمة منسدلة -->
        <select name="cashbox">...</select>
    {% else %}
        <!-- مستخدم POS: حقل للقراءة فقط -->
        <input type="text" readonly value="{{ default_cashbox.name }}">
        <input type="hidden" name="cashbox" value="{{ default_cashbox.id }}">
    {% endif %}
</div>
```

#### التغيير الثاني (السطر 684):
**حذف:** الكود القديم الذي يخفي الحقل للمستخدمين العاديين
```javascript
{% if not can_change_cashbox %}
document.addEventListener('DOMContentLoaded', function() {
    cashboxContainer.style.display = 'none'; // ← حذف هذا
});
{% endif %}
```

#### التغيير الثالث (السطور 2126-2154):
**تحسين:** JavaScript لإظهار الحقل للجميع عند اختيار "نقداً"
```javascript
if (paymentType === 'cash') {
    cashboxContainer.style.display = 'block'; // ← للجميع الآن
    {% if can_change_cashbox %}
        cashboxSelect.required = true; // مطلوب للمستخدم العادي
    {% endif %}
}
```

#### التغيير الرابع (السطور 2158-2175):
**إضافة:** عرض الحقل تلقائياً عند تحميل الصفحة إذا كان payment_type='cash'
```javascript
document.addEventListener('DOMContentLoaded', function() {
    if (paymentTypeSelect.value === 'cash') {
        cashboxContainer.style.display = 'block';
    }
});
```

### 2. ملف `sales/views.py`

#### التغيير (السطور 295-308):
**تحسين:** تحديد الصندوق الافتراضي حسب نوع المستخدم

**قبل:**
```python
context['default_cashbox'] = user.default_cashbox
```

**بعد:**
```python
if user.has_perm('users.can_access_pos'):
    # مستخدم POS: الصندوق المرتبط به (responsible_user)
    pos_cashbox = Cashbox.objects.filter(responsible_user=user, is_active=True).first()
    context['default_cashbox'] = pos_cashbox or user.default_cashbox
else:
    # مستخدم عادي: الصندوق الافتراضي
    context['default_cashbox'] = user.default_cashbox
```

## السيناريوهات بعد الإصلاح

### سيناريو 1: مستخدم عادي (بدون POS)
1. ✅ يدخل صفحة إنشاء فاتورة
2. ✅ يختار "نقداً" من نوع الدفع
3. ✅ **تظهر قائمة منسدلة** بجميع الصناديق النشطة
4. ✅ يختار الصندوق المناسب
5. ✅ يمكنه تعيينه كصندوق افتراضي (checkbox)

### سيناريو 2: مستخدم POS (كاشير)
1. ✅ يدخل صفحة إنشاء فاتورة
2. ✅ يختار "نقداً" من نوع الدفع
3. ✅ **يظهر حقل للقراءة فقط** يعرض اسم صندوقه المعين
4. ✅ لا يمكن التعديل (readonly)
5. ✅ القيمة ترسل تلقائياً مع الفورم (hidden input)

### سيناريو 3: مستخدم POS بدون صندوق معين
1. ✅ يدخل صفحة إنشاء فاتورة
2. ✅ يختار "نقداً"
3. ⚠️ **تظهر رسالة تحذير:**
   "No cash box assigned to you. Please contact the administrator."

## كيفية الاختبار

### 1. اختبار مستخدم عادي
```bash
# 1. تسجيل دخول بمستخدم عادي (ليس لديه صلاحية can_access_pos)
# 2. الذهاب إلى: http://127.0.0.1:8000/ar/sales/invoices/add/
# 3. اختيار "نقداً" من نوع الدفع
# 4. التحقق من ظهور قائمة الصناديق
```

### 2. اختبار مستخدم POS
```bash
# 1. تسجيل دخول بمستخدم POS
# 2. الذهاب إلى: http://127.0.0.1:8000/ar/sales/invoices/add/
# 3. اختيار "نقداً" من نوع الدفع
# 4. التحقق من ظهور الصندوق المعين فقط (readonly)
```

### 3. إنشاء بيانات اختبار
```python
# في Django shell:
python manage.py shell

from cashboxes.models import Cashbox
from django.contrib.auth import get_user_model
User = get_user_model()

# إنشاء صناديق
cashbox1 = Cashbox.objects.create(
    name='صندوق الفرع الرئيسي',
    balance=5000.000,
    currency='JOD',
    is_active=True
)

cashbox2 = Cashbox.objects.create(
    name='صندوق نقطة البيع 1',
    balance=3000.000,
    currency='JOD',
    is_active=True
)

# ربط صندوق بمستخدم POS
user_pos = User.objects.get(username='cashier1')
cashbox2.responsible_user = user_pos
cashbox2.save()
```

## النتيجة المتوقعة

### قبل الإصلاح:
```
❌ مستخدم عادي → لا يرى قائمة الصناديق
❌ لا يمكن اختيار الصندوق المستقبل للنقد
❌ الفاتورة تُنشأ بدون ربط بصندوق
```

### بعد الإصلاح:
```
✅ مستخدم عادي → يرى قائمة منسدلة بجميع الصناديق
✅ مستخدم POS → يرى صندوقه المعين فقط (readonly)
✅ الفاتورة تُرتبط بالصندوق الصحيح
✅ رصيد الصندوق يتحدث تلقائياً
✅ القيد المحاسبي يُسجل بشكل صحيح
```

## الملفات المعدلة
- ✅ `templates/sales/invoice_add.html` (4 تعديلات)
- ✅ `sales/views.py` (1 تعديل)

## ملاحظات مهمة
⚠️ **لم يتم رفع التعديلات على الريموت** (حسب طلب المستخدم)

## التعديلات الإضافية المطلوبة (اختياري)
1. إضافة ترجمة للرسائل الجديدة في ملفات الترجمة
2. إضافة validation على Backend لضمان اختيار صندوق عند payment_type='cash'
3. إضافة تقرير يعرض حركات كل صندوق

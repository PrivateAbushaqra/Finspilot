# 📌 ملخص سريع: نقاط التقاطع الرئيسية

## 🎯 الإجابات على أسئلتك:

### ❓ السؤال 1: أين يتم إنشاء صندوق نقدي عند فتح POS Shift؟

**الإجابة**: ✅ **لا يتم إنشاء صندوق عند فتح الشفت**

- **الملف**: [sales/views.py](sales/views.py) **السطور 2830-2869**
- **الدالة**: `open_pos_shift(request)`
- **الكود** (السطر 2856):
  ```python
  new_shift = POSShift.objects.create(
      user=pos_user,
      opened_by=request.user,
      status='open',
  )
  ```
- **لا يوجد signal**: ❌ لا يوجد `@receiver(post_save, sender=POSShift)` في `sales/signals.py`

---

### ❓ السؤال 2: أين في شاشة pos_shifts_view يتم عرض الصناديق؟

**الإجابة**:

**View** - [sales/views.py](sales/views.py) **السطور 2778-2820**:
- السطر 2795: استدعاء `get_or_create_user_pos_cashboxes(shift.user)`
- السطور 2808-2809: فلترة الصناديق التي تنتهي بـ ` - Cash` أو ` - Card`
- السطر 2815: تمرير `shift_rows` للقالب

**القالب** - [templates/sales/pos_shifts.html](templates/sales/pos_shifts.html) **السطور 59-64**:
```html
<td>
    {% if row.cashboxes %}
        <ul class="mb-0 ps-3">
            {% for cashbox in row.cashboxes %}
                <li>{{ cashbox.name }} - {{ cashbox.balance|floatformat:3 }} {{ cashbox.currency }}</li>
            {% endfor %}
        </ul>
```

---

### ❓ السؤال 3: متى يتم استدعاء get_or_create_user_pos_cashboxes؟

**الإجابة**: يُستدعى في 3 أماكن:

| # | المكان | الملف | السطر | الغرض |
|---|--------|--------|---------|-------|
| 1 | `pos_shifts_view` | [sales/views.py](sales/views.py) | 2795 | عند عرض الشفتات - يضمن وجود الصناديق |
| 2 | `pos()` (عرض POS) | [sales/views.py](sales/views.py) | 2728 | عند الدخول لـ POS - يحصل على الصناديق |
| 3 | `close_pos_shift` | [sales/views.py](sales/views.py) | 2989 | عند إغلاق الشفت - يحدث الصناديق |

---

## 🔴 المشكلة الحقيقية

### عدم توحيد أسماء الصناديق:

**الصناديق المُنشأة عند إنشاء مستخدم POS**:
```
Cash - ahmed
Card - ahmed
```
✅ **المصدر**: [users/signals.py](users/signals.py) السطر 43 + دالة `_build_pos_cashbox_names`

**الصناديق المبحوث عنها في `get_or_create_user_pos_cashboxes`**:
```
Cash POS Box      (اسم عام)
Card POS Box      (اسم عام)
```
❌ **المصدر**: [sales/views.py](sales/views.py) السطور 51-52

**النتيجة**: 
- ⚠️ قد تُنشأ صناديق **إضافية** في كل مرة يتم فيها فتح `pos_shifts_view`
- ⚠️ قد لا تُربط الصناديق بشكل صحيح بـ transactions

---

## 📍 ملفات المشكلة والأسطر

| ملف | السطر | المشكلة |
|-----|--------|---------|
| [sales/views.py](sales/views.py) | 51-52 | `POS_CASHBOX_NAME = 'Cash POS Box'` ❌ |
| [sales/views.py](sales/views.py) | 62-86 | دالة تبحث عن أسماء خاطئة |
| [sales/views.py](sales/views.py) | 2795 | استدعاء الدالة في كل مرة |
| [users/signals.py](users/signals.py) | 43 | `_build_pos_cashbox_names(instance.username)` ✅ |
| [sales/signals.py](sales/signals.py) | - | لا يوجد signal على POSShift ❌ |

---

## ✅ الصناديق الموجودة بالفعل

**عند إنشاء مستخدم POS (ahmed)**:
- ✅ تُنشأ تلقائياً عبر [users/signals.py](users/signals.py) **السطور 35-146**
- ✅ الاسم: `Cash - ahmed`
- ✅ الاسم: `Card - ahmed`

**عند فتح الشفت**:
- ❌ لا تُنشأ صناديق إضافية (صحيح)
- ✅ الصناديق الموجودة تُعرض (صحيح)

---

## 🔧 الإصلاح المقترح

**توحيد أسماء الصناديق**:
```python
# بدلاً من:
POS_CASHBOX_NAME = 'Cash POS Box'

# استخدام:
POS_CASHBOX_NAME = '{username} - Cash'  # أو إزالة هذا الثابت تماماً
```

أو تعديل `get_or_create_user_pos_cashboxes` للبحث عن الأسماء الصحيحة:
```python
# السطر 62 - تعديل البحث:
cashbox = Cashbox.objects.filter(
    responsible_user=user,
    is_active=True,
    name__iexact=f"{user.username} - Cash"  # ✅ نفس تنسيق users/signals.py
).first()
```

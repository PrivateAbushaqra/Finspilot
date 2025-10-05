# دليل إصلاح مشكلة الصندوق على الخادم المباشر

## المشكلة
عند إنشاء فاتورة مبيعات نقدية واختيار صندوق، لا يتم حفظ الصندوق المُختار.

## السبب
السيجنال `create_cashbox_transaction_for_sales` في ملف `sales/signals.py` كان يتجاهل الصندوق المُختار ويستبدله بصندوق آخر.

## الحل
تعديل السطر 11 في ملف `sales/signals.py`:

### قبل التعديل:
```python
# تحديد الصندوق المناسب
cashbox = None

# إذا كان المستخدم يستطيع الوصول لنقطة البيع، استخدم صندوقه الخاص
if instance.created_by.has_perm('users.can_access_pos'):
    ...
```

### بعد التعديل:
```python
# 🔧 استخدام الصندوق المحدد في الفاتورة أولاً (إن وُجد)
cashbox = instance.cashbox

# إذا لم يكن هناك صندوق محدد، حدد واحد حسب المستخدم
if not cashbox:
    # إذا كان المستخدم يستطيع الوصول لنقطة البيع، استخدم صندوقه الخاص
    if instance.created_by.has_perm('users.can_access_pos'):
        ...
```

---

## خطوات التطبيق على الخادم

### الطريقة 1: عبر SSH (الأسرع)

```bash
# 1. اتصل بالخادم
ssh username@your-server.com

# 2. انتقل لمجلد المشروع
cd /path/to/finspilot

# 3. افتح ملف signals.py
nano sales/signals.py

# 4. ابحث عن السطر 11 (في دالة create_cashbox_transaction_for_sales)
# اضغط Ctrl+W ثم اكتب: تحديد الصندوق المناسب

# 5. استبدل الأسطر 11-14 بالكود الجديد:
#    قبل:
#        # تحديد الصندوق المناسب
#        cashbox = None
#        
#        # إذا كان المستخدم يستطيع الوصول لنقطة البيع، استخدم صندوقه الخاص
#        if instance.created_by.has_perm('users.can_access_pos'):
#
#    بعد:
#        # 🔧 استخدام الصندوق المحدد في الفاتورة أولاً (إن وُجد)
#        cashbox = instance.cashbox
#        
#        # إذا لم يكن هناك صندوق محدد، حدد واحد حسب المستخدم
#        if not cashbox:
#            # إذا كان المستخدم يستطيع الوصول لنقطة البيع، استخدم صندوقه الخاص
#            if instance.created_by.has_perm('users.can_access_pos'):

# 6. احفظ الملف
#    اضغط Ctrl+O ثم Enter ثم Ctrl+X

# 7. أعد تشغيل الخادم
sudo systemctl restart gunicorn
# أو
sudo systemctl restart finspilot
```

---

### الطريقة 2: عبر Django Shell (إذا لم يتوفر محرر نصوص)

هذه الطريقة تعدل الملف برمجياً:

```bash
# 1. افتح Django Shell
python manage.py shell

# 2. انسخ والصق الكود التالي:
```

```python
# قراءة الملف
file_path = 'sales/signals.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# البحث والاستبدال
old_code = '''        # التحقق من أن الفاتورة جديدة ونقدية
        if created and instance.payment_type == 'cash' and instance.total_amount > 0:
            # تحديد الصندوق المناسب
            cashbox = None
            
            # إذا كان المستخدم يستطيع الوصول لنقطة البيع، استخدم صندوقه الخاص
            if instance.created_by.has_perm('users.can_access_pos'):'''

new_code = '''        # التحقق من أن الفاتورة جديدة ونقدية
        if created and instance.payment_type == 'cash' and instance.total_amount > 0:
            # 🔧 استخدام الصندوق المحدد في الفاتورة أولاً (إن وُجد)
            cashbox = instance.cashbox
            
            # إذا لم يكن هناك صندوق محدد، حدد واحد حسب المستخدم
            if not cashbox:
                # إذا كان المستخدم يستطيع الوصول لنقطة البيع، استخدم صندوقه الخاص
                if instance.created_by.has_perm('users.can_access_pos'):'''

# تنفيذ الاستبدال
if old_code in content:
    content = content.replace(old_code, new_code)
    
    # حفظ الملف
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ تم تعديل الملف بنجاح!")
else:
    print("❌ لم يتم العثور على الكود القديم")

# الخروج
exit()
```

```bash
# 3. أعد تشغيل الخادم
sudo systemctl restart gunicorn
```

---

### الطريقة 3: عبر SFTP (بدون SSH)

1. **حمّل ملف `sales/signals.py`** من الخادم إلى جهازك
2. **افتحه في محرر نصوص** (VS Code, Notepad++, etc)
3. **ابحث عن السطر 11** وعدّله كما في الأعلى
4. **ارفع الملف المُعدّل** إلى الخادم (استبدل القديم)
5. **أعد تشغيل الخادم** عبر لوحة التحكم

---

## التحقق من نجاح الإصلاح

بعد تطبيق الإصلاح:

1. ✅ افتح صفحة إنشاء فاتورة مبيعات
2. ✅ اختر "نقداً" كطريقة الدفع
3. ✅ اختر صندوق نقدي محدد
4. ✅ أنشئ الفاتورة
5. ✅ افتح صفحة قائمة الفواتير
6. ✅ تأكد من ظهور اسم الصندوق المُختار (وليس "⚠️ غير محدد")
7. ✅ افتح صفحة تقارير الصناديق
8. ✅ تأكد من أن المبلغ أُضيف للصندوق الصحيح

---

## ملاحظات مهمة

⚠️ **قبل التطبيق:**
- احفظ نسخة احتياطية من ملف `sales/signals.py`
- يفضل التطبيق في وقت قليل الاستخدام

✅ **بعد التطبيق:**
- الفواتير الجديدة ستُحفظ بالصندوق المُختار
- الفواتير القديمة يمكن إصلاحها بسكريبت `fix_remote_cash_invoices.py`
- لا حاجة لأي إجراء من المستخدمين

---

## الفرق الدقيق

الفرق الوحيد هو إضافة **3 أسطر**:

```python
# 🔧 استخدام الصندوق المحدد في الفاتورة أولاً (إن وُجد)
cashbox = instance.cashbox

# إذا لم يكن هناك صندوق محدد، حدد واحد حسب المستخدم
if not cashbox:
```

هذا يجعل السيجنال يحترم الصندوق المُختار من المستخدم بدلاً من تجاهله.

---

## الملفات المُعدّلة

- ✅ `sales/signals.py` (السطور 11-14)

لا توجد ملفات أخرى تحتاج تعديل.

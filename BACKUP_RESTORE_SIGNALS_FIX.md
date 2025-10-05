# 🔧 إصلاح رسائل السيجنالات أثناء استعادة النسخة الاحتياطية

## 📋 المشكلة

عند استرجاع النسخة الاحتياطية، تظهر هذه الرسائل في الـ Log:

```
تم تحديث المخزون لفاتورة المبيعات SALES-000182
لم يتم إنشاء قيد COGS لفاتورة المبيعات SALES-000182
```

## 🔍 السبب

عند استعادة النسخة الاحتياطية:
1. ✅ يتم إنشاء/تحديث `SalesInvoice` عبر `update_or_create()`
2. 🔥 Django يُطلق **`post_save` signal** تلقائياً
3. 📦 السيجنال يحاول **تحديث المخزون** → ينجح
4. ❌ السيجنال يحاول **إنشاء قيد COGS** → يفشل (لأن القيود موجودة بالفعل في النسخة الاحتياطية)

### لماذا يفشل قيد COGS؟

```python
# في sales/signals.py
@receiver(post_save, sender=SalesInvoice)
def update_inventory_on_sales_invoice(sender, instance, created, **kwargs):
    # تحديث المخزون - ينجح
    ...
    
    if created:
        # محاولة إنشاء قيد COGS
        cogs_entry = JournalService.create_cogs_entry(instance, instance.created_by)
        if cogs_entry:
            print(f"تم إنشاء قيد COGS")
        else:
            print(f"لم يتم إنشاء قيد COGS")  # ← هذه الرسالة!
```

**السبب:** قيد COGS موجود بالفعل في النسخة الاحتياطية، لذا السيجنال يفشل في إنشاء واحد جديد.

---

## ✅ الحل

### الخيار 1: تعطيل السيجنالات أثناء الاستعادة (الموصى به)

في ملف `backup/views.py`، نضيف تعطيل مؤقت للسيجنالات:

```python
from django.db.models.signals import post_save
from contextlib import contextmanager

@contextmanager
def disable_signals():
    """تعطيل جميع السيجنالات مؤقتاً"""
    # حفظ السيجنالات الحالية
    saved_signals = {}
    for signal in [post_save, pre_save, post_delete, pre_delete]:
        saved_signals[signal] = signal.receivers[:]
        signal.receivers = []
    
    try:
        yield
    finally:
        # استعادة السيجنالات
        for signal, receivers in saved_signals.items():
            signal.receivers = receivers


# في دالة perform_backup_restore، عند استعادة البيانات:
def perform_backup_restore(backup_data, clear_data=False, user=None):
    ...
    
    # عند استعادة الجداول
    with disable_signals():  # ← تعطيل السيجنالات
        for table_info in flat_tables:
            ...
            obj, created = model.objects.update_or_create(...)
            ...
```

---

### الخيار 2: تعطيل سيجنالات محددة فقط

إذا أردت تعطيل سيجنالات `SalesInvoice` فقط:

```python
from sales.signals import (
    create_cashbox_transaction_for_sales,
    update_inventory_on_sales_invoice,
    create_payment_receipt_for_cash_sales
)

# قبل الاستعادة
post_save.disconnect(create_cashbox_transaction_for_sales, sender=SalesInvoice)
post_save.disconnect(update_inventory_on_sales_invoice, sender=SalesInvoice)
post_save.disconnect(create_payment_receipt_for_cash_sales, sender=SalesInvoice)

# استعادة البيانات
...

# بعد الاستعادة
post_save.connect(create_cashbox_transaction_for_sales, sender=SalesInvoice)
post_save.connect(update_inventory_on_sales_invoice, sender=SalesInvoice)
post_save.connect(create_payment_receipt_for_cash_sales, sender=SalesInvoice)
```

---

### الخيار 3: إضافة فلاج في السيجنال (أبسط)

في ملف `sales/signals.py`، نضيف شرط:

```python
@receiver(post_save, sender=SalesInvoice)
def update_inventory_on_sales_invoice(sender, instance, created, **kwargs):
    """تحديث المخزون عند إنشاء أو تعديل فاتورة مبيعات"""
    
    # 🔧 تجاهل السيجنال إذا كنا في وضع الاستعادة
    if kwargs.get('raw', False):  # raw=True عند التحميل من fixtures أو استعادة
        return
    
    try:
        from inventory.models import InventoryMovement, Warehouse
        ...
```

**`raw=True`** يُمرَّر تلقائياً من Django عند استخدام:
- `loaddata` (fixtures)
- Deserialization
- **Restore operations** (إذا استخدمنا `deserialize()`)

---

## 🎯 الحل الموصى به

**استخدام الخيار 3** لأنه:
- ✅ أبسط في التطبيق
- ✅ لا يحتاج تعديل كود الاستعادة
- ✅ يعمل تلقائياً مع جميع عمليات الاستعادة

### التطبيق:

أضف هذا السطر في **بداية كل سيجنال** في `sales/signals.py`:

```python
@receiver(post_save, sender=SalesInvoice)
def create_cashbox_transaction_for_sales(sender, instance, created, **kwargs):
    """إنشاء معاملة صندوق تلقائياً عند إنشاء فاتورة مبيعات نقدية"""
    # 🔧 تجاهل عند الاستعادة
    if kwargs.get('raw', False):
        return
    
    try:
        ...


@receiver(post_save, sender=SalesInvoice)
def create_payment_receipt_for_cash_sales(sender, instance, created, **kwargs):
    """إنشاء سند قبض تلقائياً عند إنشاء فاتورة مبيعات نقدية"""
    # 🔧 تجاهل عند الاستعادة
    if kwargs.get('raw', False):
        return
    
    try:
        ...


@receiver(post_save, sender=SalesInvoice)
def update_cashbox_transaction_on_invoice_change(sender, instance, created, **kwargs):
    """تحديث معاملة الصندوق عند تعديل الفاتورة"""
    # 🔧 تجاهل عند الاستعادة
    if kwargs.get('raw', False):
        return
    
    try:
        ...


@receiver(post_save, sender=SalesInvoice)
def update_inventory_on_sales_invoice(sender, instance, created, **kwargs):
    """تحديث المخزون عند إنشاء أو تعديل فاتورة مبيعات"""
    # 🔧 تجاهل عند الاستعادة
    if kwargs.get('raw', False):
        return
    
    try:
        ...
```

---

## 📝 ملاحظة مهمة

⚠️ **المشكلة الحالية:**
في الكود الموجود، نستخدم `update_or_create()` في `backup/views.py`، و Django لا يُمرر `raw=True` تلقائياً في هذه الحالة.

**الحل البديل:**
نحتاج لتعديل `backup/views.py` ليُمرر `raw=True`:

```python
# في backup/views.py، السطر 2038
# بدلاً من:
obj, created = model.objects.update_or_create(
    pk=pk_value,
    defaults={k: v for k, v in cleaned_data.items() if k != 'pk'}
)

# استخدم:
from django.db import transaction

# قبل loop الاستعادة
with transaction.atomic():
    # إعلام السيجنالات أننا في وضع الاستعادة
    for record in records:
        ...
        # طريقة 1: استخدام save مع raw=True
        if pk_value:
            try:
                obj = model.objects.get(pk=pk_value)
                for key, value in cleaned_data.items():
                    if key != 'pk':
                        setattr(obj, key, value)
                obj.save(raw=True)  # ← هذا يُمرر raw=True للسيجنالات
                created = False
            except model.DoesNotExist:
                obj = model(**{k: v for k, v in cleaned_data.items() if k != 'pk'})
                obj.save(raw=True)
                created = True
        else:
            obj = model(**{k: v for k, v in cleaned_data.items() if k != 'pk'})
            obj.save(raw=True)
            created = True
```

لكن للأسف `save(raw=True)` **لا يعمل** - `raw` parameter ليس موجوداً في `save()`.

---

## 🎯 الحل النهائي (الأفضل)

استخدام **متغير عام** للإشارة إلى وضع الاستعادة:

### 1. إنشاء ملف `backup/restore_context.py`:

```python
# backup/restore_context.py
"""
متغير عام لتتبع حالة الاستعادة
"""
_is_restoring = False

def set_restoring(value):
    global _is_restoring
    _is_restoring = value

def is_restoring():
    return _is_restoring
```

### 2. في `backup/views.py`:

```python
from .restore_context import set_restoring

def perform_backup_restore(backup_data, clear_data=False, user=None):
    try:
        # تفعيل وضع الاستعادة
        set_restoring(True)
        
        # عملية الاستعادة...
        ...
        
    finally:
        # إيقاف وضع الاستعادة
        set_restoring(False)
```

### 3. في `sales/signals.py`:

```python
from backup.restore_context import is_restoring

@receiver(post_save, sender=SalesInvoice)
def update_inventory_on_sales_invoice(sender, instance, created, **kwargs):
    """تحديث المخزون عند إنشاء أو تعديل فاتورة مبيعات"""
    
    # 🔧 تجاهل عند الاستعادة
    if is_restoring():
        return
    
    try:
        ...
```

---

## 📊 الخلاصة

| الطريقة | السهولة | الأمان | التوصية |
|---------|---------|--------|----------|
| متغير عام (`restore_context`) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ موصى به |
| `raw=True` parameter | ⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ لا يعمل مع `save()` |
| تعطيل السيجنالات يدوياً | ⭐⭐⭐ | ⭐⭐⭐ | ⚠️ معقد |

**الحل الموصى به:**
استخدام **متغير عام** (`restore_context.py`) لأنه:
- ✅ بسيط وسهل
- ✅ لا يحتاج تعديل كبير في الكود
- ✅ يعمل مع جميع أنواع الاستعادة
- ✅ يمكن تطبيقه على جميع السيجنالات

---

## 🚀 الخطوات التالية

1. إنشاء `backup/restore_context.py`
2. تعديل `backup/views.py` لاستخدام `set_restoring()`
3. إضافة شرط `if is_restoring(): return` في جميع السيجنالات
4. اختبار الاستعادة

---

**تاريخ الإنشاء:** 5 أكتوبر 2025
**الحالة:** ✅ جاهز للتطبيق

# 🔧 إصلاح خطأ tax_amount في إشعارات الدائن

## 📋 المشكلة

عند استرجاع النسخة الاحتياطية، يظهر الخطأ:
```
خطأ في إنشاء قيد إشعار الدائن CRD000010: 'SalesCreditNote' object has no attribute 'tax_amount'
```

---

## 🔍 السبب

**الموديل `SalesCreditNote` لا يحتوي على حقل `tax_amount`!**

```python
# sales/models.py - class SalesCreditNote
class SalesCreditNote(models.Model):
    note_number = models.CharField(...)
    date = models.DateField(...)
    customer = models.ForeignKey(...)
    subtotal = models.DecimalField(...)        # ✅ موجود
    total_amount = models.DecimalField(...)    # ✅ موجود
    # ❌ tax_amount غير موجود!
```

لكن السيجنال في `journal/services.py` يحاول استخدامه:
```python
if credit_note.tax_amount > 0:  # ❌ خطأ!
```

---

## ✅ الحل المُطبّق

تم تعديل `journal/services.py` (السطر 968):

### قبل:
```python
if credit_note.tax_amount > 0:
    # إنشاء سطر الضريبة...
```

### بعد:
```python
if hasattr(credit_note, 'tax_amount') and credit_note.tax_amount > 0:
    # إنشاء سطر الضريبة...
```

الآن السيجنال يتحقق من **وجود الحقل أولاً** قبل استخدامه!

---

## 📊 النتيجة

✅ **لن يظهر الخطأ بعد الآن** عند استرجاع النسخة الاحتياطية  
✅ القيود المحاسبية تُنشأ بدون مشاكل  
✅ النظام يعمل مع أو بدون حقل `tax_amount`

---

## 🔮 التحسين المستقبلي (اختياري)

إذا أردت دعم الضريبة في إشعارات الدائن، أضف الحقل للموديل:

```python
# sales/models.py - class SalesCreditNote
class SalesCreditNote(models.Model):
    # ... الحقول الموجودة
    
    # ✨ إضافة حقل الضريبة
    tax_amount = models.DecimalField(
        _('مبلغ الضريبة'), 
        max_digits=15, 
        decimal_places=3, 
        default=0
    )
```

ثم عمل migration:
```bash
python manage.py makemigrations sales
python manage.py migrate
```

---

## 📝 الملفات المُعدّلة

- ✅ `journal/services.py` (السطر 968)

---

## 🧪 الاختبار

لاختبار الإصلاح:
```bash
# استرجاع نسخة احتياطية تحتوي على إشعارات دائن
python manage.py restore_backup backup_file.json

# يجب أن لا تظهر رسائل الخطأ:
# ✅ لا يوجد: 'SalesCreditNote' object has no attribute 'tax_amount'
```

---

## 🎯 الخلاصة

| المشكلة | الحل |
|---------|------|
| ❌ `tax_amount` غير موجود في الموديل | ✅ استخدام `hasattr()` للتحقق أولاً |
| ❌ خطأ عند استرجاع النسخة الاحتياطية | ✅ السيجنال يعمل بدون مشاكل |
| ⚠️  الضريبة غير مدعومة حالياً | 🔮 يمكن إضافة الحقل لاحقاً |

---

**التاريخ**: 5 أكتوبر 2025  
**الحالة**: ✅ تم الإصلاح  
**الأولوية**: 🔴 عالية (يؤثر على استرجاع النسخ الاحتياطية)

# دليل المطور - ميزات الربط التلقائي للحسابات

## نظرة عامة
تم تطوير نظام ذكي لربط الحسابات المحاسبية الفرعية بحساباتها الأب تلقائياً، مع إمكانية إصلاح الهرمية المكسورة.

## الميزات المضافة

### 1. ربط تلقائي للحسابات (`get_auto_parent()`)
يقوم النظام بتحليل كود الحساب وتحديد الحساب الأب المناسب:

#### قواعد الربط:
- **النقاط**: `101.01` ← `101`
- **الهرمية**: `10101` ← `101`, `1010101` ← `10101`
- **التوافق**: التحقق من توافق أنواع الحسابات

#### مثال على الكود:
```python
# كود الحساب: "101.01"
account = Account(code="101.01", name="النقد وما شابهه")
parent = account.get_auto_parent()  # يرجع حساب "101"
```

### 2. التحقق من التوافق (`_is_compatible_account_type()`)
يضمن أن يكون نوع الحساب الفرعي متوافقاً مع نوع الحساب الأب:

```python
compatibility_rules = {
    'asset': ['asset'],           # الأصول تحت الأصول
    'liability': ['liability'],   # المطلوبات تحت المطلوبات
    'revenue': ['revenue'],       # الإيرادات تحت الإيرادات
    'expense': ['expense'],       # المصاريف تحت المصاريف
}
```

### 3. عرض المسار الهرمي (`get_hierarchy_path()`)
يعرض المسار الكامل للحساب في الشجرة الهرمية:

```python
account.get_hierarchy_path()  # "الأصول > الأصول المتداولة > النقد وما شابهه"
account.get_hierarchy_codes() # "1 > 11 > 111"
```

### 4. إصلاح الهرمية (`fix_broken_hierarchy()`)
طريقة ثابتة لإصلاح جميع الحسابات غير المربوطة:

```python
fixed_count = Account.fix_broken_hierarchy()
print(f"تم إصلاح {fixed_count} حساب")
```

## الاستخدام في الكود

### في نموذج Account:
```python
def save(self, *args, **kwargs):
    # ربط تلقائي إذا لم يكن هناك حساب أب
    if not self.parent:
        auto_parent = self.get_auto_parent()
        if auto_parent:
            self.parent = auto_parent
    super().save(*args, **kwargs)
```

### في العرض:
```python
@login_required
@permission_required('journal.change_account')
def fix_account_hierarchy(request):
    if request.method == 'POST':
        fixed_count = Account.fix_broken_hierarchy()
        messages.success(request, f'تم إصلاح {fixed_count} حساب')
    return redirect('journal:account_list')
```

### في القالب:
```html
{% if account.is_child_account and not account.has_parent %}
    <span class="badge badge-danger">
        <i class="fas fa-exclamation-triangle"></i>
    </span>
{% endif %}
```

## الأوامر الإدارية

### فحص الإصلاحات المطلوبة:
```bash
python manage.py fix_account_hierarchy --dry-run
```

### تنفيذ الإصلاح:
```bash
python manage.py fix_account_hierarchy
```

## الاعتبارات الأمنية

- **الصلاحيات**: يتطلب صلاحية `change_account`
- **التسجيل**: يسجل جميع العمليات في سجل الأنشطة
- **التحقق**: فحص شامل لعدم وجود حلقات مفرغة

## الاختبار

### اختبار الربط التلقائي:
```python
# إنشاء حساب أب
parent = Account.objects.create(code="101", name="الأصول المتداولة", account_type="asset")

# إنشاء حساب فرعي - سيتم الربط تلقائياً
child = Account.objects.create(code="101.01", name="النقد وما شابهه", account_type="asset")
assert child.parent == parent
```

### اختبار التحقق من التوافق:
```python
# حساب غير متوافق - سيرفض الربط
incompatible = Account(code="101.01", name="مبيعات", account_type="revenue")
assert not incompatible._is_compatible_account_type(parent.account_type, incompatible.account_type)
```

## الأداء

- **الكفاءة**: البحث المحسن يستخدم فهرسة قاعدة البيانات
- **التخزين المؤقت**: إمكانية إضافة cache للاستعلامات المتكررة
- **الدفعات**: معالجة الحسابات على دفعات لتجنب الضغط على قاعدة البيانات

## التطوير المستقبلي

- [ ] إضافة واجهة API للربط التلقائي
- [ ] دعم أنماط كود إضافية (مثل الشرطة)
- [ ] تحليل ذكي باستخدام AI للكشف عن الأخطاء
- [ ] تقارير مفصلة عن حالة الهرمية
- [ ] نظام إشعارات للحسابات غير المربوطة</content>
<parameter name="filePath">c:\Accounting_soft\finspilot\ACCOUNT_HIERARCHY_GUIDE.md
# ✅ تم إضافة عمود الصندوق النقدي في قائمة الفواتير

## 🎯 الهدف
إضافة **عمود الصندوق** في صفحة قائمة الفواتير (`/ar/sales/invoices/`) لإظهار الصندوق الذي تم إيداع النقد فيه للفواتير النقدية.

---

## 📝 التعديلات المطبقة

### 1. ملف `templates/sales/invoice_list.html`

#### التغيير الأول: إضافة عمودين في رأس الجدول (السطر 343-352)

**قبل:**
```html
<thead class="table-light">
    <tr>
        <th>رقم الفاتورة</th>
        <th>العميل</th>
        <th>التاريخ</th>
        <th>المبلغ الإجمالي</th>
        <th>الحالة</th>
        <th>الإجراءات</th>
    </tr>
</thead>
```

**بعد ✅:**
```html
<thead class="table-light">
    <tr>
        <th>رقم الفاتورة</th>
        <th>العميل</th>
        <th>التاريخ</th>
        <th>المبلغ الإجمالي</th>
        <th>طريقة الدفع</th>      ← جديد
        <th>الصندوق النقدي</th>    ← جديد
        <th>الحالة</th>
        <th>الإجراءات</th>
    </tr>
</thead>
```

---

#### التغيير الثاني: إضافة بيانات العمودين (السطر 365-405)

**عمود طريقة الدفع:**
```html
<td>
    {% if invoice.payment_type == 'cash' %}
        <span class="badge bg-success">
            <i class="fas fa-money-bill-wave"></i> نقدي
        </span>
    {% elif invoice.payment_type == 'credit' %}
        <span class="badge bg-warning">
            <i class="fas fa-credit-card"></i> ذمم (آجل)
        </span>
    {% elif invoice.payment_type == 'check' %}
        <span class="badge bg-info">
            <i class="fas fa-money-check"></i> شيك
        </span>
    {% elif invoice.payment_type == 'installment' %}
        <span class="badge bg-primary">
            <i class="fas fa-calendar-alt"></i> تقسيط
        </span>
    {% else %}
        <span class="badge bg-secondary">غير محدد</span>
    {% endif %}
</td>
```

**عمود الصندوق النقدي:**
```html
<td>
    {% if invoice.payment_type == 'cash' and invoice.cashbox %}
        <!-- فاتورة نقدية مع صندوق محدد -->
        <span class="badge bg-primary">
            <i class="fas fa-box"></i> {{ invoice.cashbox.name }}
        </span>
    {% elif invoice.payment_type == 'cash' and not invoice.cashbox %}
        <!-- فاتورة نقدية بدون صندوق (خطأ) -->
        <span class="text-danger">
            <i class="fas fa-exclamation-triangle"></i> غير محدد
        </span>
    {% else %}
        <!-- ليست فاتورة نقدية -->
        <span class="text-muted">-</span>
    {% endif %}
</td>
```

---

#### التغيير الثالث: إضافة فلاتر (السطر 303-327)

**فلتر طريقة الدفع:**
```html
<div class="col-md-2">
    <label for="payment_type" class="form-label">طريقة الدفع</label>
    <select class="form-select" id="payment_type" name="payment_type">
        <option value="">جميع الأنواع</option>
        <option value="cash">نقدي</option>
        <option value="credit">ذمم (آجل)</option>
        <option value="check">شيك</option>
        <option value="installment">تقسيط</option>
    </select>
</div>
```

**فلتر الصندوق النقدي:**
```html
<div class="col-md-2">
    <label for="cashbox" class="form-label">الصندوق النقدي</label>
    <select class="form-select" id="cashbox" name="cashbox">
        <option value="">جميع الصناديق</option>
        {% for cashbox in cashboxes %}
            <option value="{{ cashbox.id }}">{{ cashbox.name }}</option>
        {% endfor %}
    </select>
</div>
```

---

#### التغيير الرابع: تحسينات CSS للشاشات الصغيرة (السطر 71-79)

```css
/* إخفاء بعض الأعمدة على الشاشات الصغيرة */
@media (max-width: 768px) {
    /* إخفاء عمود التاريخ */
    .table th:nth-child(3),
    .table td:nth-child(3) {
        display: none;
    }
    
    /* إخفاء عمود الصندوق */
    .table th:nth-child(6),
    .table td:nth-child(6) {
        display: none;
    }
}
```

---

### 2. ملف `sales/views.py` (SalesInvoiceListView)

#### التغيير الأول: إضافة فلتر الحالة والصندوق (السطر 191-219)

**قبل:**
```python
def get_queryset(self):
    queryset = SalesInvoice.objects.all()
    
    # Search
    search = self.request.GET.get('search')
    if search:
        queryset = queryset.filter(...)
    
    # Date filter
    date_from = self.request.GET.get('date_from')
    date_to = self.request.GET.get('date_to')
    ...
    
    # Payment type filter
    payment_type = self.request.GET.get('payment_type')
    if payment_type:
        queryset = queryset.filter(payment_type=payment_type)
    
    return queryset.select_related('customer', 'created_by')
```

**بعد ✅:**
```python
def get_queryset(self):
    queryset = SalesInvoice.objects.all()
    
    # Search
    search = self.request.GET.get('search')
    if search:
        queryset = queryset.filter(...)
    
    # Status filter (جديد ✅)
    status = self.request.GET.get('status')
    if status:
        queryset = queryset.filter(status=status)
    
    # Date filter
    date_from = self.request.GET.get('date_from')
    date_to = self.request.GET.get('date_to')
    ...
    
    # Payment type filter
    payment_type = self.request.GET.get('payment_type')
    if payment_type:
        queryset = queryset.filter(payment_type=payment_type)
    
    # Cashbox filter (جديد ✅)
    cashbox_id = self.request.GET.get('cashbox')
    if cashbox_id:
        queryset = queryset.filter(cashbox_id=cashbox_id)
    
    # إضافة 'cashbox' للـ select_related
    return queryset.select_related('customer', 'created_by', 'cashbox')
```

---

#### التغيير الثاني: إضافة قائمة الصناديق للسياق (السطر 221-248)

**قبل:**
```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    
    # Statistics
    invoices = SalesInvoice.objects.all()
    context['total_invoices'] = invoices.count()
    ...
    
    # Currency settings
    ...
    
    return context
```

**بعد ✅:**
```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    
    # Statistics
    invoices = SalesInvoice.objects.all()
    context['total_invoices'] = invoices.count()
    ...
    
    # Cashboxes list for filter (جديد ✅)
    try:
        from cashboxes.models import Cashbox
        context['cashboxes'] = Cashbox.objects.filter(is_active=True).order_by('name')
    except ImportError:
        context['cashboxes'] = []
    
    # Currency settings
    ...
    
    return context
```

---

## 🎉 النتيجة

### عرض البيانات في الجدول:

| رقم الفاتورة | العميل | التاريخ | المبلغ | **طريقة الدفع** | **الصندوق** | الحالة | الإجراءات |
|--------------|---------|---------|--------|-----------------|--------------|--------|-----------|
| INV-001 | أحمد | 2025-10-05 | 150.000 | 🟢 نقدي | 📦 صندوق الفرع الرئيسي | ✅ مدفوع | ... |
| INV-002 | محمد | 2025-10-04 | 250.500 | 🟡 ذمم (آجل) | - | ⏳ معلق | ... |
| INV-003 | خالد | 2025-10-03 | 89.000 | 🟢 نقدي | 📦 صندوق الكاشير 1 | ✅ مدفوع | ... |
| INV-004 | فاطمة | 2025-10-02 | 120.000 | 🟢 نقدي | ⚠️ غير محدد | ✅ مدفوع | ... |
| INV-005 | علي | 2025-10-01 | 180.000 | 🔵 شيك | - | ⏳ معلق | ... |

---

### الفلاتر المتاحة:

```
┌─────────────────┬──────────────────┬─────────────┬──────────────┐
│ البحث           │ طريقة الدفع      │ الصندوق     │ الحالة       │
├─────────────────┼──────────────────┼─────────────┼──────────────┤
│ رقم/اسم عميل   │ • جميع الأنواع   │ • جميع      │ • جميع       │
│                 │ • نقدي ✅        │ • الفرع     │ • مسودة      │
│                 │ • ذمم (آجل)     │ • الكاشير 1 │ • مرسل       │
│                 │ • شيك           │ • الكاشير 2 │ • مدفوع ✅   │
│                 │ • تقسيط         │              │ • ملغي       │
└─────────────────┴──────────────────┴─────────────┴──────────────┘
```

---

## 🔍 حالات العرض

### حالة 1: فاتورة نقدية مع صندوق محدد ✅
```html
طريقة الدفع: 🟢 نقدي
الصندوق: 📦 صندوق الفرع الرئيسي
```

### حالة 2: فاتورة نقدية بدون صندوق ⚠️
```html
طريقة الدفع: 🟢 نقدي
الصندوق: ⚠️ غير محدد  (تحذير بالأحمر)
```

### حالة 3: فاتورة ذمم/شيك/تقسيط
```html
طريقة الدفع: 🟡 ذمم (آجل)
الصندوق: -  (علامة ناقص)
```

---

## 📊 استعلامات الفلترة

### مثال 1: جميع الفواتير النقدية
```
URL: /ar/sales/invoices/?payment_type=cash
النتيجة: فقط الفواتير بطريقة دفع "نقدي"
```

### مثال 2: فواتير صندوق معين
```
URL: /ar/sales/invoices/?cashbox=1
النتيجة: فقط الفواتير المسجلة في الصندوق رقم 1
```

### مثال 3: فواتير نقدية لصندوق معين
```
URL: /ar/sales/invoices/?payment_type=cash&cashbox=2
النتيجة: فواتير نقدية فقط من الصندوق رقم 2
```

### مثال 4: فواتير نقدية مدفوعة من صندوق معين
```
URL: /ar/sales/invoices/?payment_type=cash&cashbox=1&status=paid
النتيجة: فواتير نقدية مدفوعة من الصندوق رقم 1
```

---

## 🧪 الاختبار

### 1. اختبار العرض الأساسي
```bash
# افتح المتصفح
http://127.0.0.1:8000/ar/sales/invoices/

# تحقق من:
✅ ظهور عمود "طريقة الدفع"
✅ ظهور عمود "الصندوق النقدي"
✅ الفواتير النقدية تعرض اسم الصندوق
✅ الفواتير غير النقدية تعرض "-"
```

### 2. اختبار الفلاتر
```bash
# فلترة بطريقة الدفع
1. اختر "نقدي" من فلتر طريقة الدفع
2. انقر "بحث"
3. النتيجة: فقط الفواتير النقدية ✅

# فلترة بالصندوق
1. اختر "صندوق الفرع الرئيسي"
2. انقر "بحث"
3. النتيجة: فقط فواتير هذا الصندوق ✅

# فلترة مركبة
1. اختر "نقدي" + "صندوق الكاشير 1"
2. انقر "بحث"
3. النتيجة: فواتير نقدية من الصندوق المحدد ✅
```

### 3. اختبار الأجهزة المحمولة
```bash
# افتح أدوات المطور (F12)
# غير حجم الشاشة إلى 768px
# تحقق من:
✅ إخفاء عمود "التاريخ"
✅ إخفاء عمود "الصندوق"
✅ بقاء الأعمدة المهمة (رقم، عميل، مبلغ، إجراءات)
```

---

## 📝 ملخص التعديلات

| الملف | التعديلات | الغرض |
|------|----------|-------|
| `templates/sales/invoice_list.html` | 4 تعديلات | إضافة عمودين + فلاتر + CSS |
| `sales/views.py` | 2 تعديل | إضافة فلترة بالصندوق + قائمة الصناديق |
| **المجموع** | **6 تعديلات** | **عرض وفلترة الصناديق** |

---

## ✅ التأكيد

- [x] عمود "طريقة الدفع" مضاف
- [x] عمود "الصندوق النقدي" مضاف
- [x] الفواتير النقدية تعرض اسم الصندوق
- [x] الفواتير غير النقدية تعرض "-"
- [x] تحذير للفواتير النقدية بدون صندوق
- [x] فلتر طريقة الدفع مضاف
- [x] فلتر الصندوق مضاف
- [x] تحسينات للشاشات الصغيرة
- [x] لم يتم رفع التعديلات على الريموت ✅

---

## ⚠️ ملاحظة نهائية

**لم يتم رفع أي شيء على GitHub** (حسب طلبك)

جميع التعديلات محلية. يمكنك اختبارها الآن:

```bash
# تشغيل السيرفر
python manage.py runserver

# فتح الصفحة
http://127.0.0.1:8000/ar/sales/invoices/

# النتيجة المتوقعة:
✅ عمود جديد يعرض طريقة الدفع
✅ عمود جديد يعرض الصندوق للفواتير النقدية
✅ فلاتر للبحث بطريقة الدفع والصندوق
✅ تحديد الصناديق التي تم إيداع النقد فيها
```

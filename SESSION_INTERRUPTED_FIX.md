# دليل إصلاح مشكلة SessionInterrupted على الخادم المباشر

## المشكلة
```
SessionInterrupted at /ar/sales/invoices/add/
The request's session was deleted before the request completed.
```

## السبب
توجد سيجنالات مكررة في ملف `sales/signals.py` تعمل 3 مرات على نفس الحدث، مما يسبب:
- ⏱️ **بطء شديد** في حفظ الفاتورة
- 🔄 **معالجة مكررة** لنفس البيانات 3 مرات
- 🔥 **انتهاء الجلسة** قبل اكتمال العملية

## الحل
حذف السيجنالات المكررة من السطر 463 حتى 936 (475 سطر مكرر)

---

## خطوات التطبيق على الخادم

### الطريقة 1: عبر SSH (الأسرع) ⭐

```bash
# 1. اتصل بالخادم
ssh username@your-server.com

# 2. انتقل لمجلد المشروع
cd /path/to/finspilot

# 3. إنشاء نسخة احتياطية
cp sales/signals.py sales/signals.py.backup_$(date +%Y%m%d_%H%M%S)

# 4. تشغيل السكريبت
python remove_duplicate_signals.py

# 5. أعد تشغيل الخادم
sudo systemctl restart gunicorn
# أو
sudo systemctl restart finspilot
```

---

### الطريقة 2: عبر محرر نصوص يدوياً

```bash
# 1. افتح الملف
nano sales/signals.py
# أو
vim sales/signals.py

# 2. احذف كل شيء من السطر 463 حتى نهاية الملف
# في nano: اذهب للسطر 463، اضغط Ctrl+K عدة مرات
# في vim: اذهب للسطر 463، اكتب: :463,$d

# 3. احفظ الملف
# في nano: Ctrl+O ثم Enter ثم Ctrl+X
# في vim: :wq

# 4. أعد تشغيل الخادم
sudo systemctl restart gunicorn
```

---

### الطريقة 3: عبر Python مباشرة

```bash
python << 'EOF'
file_path = 'sales/signals.py'

# قراءة الملف
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# نسخة احتياطية
with open(file_path + '.backup', 'w', encoding='utf-8') as f:
    f.writelines(lines)

# حفظ أول 460 سطر فقط
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines[:460])

print(f"✅ تم حذف {len(lines) - 460} سطر مكرر")
EOF

# أعد تشغيل الخادم
sudo systemctl restart gunicorn
```

---

### الطريقة 4: رفع السكريبت عبر SFTP

1. **ارفع الملف** `remove_duplicate_signals.py` إلى مجلد المشروع على الخادم
2. **شغله عبر SSH** أو لوحة التحكم:
   ```bash
   python remove_duplicate_signals.py
   ```
3. **أعد تشغيل الخادم**

---

## التحقق من نجاح الإصلاح

بعد تطبيق الإصلاح:

1. ✅ افتح صفحة إنشاء فاتورة مبيعات
2. ✅ أضف منتجات وحدد الصندوق
3. ✅ احفظ الفاتورة
4. ✅ يجب أن تُحفظ **بسرعة** (أقل من 2 ثانية)
5. ✅ لا يجب أن يظهر خطأ `SessionInterrupted`

---

## معلومات تقنية

### عدد الأسطر:
- **قبل**: 935 سطر
- **بعد**: 460 سطر
- **محذوف**: 475 سطر (السيجنالات المكررة)

### السيجنالات المكررة:
تم حذف النسخ المكررة من:
- `update_cashbox_transaction_on_invoice_change` (كانت موجودة 3 مرات)
- `update_inventory_on_sales_invoice` (كانت موجودة 3 مرات)
- `update_inventory_on_sales_return` (كانت موجودة 3 مرات)
- `update_inventory_on_sales_invoice_item` (كانت موجودة 2 مرة)
- `create_cogs_entry_for_sales_invoice_item` (كانت موجودة 2 مرة)
- `update_inventory_on_sales_return_item` (كانت موجودة 2 مرة)

### تحسين الأداء:
- ⚡ **سرعة الحفظ**: تحسنت بنسبة ~66%
- 🔄 **عدد العمليات**: انخفض من 3× إلى 1×
- 💾 **استهلاك الذاكرة**: انخفض بشكل ملحوظ

---

## استكشاف الأخطاء

### خطأ: "No such file or directory"
**الحل:** تأكد من أنك في مجلد المشروع الصحيح
```bash
cd /path/to/finspilot
pwd  # يجب أن يُظهر مسار المشروع
ls sales/signals.py  # يجب أن يظهر الملف
```

### خطأ بعد الحذف
**الحل:** استعادة النسخة الاحتياطية
```bash
cp sales/signals.py.backup sales/signals.py
sudo systemctl restart gunicorn
```

### الخطأ مازال موجوداً
**الحل:** تأكد من إعادة تشغيل الخادم بعد التعديل

---

## ملاحظات مهمة

⚠️ **قبل التطبيق:**
- خذ نسخة احتياطية من `sales/signals.py`
- يفضل التطبيق في وقت قليل الاستخدام
- اختبر على بيئة تطوير أولاً إن أمكن

✅ **بعد التطبيق:**
- اختبر إنشاء فاتورة مبيعات
- اختبر إنشاء مردود مبيعات
- تحقق من تحديث المخزون
- تحقق من إنشاء القيود المحاسبية

🔧 **الصيانة:**
- تحقق بشكل دوري من عدم تكرار السيجنالات
- راقب أداء حفظ الفواتير
- راقب سجلات الأخطاء (logs)

---

## المساعدة

إذا واجهت أي مشكلة:
1. تحقق من سجلات الأخطاء: `tail -f /var/log/gunicorn/error.log`
2. استعد النسخة الاحتياطية إذا لزم الأمر
3. أعد تشغيل الخادم دائماً بعد أي تعديل

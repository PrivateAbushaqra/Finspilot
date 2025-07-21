# دليل إنشاء قاعدة بيانات جديدة - نظام Finspilot المحاسبي

## 📋 المعلومات الضرورية لإنشاء قاعدة بيانات جديدة

### 1. المتطلبات الأساسية

#### ✅ البرامج المطلوبة:
- Python 3.11+ 
- Django 4.2.7
- المكتبات المحددة في `requirements.txt`

#### ✅ المعلومات الأساسية المطلوبة:
- **اسم الشركة** (مطلوب)
- **عملة الأساس** (افتراضي: الريال السعودي SAR)
- **العنوان والمعلومات التجارية** (اختياري)
- **الرقم الضريبي** (اختياري)
- **بيانات المستخدم الرئيسي** (superadmin)

### 2. الخطوات المطلوبة لإنشاء قاعدة بيانات جديدة

#### الخطوة 1: حذف قاعدة البيانات الحالية (إن وجدت)
```powershell
# حذف ملف قاعدة البيانات
Remove-Item "db.sqlite3" -Force -ErrorAction SilentlyContinue

# حذف ملفات الهجرات (الاحتفاظ بـ __init__.py فقط)
Get-ChildItem -Path . -Recurse -Name "migrations" | ForEach-Object {
    $path = "$_"
    Get-ChildItem -Path $path -Include "*.py" -Exclude "__init__.py" | Remove-Item -Force
}
```

#### الخطوة 2: إنشاء هجرات جديدة
```powershell
python manage.py makemigrations
```

#### الخطوة 3: تطبيق الهجرات بالترتيب الصحيح
```powershell
# 1. تطبيق هجرات Django الأساسية
python manage.py migrate contenttypes
python manage.py migrate auth
python manage.py migrate sessions
python manage.py migrate admin

# 2. تطبيق هجرات التطبيقات الأساسية
python manage.py migrate users
python manage.py migrate core
python manage.py migrate settings

# 3. تطبيق باقي الهجرات
python manage.py migrate
```

#### الخطوة 4: إنشاء البيانات الأساسية
```powershell
# 1. إنشاء المستخدم الرئيسي
python create_superadmin.py

# 2. إنشاء العملات الافتراضية
python create_default_currencies.py

# 3. إنشاء المجموعات والصلاحيات
python create_default_groups.py

# 4. إنشاء الحسابات المحاسبية الافتراضية
python create_default_accounts.py

# 5. جمع الملفات الثابتة
python manage.py collectstatic --noinput
```

### 3. الترتيب الصحيح للهجرات

#### أولاً: هجرات Django الأساسية
1. `contenttypes.0001_initial`
2. `auth.0001_initial`
3. `sessions.0001_initial`
4. `admin.0001_initial`

#### ثانياً: هجرات التطبيقات الأساسية
1. `users.0001_initial` - نموذج المستخدم المخصص
2. `core.0001_initial` - النماذج الأساسية
3. `settings.0001_initial` - إعدادات الشركة والعملات

#### ثالثاً: هجرات التطبيقات المحاسبية
1. `accounts.0001_initial` - الحسابات المحاسبية
2. `journal.0001_initial` - دفتر اليومية
3. `products.0001_initial` - المنتجات
4. `customers.0001_initial` - العملاء والموردين
5. `banks.0001_initial` - الحسابات البنكية
6. `cashboxes.0001_initial` - الصناديق

#### رابعاً: هجرات باقي التطبيقات
1. `sales.0001_initial` - المبيعات
2. `purchases.0001_initial` - المشتريات
3. `inventory.0001_initial` - المخزون
4. `receipts.0001_initial` - سندات القبض
5. `payments.0001_initial` - سندات الدفع
6. `revenues_expenses.0001_initial` - الإيرادات والمصاريف
7. `assets_liabilities.0001_initial` - الأصول والالتزامات

### 4. البيانات الافتراضية المطلوبة

#### 🔑 المستخدم الرئيسي
- **اسم المستخدم**: superadmin
- **كلمة المرور**: password (يُنصح بتغييرها فوراً)
- **البريد الإلكتروني**: superadmin@finspilot.com
- **النوع**: Super Admin
- **الصلاحيات**: جميع الصلاحيات

#### 💱 العملات المدعومة
- **الريال السعودي (SAR)** - العملة الأساسية
- **الدولار الأمريكي (USD)**
- **اليورو (EUR)**
- **الدرهم الإماراتي (AED)**
- **الدينار الكويتي (KWD)**
- **وعملات أخرى...**

#### 👥 المجموعات الافتراضية
- **المدراء** - صلاحيات كاملة
- **المحاسبين** - صلاحيات محاسبية
- **أمناء المخزن** - إدارة المخزون
- **البائعين** - المبيعات فقط

#### 🏦 الحسابات المحاسبية الافتراضية
- **الأصول**: الصندوق، البنوك، العملاء، المخزون
- **المطلوبات**: الدائنون، الموردون، الضرائب
- **حقوق الملكية**: رأس المال، الأرباح المحتجزة
- **الإيرادات**: المبيعات، الإيرادات الأخرى
- **المصاريف**: المصاريف العامة، الرواتب، الإيجارات

### 5. تصدير واستيراد البيانات

#### 🔄 تصدير البيانات من قاعدة البيانات الحالية
```powershell
# تصدير جميع البيانات
python manage.py dumpdata --natural-foreign --natural-primary > backup_data.json

# تصدير بيانات محددة (بدون جلسات وسجلات التدقيق)
python manage.py dumpdata --natural-foreign --natural-primary --exclude=sessions --exclude=admin.logentry --exclude=contenttypes --exclude=auth.permission > clean_backup.json
```

#### 📥 استيراد البيانات إلى قاعدة البيانات الجديدة
```powershell
# بعد إعداد قاعدة البيانات الجديدة وتطبيق الهجرات
python manage.py loaddata clean_backup.json
```

#### ⚠️ تحذيرات مهمة عند الاستيراد:
1. **تأكد من تطابق إصدارات النماذج**
2. **تجنب استيراد جلسات المستخدمين القديمة**
3. **تحقق من تطابق أنواع البيانات**
4. **قم بنسخ احتياطي قبل الاستيراد**

### 6. سكريبت إعداد شامل

#### استخدام السكريبت الجاهز:
```powershell
# تشغيل سكريبت الإعداد الشامل
.\setup_system.ps1
```

#### أو تشغيل الأوامر يدوياً:
```powershell
# 1. إنشاء وتطبيق الهجرات
python manage.py makemigrations
python manage.py migrate

# 2. إنشاء البيانات الأساسية
python create_superadmin.py
python create_default_currencies.py  
python create_default_groups.py
python create_default_accounts.py

# 3. جمع الملفات الثابتة
python manage.py collectstatic --noinput
```

### 7. التحقق من نجاح الإعداد

#### ✅ فحوصات ما بعد الإعداد:
```powershell
# فحص حالة قاعدة البيانات
python manage.py showmigrations

# فحص البيانات الأساسية
python manage.py shell -c "
from users.models import User
from settings.models import Currency, CompanySettings
from journal.models import Account

print(f'المستخدمين: {User.objects.count()}')
print(f'العملات: {Currency.objects.count()}')
print(f'الحسابات: {Account.objects.count()}')
print(f'إعدادات الشركة: {CompanySettings.objects.count()}')
"

# تشغيل الخادم للاختبار
python manage.py runserver
```

### 8. نصائح مهمة

#### 🔒 الأمان:
- غيّر كلمة مرور superadmin فوراً
- فعّل نظام انتهاء الجلسة
- حدث المفاتيح السرية في الإنتاج

#### 🚀 الأداء:
- استخدم PostgreSQL في الإنتاج
- فعّل ضغط الملفات الثابتة
- راقب حجم قاعدة البيانات

#### 🔧 الصيانة:
- قم بنسخ احتياطية دورية
- راقب سجلات الأخطاء
- حدث البيانات المرجعية حسب الحاجة

---

## 📞 الدعم

لأي استفسارات تقنية أو مشاكل في الإعداد، راجع:
- ملف `README.md`
- ملف `DB_INFO_SUMMARY.txt`
- سجلات النظام في Django Admin

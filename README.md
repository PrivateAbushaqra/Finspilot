# Finspilot - نظام محاسبي شامل

نظام محاسبي متكامل مبني بـ Django لإدارة الأعمال المالية والمحاسبية.

## 🚀 **الميزات**

- ✅ إدارة الحسابات والقيود اليومية
- ✅ إدارة العملاء والموردين
- ✅ إدارة المخزون والمنتجات
- ✅ إدارة المبيعات والمشتريات
- ✅ إدارة البنوك والصناديق النقدية
- ✅ التقارير المالية الشاملة
- ✅ نظام المستخدمين والصلاحيات
- ✅ دعم اللغة العربية
- ✅ واجهة ويب حديثة

## 🛠️ **التقنيات المستخدمة**

- **Backend**: Django 4.2.7
- **Database**: PostgreSQL
- **Frontend**: HTML5, CSS3, Bootstrap 5
- **API**: Django REST Framework
- **Deployment**: Render.com
- **Python**: 3.11.9

## 📋 **متطلبات النظام**

- Python 3.11.9+
- PostgreSQL 12+
- Git

## 🚀 **التثبيت والتشغيل**

### **1. استنساخ المشروع**
```bash
git clone https://github.com/your-username/finspilot.git
cd finspilot
```

### **2. إنشاء البيئة الافتراضية**
```bash
python -m venv .venv
.venv\Scripts\activate  # على Windows
```

### **3. تثبيت المتطلبات**
```bash
pip install -r requirements.txt
```

### **4. إعداد قاعدة البيانات**
```bash
# إنشاء قاعدة بيانات PostgreSQL
createdb finspilot_local

# أو استخدم setup_postgres.bat على Windows
```

### **5. إعداد متغيرات البيئة**
```bash
cp .env.example .env
# عدل .env حسب إعداداتك
```

### **6. تشغيل migrations**
```bash
python manage.py migrate
```

### **7. إنشاء مستخدم Admin**
```bash
python manage.py createsuperuser
```

### **8. تشغيل الخادم**
```bash
python manage.py runserver
```

## 🌐 **النشر على Render.com**

اتبع دليل النشر المفصل في `RENDER_DEPLOYMENT_GUIDE.md`

### **خطوات سريعة:**
1. ارفع الكود إلى GitHub
2. أنشئ Web Service على Render
3. أنشئ PostgreSQL Database على Render
4. اربط الخدمتين
5. انشر التطبيق

### **التحقق من الإعدادات:**
```bash
# تشغيل script التحقق
./check_deployment.sh
```

## 📁 **هيكل المشروع**

```
finspilot/
├── accounts/          # إدارة الحسابات
├── assets_liabilities/ # الأصول والخصوم
├── backup/           # النسخ الاحتياطي
├── banks/            # إدارة البنوك
├── cashboxes/        # الصناديق النقدية
├── core/             # النواة الأساسية
├── customers/        # إدارة العملاء
├── documents/        # إدارة المستندات
├── hr/               # الموارد البشرية
├── inventory/        # إدارة المخزون
├── journal/          # القيود اليومية
├── payments/         # المدفوعات
├── products/         # المنتجات
├── provisions/       # المخصصات
├── purchases/        # المشتريات
├── receipts/         # الإيصالات
├── reports/          # التقارير
├── revenues_expenses/ # الإيرادات والمصروفات
├── sales/            # المبيعات
├── search/           # البحث
├── settings/         # الإعدادات
├── users/            # إدارة المستخدمين
├── static/           # الملفات الثابتة
├── templates/        # القوالب
└── media/            # الملفات المرفوعة
```

## 🔧 **الأوامر المفيدة**

```bash
# تشغيل الخادم
python manage.py runserver

# تشغيل migrations
python manage.py migrate

# إنشاء migration جديد
python manage.py makemigrations

# إنشاء مستخدم superuser
python manage.py createsuperuser

# جمع الملفات الثابتة
python manage.py collectstatic

# فحص النظام
python manage.py check

# تشغيل الاختبارات
python manage.py test

# إنشاء نسخة احتياطية
python manage.py dumpdata > backup.json

# استعادة النسخة الاحتياطية
python manage.py loaddata backup.json
```

## 📊 **التقارير المتاحة**

- ميزان المراجعة
- قائمة الدخل
- التدفق النقدي
- تقارير المبيعات والمشتريات
- تقارير المخزون
- تقارير العملاء والموردين

## 🔐 **الأمان**

- تشفير كلمات المرور
- نظام صلاحيات متقدم
- حماية CSRF
- جلسات آمنة
- تدقيق العمليات

## 🌍 **الدعم**

- **اللغة**: العربية والإنجليزية
- **العملة**: الدينار الأردني (JOD)
- **المنطقة الزمنية**: UTC+3

## 📝 **الترخيص**

هذا المشروع محمي بحقوق الطبع والنشر.

## 👥 **المساهمة**

نرحب بالمساهمات! يرجى قراءة دليل المساهمة قبل البدء.

## 📞 **الدعم الفني**

للحصول على الدعم، يرجى التواصل مع فريق التطوير.

---

**تم تطوير هذا النظام بواسطة فريق Finspilot** 💼

## 🔍 **إثبات استخدام PostgreSQL**

بعد النشر على Render.com، يمكنك التحقق من أن التطبيق يستخدم PostgreSQL وليس SQLite من خلال:

### **صفحة معلومات قاعدة البيانات**
- اذهب إلى: `https://your-app-name.onrender.com/ar/database-info/`
- ستجد صفحة تعرض:
  - ✅ نوع قاعدة البيانات: PostgreSQL
  - ✅ اسم قاعدة البيانات
  - ✅ المضيف والمنفذ
  - ✅ حالة الاتصال: متصل
  - ✅ نشر على Render: نعم

### **الاختبار السريع**
```bash
# في Django shell على Render.com
python manage.py shell -c "from django.db import connection; print(connection.vendor)"
# يجب أن يطبع: postgresql
```

### **لماذا PostgreSQL وليس SQLite؟**
- **الإنتاج**: SQLite غير مناسب للإنتاج بسبب مشاكل التزامن
- **الأداء**: PostgreSQL أسرع وأكثر موثوقية للتطبيقات متعددة المستخدمين
- **النسخ الاحتياطي**: PostgreSQL يدعم النسخ الاحتياطي المتقدم
- **الأمان**: PostgreSQL يوفر تحكماً أفضل في الصلاحيات
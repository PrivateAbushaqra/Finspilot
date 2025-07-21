# دليل نشر نظام Finspilot على Render.com

## 📋 المحتويات
1. [إعداد ملفات النشر](#1-إعداد-ملفات-النشر)
2. [إنشاء قاعدة بيانات PostgreSQL](#2-إنشاء-قاعدة-بيانات-postgresql)
3. [إعداد التطبيق على Render](#3-إعداد-التطبيق-على-render)
4. [ربط قاعدة البيانات](#4-ربط-قاعدة-البيانات)
5. [نشر التطبيق](#5-نشر-التطبيق)
6. [الإعداد الأولي](#6-الإعداد-الأولي)
7. [حل المشاكل الشائعة](#7-حل-المشاكل-الشائعة)

---

## 1. إعداد ملفات النشر

### الخطوة 1.1: إنشاء ملف requirements.txt محدث
```bash
# قم بتحديث ملف requirements.txt
pip freeze > requirements.txt
```

### الخطوة 1.2: إنشاء ملف Procfile
أنشئ ملف `Procfile` في جذر المشروع (بدون امتداد):
```
web: gunicorn finspilot.wsgi:application
```

### الخطوة 1.3: إنشاء ملف runtime.txt
أنشئ ملف `runtime.txt` لتحديد إصدار Python:
```
python-3.11.6
```

### الخطوة 1.4: إضافة Gunicorn إلى requirements.txt
أضف هذه السطور لـ requirements.txt:
```
gunicorn>=21.2.0
psycopg2-binary>=2.9.7
whitenoise>=6.5.0
dj-database-url>=2.1.0
```

### الخطوة 1.5: إنشاء ملف .env.example
```bash
# إعدادات الأمان
SECRET_KEY=your-secret-key-here
DEBUG=False

# إعدادات قاعدة البيانات
DATABASE_URL=postgresql://username:password@hostname:port/database_name

# إعدادات التطبيق
ALLOWED_HOSTS=your-app-name.onrender.com,localhost,127.0.0.1
DEFAULT_CURRENCY=SAR

# إعدادات Render
RENDER=True
```

---

## 2. إنشاء قاعدة بيانات PostgreSQL

### الخطوة 2.1: إنشاء خدمة PostgreSQL
1. سجل دخول إلى [Render.com](https://render.com)
2. انقر على **"New +"** من الشريط العلوي
3. اختر **"PostgreSQL"**

### الخطوة 2.2: إعداد قاعدة البيانات
```
Name: finspilot-database
Database: finspilot_prod
User: finspilot_admin
Region: اختر الأقرب لك (مثل Frankfurt أو Singapore)
PostgreSQL Version: 15
Plan: Free (للبداية)
```

### الخطوة 2.3: حفظ معلومات قاعدة البيانات
بعد الإنشاء، احفظ هذه المعلومات:
- **Internal Database URL**: سيبدأ بـ `postgresql://`
- **External Database URL**: للاتصال من الخارج
- **Host**: عنوان الخادم
- **Port**: رقم المنفذ
- **Database**: اسم قاعدة البيانات
- **Username**: اسم المستخدم
- **Password**: كلمة المرور

---

## 3. إعداد التطبيق على Render

### الخطوة 3.1: إنشاء Web Service
1. انقر على **"New +"** → **"Web Service"**
2. اختر **"Connect a repository"**
3. اربط حسابك مع GitHub (إذا لم يكن مربوطاً)
4. ارفع كود المشروع إلى GitHub أولاً

### الخطوة 3.2: ربط Repository (طرق متعددة)

**الطريقة الأولى: GitHub (الأسهل)**
1. اختر المستودع (Repository) الخاص بك من GitHub
2. Render سيتزامن تلقائياً مع التحديثات

**الطريقة الثانية: Public Git Repository**
1. استخدم **"Public Git Repository"** 
2. أدخل رابط المشروع من أي خدمة Git أخرى:
   - GitLab: `https://gitlab.com/username/project.git`
   - Bitbucket: `https://bitbucket.org/username/project.git`
   - أي خادم Git عام آخر

**الطريقة الثالثة: رفع الملفات مباشرة (محدود)**
- بعض خدمات الاستضافة تدعم رفع ملف ZIP
- لكن Render يفضل Git Repository

### الخطوة 3.3: إعداد خدمة الويب
```
Name: finspilot-accounting
Environment: Python 3
Region: نفس منطقة قاعدة البيانات
Branch: main (أو master)
Build Command: pip install -r requirements.txt
Start Command: gunicorn finspilot.wsgi:application
Plan: Free (للبداية)
```

---

## 4. ربط قاعدة البيانات

### الخطوة 4.1: إضافة متغيرات البيئة
في إعدادات Web Service، أضف هذه المتغيرات:

```bash
# الأمان
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
DEBUG=False
RENDER=True

# قاعدة البيانات
DATABASE_URL=postgresql://username:password@hostname:port/database_name

# الاستضافة
ALLOWED_HOSTS=your-app-name.onrender.com

# التطبيق
DEFAULT_CURRENCY=SAR
```

### الخطوة 4.2: إنشاء مفتاح سري جديد
```python
# قم بتشغيل هذا في Python shell لإنشاء مفتاح سري
import secrets
print(secrets.token_urlsafe(50))
```

---

## 5. نشر التطبيق

### الخطوة 5.1: رفع الكود إلى GitHub
```bash
# إضافة ملفات جديدة
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### الخطوة 5.2: انتظار النشر
- Render سيقوم تلقائياً بنشر التطبيق
- راقب سجلات النشر (Deploy Logs)
- قد يستغرق 5-15 دقيقة

### الخطوة 5.3: التحقق من النشر
بعد النشر الناجح:
1. افتح رابط التطبيق
2. يجب أن تشاهد صفحة Django الافتراضية أو صفحة خطأ (طبيعي قبل الإعداد)

---

## 6. الإعداد الأولي

### الخطوة 6.1: تطبيق الهجرات
في **Render Shell** (من إعدادات الخدمة):
```bash
# تطبيق الهجرات
python manage.py migrate

# إنشاء المستخدم الرئيسي
python manage.py shell -c "
from users.models import User
if not User.objects.filter(username='superadmin').exists():
    User.objects.create_superuser(
        username='superadmin',
        email='admin@finspilot.com',
        password='Finspilot@2025',
        first_name='Super',
        last_name='Admin',
        user_type='superadmin'
    )
    print('تم إنشاء المستخدم الرئيسي')
else:
    print('المستخدم موجود بالفعل')
"

# جمع الملفات الثابتة
python manage.py collectstatic --noinput
```

### الخطوة 6.2: إعداد البيانات الأساسية
```bash
# إنشاء العملات الافتراضية
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from settings.models import Currency
default_currencies = [
    {'code': 'SAR', 'name': 'الريال السعودي', 'symbol': 'ر.س', 'exchange_rate': 1.0, 'is_base_currency': True},
    {'code': 'USD', 'name': 'الدولار الأمريكي', 'symbol': '$', 'exchange_rate': 3.75, 'is_base_currency': False},
    {'code': 'EUR', 'name': 'اليورو', 'symbol': '€', 'exchange_rate': 4.08, 'is_base_currency': False},
]

for curr in default_currencies:
    Currency.objects.get_or_create(code=curr['code'], defaults=curr)
    print(f'تم إنشاء عملة: {curr[\"name\"]}')
"

# إنشاء الحسابات المحاسبية
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from journal.models import Account
accounts = [
    {'code': '1010', 'name': 'الصندوق', 'account_type': 'asset'},
    {'code': '1020', 'name': 'البنوك', 'account_type': 'asset'},
    {'code': '1050', 'name': 'العملاء', 'account_type': 'asset'},
    {'code': '2050', 'name': 'الموردون', 'account_type': 'liability'},
    {'code': '4010', 'name': 'المبيعات', 'account_type': 'sales'},
    {'code': '5010', 'name': 'المشتريات', 'account_type': 'purchases'},
]

for acc in accounts:
    Account.objects.get_or_create(code=acc['code'], defaults=acc)
    print(f'تم إنشاء حساب: {acc[\"name\"]}')
"
```

---

## 7. حل المشاكل الشائعة

### مشكلة 7.1: "Application failed to start"
**الحل:**
1. تحقق من سجلات النشر (Deploy Logs)
2. تأكد من وجود `Procfile` صحيح
3. تحقق من `requirements.txt`

### مشكلة 7.2: "Database connection failed"
**الحل:**
1. تحقق من `DATABASE_URL` في متغيرات البيئة
2. تأكد من أن قاعدة البيانات تعمل
3. تحقق من إعدادات الشبكة

### مشكلة 7.3: "Static files not loading"
**الحل:**
```bash
# في Render Shell
python manage.py collectstatic --noinput
```

### مشكلة 7.4: "ALLOWED_HOSTS error"
**الحل:**
أضف نطاق Render إلى متغيرات البيئة:
```
ALLOWED_HOSTS=your-app-name.onrender.com,localhost
```

---

## 8. نصائح مهمة

### 🔒 الأمان:
1. **لا تكشف المفاتيح السرية** في الكود
2. **استخدم متغيرات البيئة** لجميع الإعدادات الحساسة
3. **غيّر كلمة مرور superadmin** بعد النشر
4. **فعّل HTTPS** (مجاني في Render)

### 🚀 الأداء:
1. **استخدم خطة مدفوعة** للإنتاج
2. **فعّل auto-scaling** عند الحاجة
3. **راقب استخدام الذاكرة** و المعالج
4. **استخدم CDN** للملفات الثابتة

### 💾 النسخ الاحتياطي:
1. **فعّل النسخ الاحتياطي التلقائي** لقاعدة البيانات
2. **اعمل نسخة احتياطية يدوية** قبل التحديثات
3. **احفظ نسخة من متغيرات البيئة**

### 🔍 المراقبة:
1. **راقب سجلات التطبيق** بانتظام
2. **اعمل اختبارات دورية** للوظائف
3. **راقب أداء قاعدة البيانات**

---

## 9. روابط مفيدة

- **لوحة تحكم Render**: https://dashboard.render.com
- **وثائق Render**: https://render.com/docs
- **دعم Render**: https://render.com/support
- **مجتمع Render**: https://community.render.com

---

## 10. تسجيل الدخول للنظام

بعد النشر الناجح:
- **الرابط**: https://your-app-name.onrender.com/admin/
- **اسم المستخدم**: superadmin
- **كلمة المرور**: Finspilot@2025

⚠️ **مهم**: غيّر كلمة المرور فوراً بعد أول تسجيل دخول!

---

## 11. الخطوات التالية

1. **اختبر جميع الوظائف** في البيئة المباشرة
2. **أعد إعداد إعدادات الشركة** من لوحة التحكم
3. **أنشئ المستخدمين** والصلاحيات المطلوبة
4. **استورد البيانات** إذا كان لديك نسخة احتياطية
5. **اعمل domain مخصص** (اختياري)

---

## 🎉 مبروك!

تم نشر نظام Finspilot المحاسبي بنجاح على Render.com!

للدعم التقني، راجع ملف `RENDER_TROUBLESHOOTING.md`

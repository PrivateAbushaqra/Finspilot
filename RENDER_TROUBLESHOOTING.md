# دليل حل المشاكل - Render.com

## 🔧 المشاكل الشائعة وحلولها

### 1. مشكلة فشل النشر (Build Failed)

#### الأعراض:
- رسالة "Build failed" في سجلات النشر
- التطبيق لا يبدأ

#### الحلول:

**أ) فحص requirements.txt:**
```bash
# تأكد من وجود جميع المكتبات المطلوبة
Django==4.2.7
psycopg2-binary==2.9.7
gunicorn==21.2.0
whitenoise==6.5.0
dj-database-url==2.1.0
```

**ب) فحص Procfile:**
```
web: gunicorn finspilot.wsgi:application
```

**ج) فحص runtime.txt:**
```
python-3.11.6
```

### 2. مشكلة قاعدة البيانات (Database Connection Error)

#### الأعراض:
- رسائل خطأ في الاتصال بقاعدة البيانات
- "could not connect to server"

#### الحلول:

**أ) فحص متغيرات البيئة:**
```bash
# تأكد من DATABASE_URL صحيح
DATABASE_URL=postgresql://username:password@hostname:port/database_name
```

**ب) فحص حالة قاعدة البيانات:**
1. اذهب إلى لوحة تحكم قاعدة البيانات
2. تأكد من أنها تعمل (Status: Available)
3. تحقق من الشبكة والاتصال

**ج) إعادة تطبيق الهجرات:**
```bash
# في Render Shell
python manage.py migrate --run-syncdb
```

### 3. مشكلة الملفات الثابتة (Static Files)

#### الأعراض:
- CSS و JavaScript لا يعمل
- الصفحات تظهر بدون تنسيق

#### الحلول:

**أ) جمع الملفات الثابتة:**
```bash
# في Render Shell
python manage.py collectstatic --noinput
```

**ب) فحص إعدادات STATIC:**
```python
# في settings.py
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

**ج) فحص Middleware:**
```python
MIDDLEWARE = [
    # ...
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # ...
]
```

### 4. مشكلة ALLOWED_HOSTS

#### الأعراض:
- رسالة "DisallowedHost"
- التطبيق لا يفتح

#### الحل:
```bash
# أضف هذا لمتغيرات البيئة
ALLOWED_HOSTS=your-app-name.onrender.com,localhost
```

### 5. مشكلة CORS

#### الأعراض:
- أخطاء CORS في المتصفح
- طلبات AJAX فاشلة

#### الحل:
```bash
# أضف هذا لمتغيرات البيئة
CORS_ALLOWED_ORIGINS=https://your-app-name.onrender.com
```

### 6. مشكلة انتهاء الذاكرة (Memory Limit)

#### الأعراض:
- التطبيق يتوقف فجأة
- رسائل "out of memory"

#### الحلول:

**أ) ترقية الخطة:**
- انتقل لخطة مدفوعة بذاكرة أكبر

**ب) تحسين الكود:**
```python
# تحسين استعلامات قاعدة البيانات
# استخدام select_related و prefetch_related
# تجنب تحميل بيانات كبيرة دفعة واحدة
```

### 7. مشكلة البيئة الافتراضية

#### الأعراض:
- خطأ في تثبيت المكتبات
- conflict في الإصدارات

#### الحل:
```bash
# إنشاء requirements.txt جديد
pip freeze > requirements.txt

# أو تحديد إصدارات محددة
Django>=4.2,<5.0
```

### 8. مشكلة الهجرات

#### الأعراض:
- خطأ في تطبيق الهجرات
- تضارب في الهجرات

#### الحلول:

**أ) إعادة تطبيق الهجرات:**
```bash
python manage.py migrate --fake-initial
python manage.py migrate
```

**ب) حل تضارب الهجرات:**
```bash
python manage.py makemigrations --merge
python manage.py migrate
```

### 9. مشكلة متغيرات البيئة

#### الأعراض:
- خطأ في قراءة الإعدادات
- قيم افتراضية خاطئة

#### الحل:
```bash
# تأكد من إعداد جميع المتغيرات المطلوبة:
SECRET_KEY=your-secret-key
DEBUG=False
DATABASE_URL=postgresql://...
ALLOWED_HOSTS=your-app.onrender.com
RENDER=True
```

### 10. مشكلة SSL/HTTPS

#### الأعراض:
- تحذيرات أمان
- مشاكل في تسجيل الدخول

#### الحل:
```python
# في settings.py للإنتاج
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## 🛠️ أدوات التشخيص

### 1. فحص سجلات النشر
```bash
# في Render Dashboard
Events → Deploy Logs
```

### 2. فحص سجلات التطبيق
```bash
# في Render Dashboard  
Logs → Runtime Logs
```

### 3. فحص Shell
```bash
# في Render Dashboard
Shell → Connect
python manage.py shell
```

### 4. فحص حالة قاعدة البيانات
```bash
# في قاعدة البيانات
Connect → Info
```

---

## 🚀 نصائح للأداء

### 1. تحسين قاعدة البيانات
```python
# استخدام connection pooling
DATABASES = {
    'default': dj_database_url.config(
        conn_max_age=600,  # إعادة استخدام الاتصالات
        conn_health_checks=True,
    )
}
```

### 2. تحسين الملفات الثابتة
```python
# ضغط الملفات الثابتة
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

### 3. تحسين الذاكرة
```python
# في settings.py
# تقليل حجم الجلسات
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600  # ساعة واحدة
```

---

## 📞 الحصول على المساعدة

### 1. وثائق Render
- https://render.com/docs

### 2. مجتمع Render
- https://community.render.com

### 3. الدعم الفني
- dashboard.render.com → Help

### 4. حالة الخدمة
- https://status.render.com

---

## 🔍 سجل المشاكل المحلولة

### التحديث الأخير: 2025-01-21

- ✅ حل مشكلة ALLOWED_HOSTS
- ✅ إعداد WhiteNoise للملفات الثابتة
- ✅ تحسين إعدادات قاعدة البيانات
- ✅ إضافة إعدادات أمان HTTPS
- ✅ حل مشكلة CORS

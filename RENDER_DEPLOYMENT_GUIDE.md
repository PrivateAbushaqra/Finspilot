# نشر مشروع Finspilot على Render.com

## ✅ **المتطلبات المسبقة**

### 1. **حساب على Render.com**
- اذهب إلى [render.com](https://render.com) وقم بإنشاء حساب
- اربط حسابك مع GitHub

### 2. **Repository على GitHub**
- تأكد من أن مشروعك موجود على GitHub
- تأكد من أن جميع الملفات محدثة:
  - `render.yaml`
  - `requirements.txt`
  - `finspilot/settings.py`
  - `.env` (للتطوير المحلي فقط)

## 🚀 **خطوات النشر**

### **الخطوة 1: إنشاء Web Service**
1. في لوحة Render، اضغط **"New"** → **"Web Service"**
2. اختر **"Connect GitHub"** وحدد repository مشروعك
3. املأ التفاصيل:
   - **Name**: `finspilot`
   - **Environment**: `Python 3`
   - **Region**: `Oregon` (أو أقرب منطقة لك)
   - **Branch**: `main`
   - **Build Command**: `python -m pip install --upgrade pip setuptools wheel && pip install -r requirements.txt && python manage.py migrate --noinput && python manage.py collectstatic --noinput`
   - **Start Command**: `gunicorn finspilot.wsgi:application --bind 0.0.0.0:$PORT`

### **الخطوة 2: إنشاء قاعدة البيانات PostgreSQL**
1. اضغط **"New"** → **"PostgreSQL"**
2. املأ التفاصيل:
   - **Name**: `finspilot-db`
   - **Database**: `finspilot`
   - **User**: `admin`
   - **Region**: نفس منطقة Web Service
   - **Plan**: ابدأ بـ Free أو Starter

### **الخطوة 3: ربط قاعدة البيانات**
1. في Web Service، اذهب إلى **"Environment"**
2. تأكد من وجود المتغيرات التالية (سيتم إنشاؤها تلقائياً):
   ```
   PG_NAME=finspilot
   PG_USER=admin
   PG_PASSWORD=[generated]
   PG_HOST=[generated]
   PG_PORT=5432
   RENDER=True
   ```

### **الخطوة 4: النشر**
1. اضغط **"Create Web Service"**
2. انتظر حتى يكتمل البناء (قد يستغرق 10-15 دقيقة)
3. ستحصل على رابط مثل: `https://finspilot.onrender.com`

## 🔍 **التحقق من استخدام PostgreSQL**

### **بعد النشر - تأكيد استخدام PostgreSQL**

#### **1. صفحة معلومات قاعدة البيانات**
- اذهب إلى: `https://your-app-name.onrender.com/ar/database-info/`
- ستجد صفحة تعرض:
  - ✅ نوع قاعدة البيانات: PostgreSQL
  - ✅ اسم قاعدة البيانات
  - ✅ المضيف والمنفذ
  - ✅ حالة الاتصال: متصل
  - ✅ نشر على Render: نعم

#### **2. التحقق عبر Django Shell**
```bash
# في Render SSH أو عبر python manage.py shell
from django.db import connection
print(connection.vendor)  # يجب أن يطبع: postgresql
print(connection.settings_dict['NAME'])  # اسم قاعدة البيانات
```

#### **3. استخدام سكريبت الفحص**
```bash
# محلياً
python check_database.py

# أو على Render عبر SSH
python check_database.py
```

### **ما يجب أن تراه:**
```
🚀 Finspilot - فحص قاعدة البيانات
==================================================
🔍 فحص قاعدة البيانات...
==================================================
نوع قاعدة البيانات: postgresql
اسم قاعدة البيانات: finspilot
المضيف: [render-postgres-host]
المنفذ: 5432
محرك قاعدة البيانات: django.db.backends.postgresql
==================================================
✅ ممتاز! التطبيق يستخدم PostgreSQL
✅ هذا يعني أن النشر على Render.com سيكون مع PostgreSQL أيضاً

🔗 اختبار الاتصال...
✅ الاتصال بقاعدة البيانات ناجح

==================================================
🎉 كل شيء يعمل بشكل صحيح!
🎉 التطبيق جاهز للنشر على Render.com مع PostgreSQL
```

### **إذا لم يعمل:**
- تحقق من متغيرات البيئة على Render
- تأكد من ربط قاعدة البيانات
- راجع logs البناء والتشغيل
- تأكد من أن `RENDER=True` مُعيّن

## ⚠️ **مشاكل شائعة وحلولها**

### **خطأ في البناء:**
```
Build failed
```
**الحل:**
- تحقق من `requirements.txt`
- تأكد من أن `render.yaml` صحيح
- راجع logs البناء

### **خطأ في قاعدة البيانات:**
```
Database connection failed
```
**الحل:**
- تأكد من أن قاعدة البيانات مربوطة
- تحقق من متغيرات البيئة
- راجع logs الخادم

### **خطأ 500:**
```
Internal Server Error
```
**الحل:**
- تحقق من `DEBUG=False` في الإنتاج
- راجع logs الخادم
- تأكد من تطبيق migrations

## 🔧 **إعدادات إضافية**

### **Domain مخصص:**
1. في Web Service → **Settings** → **Custom Domain**
2. أضف domainك واتبع التعليمات

### **SSL Certificate:**
- Render يوفر SSL تلقائياً ✅

### **Environment Variables إضافية:**
```yaml
- key: DJANGO_SETTINGS_MODULE
  value: finspilot.settings
- key: SECRET_KEY
  generateValue: true
- key: DEBUG
  value: False
- key: ALLOWED_HOSTS
  value: your-domain.com
```

## 📊 **التكاليف**

- **Web Service**: Free tier متاح
- **PostgreSQL**: Free tier متاح (حتى 750 ساعات/شهر)
- **Domain**: مجاني مع Render

## 🎯 **بعد النشر**

1. **إنشاء مستخدم Admin:**
   ```bash
   heroku run python manage.py createsuperuser
   ```

2. **نسخ احتياطي:**
   - Render يوفر automated backups

3. **Monitoring:**
   - استخدم Render's built-in monitoring
   - راجع logs بانتظام

## 🚨 **ملاحظات مهمة**

- **Free Tier Limitations**: قد يدخل في sleep mode بعد 15 دقيقة عدم نشاط
- **Cold Starts**: قد يستغرق التحميل الأول وقتاً أطول
- **File Uploads**: استخدم cloud storage للملفات الكبيرة

## 📞 **دعم فني**

إذا واجهت مشاكل:
1. راجع [Render Documentation](https://docs.render.com)
2. تحقق من [Django Deployment Guide](https://docs.djangoproject.com/en/stable/howto/deployment/)
3. استخدم Render's support

---

**تهانينا! مشروعك الآن على السحابة! 🎉**
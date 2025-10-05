# دليل نشر Finspilot على Render.com

## 📋 **المتطلبات الأساسية**

- حساب على [Render.com](https://render.com)
- حساب على [GitHub](https://github.com)
- مشروع Finspilot مرفوع على GitHub

## 🚀 **خطوات النشر**

### **الخطوة 1: رفع الكود إلى GitHub**

1. ارفع مشروع Finspilot إلى GitHub:
```bash
git add .
git commit -m "إعداد للنشر على Render"
git push origin main
```

### **الخطوة 2: إنشاء قاعدة بيانات PostgreSQL**

1. اذهب إلى [Render Dashboard](https://dashboard.render.com)
2. اضغط على **"New"** → **"PostgreSQL"**
3. أدخل التفاصيل:
   - **Name**: `finspilot-db` (أو أي اسم تفضله)
   - **Database**: `finspilot_prod`
   - **User**: `finspilot_user`
4. اضغط **"Create Database"**
5. انتظر حتى تكتمل الإنشاء (يستغرق 2-3 دقائق)
6. احفظ **"Internal Database URL"** - ستحتاجه لاحقاً

### **الخطوة 3: إنشاء Web Service**

1. في Render Dashboard، اضغط **"New"** → **"Web Service"**
2. اربط مع repository الخاص بك على GitHub
3. أدخل التفاصيل:
   - **Name**: `finspilot` (أو أي اسم تفضله)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn finspilot.wsgi:application --bind 0.0.0.0:$PORT`

### **الخطوة 4: إعداد متغيرات البيئة**

أضف المتغيرات التالية في قسم **"Environment"**:

#### **متغيرات أساسية:**
```
DEBUG=False
SECRET_KEY=your-super-secret-key-here
RENDER=True
USE_LOCAL_POSTGRES=False
DEFAULT_CURRENCY=JOD
```

#### **متغير قاعدة البيانات:**
```
DATABASE_URL=postgresql://finspilot_user:your-password@your-host:5432/finspilot_prod
```
*(استبدل your-password و your-host بالقيم من قاعدة البيانات)*

#### **متغيرات الأمان:**
```
ALLOWED_HOSTS=your-app-name.onrender.com
RENDER_EXTERNAL_URL=https://your-app-name.onrender.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### **الخطوة 5: النشر**

1. اضغط **"Create Web Service"**
2. انتظر اكتمال البناء والنشر (يستغرق 5-10 دقائق)
3. ستحصل على رابط التطبيق: `https://your-app-name.onrender.com`

## 🔧 **استكشاف الأخطاء**

### **خطأ في قاعدة البيانات:**
- تأكد من صحة `DATABASE_URL`
- تأكد من أن قاعدة البيانات PostgreSQL نشطة

### **خطأ في التبعيات:**
- تأكد من أن `requirements.txt` محدث
- تأكد من استخدام Python 3.11+

### **خطأ في ALLOWED_HOSTS:**
- أضف نطاق Render في `ALLOWED_HOSTS`

## ✅ **التحقق من النجاح**

### **1. صفحة معلومات قاعدة البيانات**
- اذهب إلى: `https://your-app-name.onrender.com/ar/database-info/`
- يجب أن ترى:
  - ✅ نوع قاعدة البيانات: PostgreSQL
  - ✅ حالة الاتصال: متصل
  - ✅ نشر على Render: نعم

### **2. إنشاء مستخدم Admin**
```bash
# في Render Shell أو محلياً
python manage.py createsuperuser
```

### **3. إنشاء البيانات التجريبية**
```bash
# في Render Shell
python manage.py shell -c "from create_full_sample_data import *; create_sample_data()"
```

## 🔄 **التحديثات المستقبلية**

لتحديث التطبيق:
1. ارفع التغييرات إلى GitHub
2. Render سيقوم بالنشر التلقائي
3. أو اضغط **"Manual Deploy"** في لوحة التحكم

## 📞 **الدعم**

إذا واجهت مشاكل:
1. تحقق من logs في Render Dashboard
2. تأكد من إعدادات البيئة
3. تحقق من اتصال قاعدة البيانات

---

**تم إعداد هذا الدليل بواسطة فريق Finspilot** 🚀
# إعداد PostgreSQL محلي لمشروع Finspilot

## الوضع الحالي
✅ PostgreSQL مثبت على النظام  
❌ يحتاج إعداد كلمة مرور للمستخدم postgres

## المتطلبات
- PostgreSQL 17+ مثبت على النظام ✅
- خدمة PostgreSQL تعمل ✅

## خطوات الإعداد

### 1. تعيين كلمة مرور للمستخدم postgres
```bash
# افتح pgAdmin أو psql كمسؤول
psql -U postgres

# في psql، أدخل:
\password postgres
# أدخل كلمة مرور جديدة (مثل: postgres123)
# أعد إدخالها للتأكيد
\q
```

### 2. إنشاء قاعدة البيانات
```bash
createdb -U postgres finspilot_local
```

### 3. تحديث ملف .env
```env
USE_LOCAL_POSTGRES=True
LOCAL_PG_NAME=finspilot_local
LOCAL_PG_USER=postgres
LOCAL_PG_PASSWORD=postgres123  # كلمة المرور التي حددتها
LOCAL_PG_HOST=localhost
LOCAL_PG_PORT=5432
```

### 4. تطبيق migrations
```bash
python manage.py migrate
```

### 5. نقل البيانات (إذا كانت موجودة)
```bash
python manage.py loaddata backup_data.json
```

## استكشاف الأخطاء

### خطأ: fe_sendauth: no password supplied
```bash
# تحتاج لتعيين كلمة مرور للمستخدم postgres
psql -U postgres
\password postgres
# أدخل كلمة مرور
```

### خطأ: authentication failed
```bash
# تأكد من كلمة المرور في .env
# أو جرب:
psql -U postgres -h localhost -d postgres
```

### خطأ: database doesn't exist
```bash
createdb -U postgres finspilot_local
```

## البدائل

### استخدام SQLite (مؤقتاً)
```env
USE_LOCAL_POSTGRES=False
```

### استخدام Render.com (للإنتاج)
التطبيق جاهز للعمل مع PostgreSQL على Render.com ✅

## اختبار الإعداد
```bash
python manage.py check
python manage.py runserver
```
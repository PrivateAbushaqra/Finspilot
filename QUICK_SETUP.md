# تعليمات سريعة - إعداد قاعدة بيانات جديدة

## 🚀 الإعداد السريع (للمبتدئين)

### الخطوة 1: إعداد قاعدة بيانات جديدة
```powershell
# تشغيل سكريبت الإعداد الشامل
.\setup_database.ps1 -ResetDatabase

# أو استخدام السكريبت البسيط
.\setup_system.ps1 -FullSetup
```

### الخطوة 2: تشغيل النظام
```powershell
python manage.py runserver
```

### الخطوة 3: تسجيل الدخول
- **العنوان المحلي**: http://127.0.0.1:8000/admin/
- **العنوان على Render**: https://your-app-name.onrender.com/admin/
- **اسم المستخدم**: superadmin
- **كلمة المرور**: password

---

## 🌐 نشر التطبيق على Render.com

### تحضير النشر
```powershell
# فحص جاهزية المشروع
python check_deployment_readiness.py

# رفع الكود إلى GitHub
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

### خطوات النشر
1. **راجع دليل النشر الشامل**: `RENDER_DEPLOYMENT_GUIDE.md`
2. **أنشئ قاعدة بيانات PostgreSQL** في Render
3. **أنشئ Web Service** واربطه بـ GitHub
4. **أعد إعداد متغيرات البيئة**
5. **انشر التطبيق**
6. **شغّل سكريبت الإعداد الأولي**

---

## 🔄 تصدير واستيراد البيانات

### تصدير البيانات الحالية
```powershell
# تصدير نسخة احتياطية آمنة
python export_database.py
```

### استيراد البيانات لقاعدة جديدة
```powershell
# إعداد قاعدة جديدة مع استيراد البيانات
.\setup_database.ps1 -ResetDatabase -ImportData -BackupFile "finspilot_clean_backup_YYYYMMDD_HHMMSS.json"
```

---

## 🛠️ إعداد متقدم (للمطورين)

### حذف قاعدة البيانات الحالية
```powershell
Remove-Item "db.sqlite3" -Force
Get-ChildItem -Recurse -Directory -Name "migrations" | ForEach-Object {
    Get-ChildItem -Path $_ -Include "*.py" -Exclude "__init__.py" | Remove-Item -Force
}
```

### إنشاء هجرات جديدة
```powershell
python manage.py makemigrations
```

### تطبيق الهجرات بالترتيب
```powershell
# الهجرات الأساسية
python manage.py migrate contenttypes
python manage.py migrate auth
python manage.py migrate sessions  
python manage.py migrate admin

# هجرات التطبيقات
python manage.py migrate users
python manage.py migrate core
python manage.py migrate settings
python manage.py migrate
```

### إنشاء البيانات الأساسية
```powershell
python create_superadmin.py
python create_default_currencies.py
python create_default_groups.py
python create_default_accounts.py
```

---

## 📋 قائمة التحقق

### ✅ قبل البدء
- [ ] Python 3.11+ مثبت
- [ ] البيئة الافتراضية نشطة
- [ ] المكتبات مثبتة (`pip install -r requirements.txt`)

### ✅ بعد الإعداد
- [ ] قاعدة البيانات موجودة (`db.sqlite3`)
- [ ] الهجرات مطبقة (`python manage.py showmigrations`)
- [ ] المستخدم الرئيسي موجود (superadmin)
- [ ] العملات الافتراضية موجودة
- [ ] الحسابات المحاسبية موجودة

### ✅ اختبار النظام
- [ ] الخادم يعمل (`python manage.py runserver`)
- [ ] تسجيل الدخول ناجح
- [ ] لوحة التحكم تعمل
- [ ] إنشاء فاتورة تجريبية

---

## 🆘 حل المشاكل الشائعة

### مشكلة: "No module named 'django'"
```powershell
# تفعيل البيئة الافتراضية
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### مشكلة: "Database is locked"
```powershell
# إغلاق جميع اتصالات قاعدة البيانات
# إيقاف الخادم وإعادة تشغيله
```

### مشكلة: "Migration conflicts"
```powershell
# حذف الهجرات المتضاربة وإعادة إنشائها
.\setup_database.ps1 -ResetDatabase
```

### مشكلة: "Permission denied"
```powershell
# تشغيل PowerShell كمدير
# أو تغيير سياسة التنفيذ
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📞 الدعم

للحصول على مساعدة مفصلة، راجع:
- **`DATABASE_SETUP_GUIDE.md`** - دليل شامل
- **`DB_INFO_SUMMARY.txt`** - معلومات قاعدة البيانات
- **`README.md`** - معلومات المشروع

---

## ⚡ نصائح سريعة

1. **استخدم النسخة المنظفة عند الاستيراد** (`finspilot_clean_backup_*.json`)
2. **غيّر كلمة مرور superadmin فوراً بعد التثبيت**
3. **قم بنسخة احتياطية قبل أي تغييرات مهمة**
4. **استخدم PostgreSQL في الإنتاج بدلاً من SQLite**
5. **فعّل نظام انتهاء الجلسة للأمان**

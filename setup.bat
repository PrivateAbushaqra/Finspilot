@echo off
echo ===============================================
echo        Finspilot - نظام المحاسبة المتكامل
echo ===============================================
echo.

echo تجهيز النظام...

echo.
echo [1/6] التحقق من Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo خطأ: Python غير مثبت. يرجى تثبيت Python 3.8 أو أحدث
    pause
    exit /b 1
)
echo ✓ Python مثبت

echo.
echo [2/6] إنشاء البيئة الافتراضية...
if exist .venv (
    echo ✓ البيئة الافتراضية موجودة مسبقاً
) else (
    python -m venv .venv
    echo ✓ تم إنشاء البيئة الافتراضية
)

echo.
echo [3/6] تفعيل البيئة الافتراضية...
call .venv\Scripts\activate
echo ✓ تم تفعيل البيئة الافتراضية

echo.
echo [4/6] تثبيت المتطلبات...
pip install -r requirements.txt
if errorlevel 1 (
    echo خطأ في تثبيت المتطلبات
    pause
    exit /b 1
)
echo ✓ تم تثبيت جميع المتطلبات

echo.
echo [5/6] إعداد قاعدة البيانات...
python manage.py makemigrations
if errorlevel 1 (
    echo خطأ في إنشاء ملفات الهجرة
    pause
    exit /b 1
)

python manage.py migrate
if errorlevel 1 (
    echo خطأ في تطبيق قاعدة البيانات
    echo.
    echo تأكد من:
    echo 1. تثبيت PostgreSQL
    echo 2. إنشاء قاعدة البيانات Finspilot
    echo 3. إنشاء المستخدم admin3 بكلمة مرور pass
    echo.
    echo يمكنك استخدام ملف database_setup.sql لإنشاء قاعدة البيانات
    pause
    exit /b 1
)
echo ✓ تم إعداد قاعدة البيانات

echo.
echo [6/6] إنشاء البيانات الأولية...
python manage.py setup_initial_data
if errorlevel 1 (
    echo خطأ في إنشاء البيانات الأولية
    pause
    exit /b 1
)
echo ✓ تم إنشاء البيانات الأولية

echo.
echo ===============================================
echo           تم تجهيز النظام بنجاح! ✓
echo ===============================================
echo.
echo بيانات تسجيل الدخول:
echo.
echo ┌─────────────────────────────────────────┐
echo │ Super Admin:                            │
echo │   اسم المستخدم: superadmin              │
echo │   كلمة المرور: password                 │
echo │                                         │
echo │ Admin:                                  │
echo │   اسم المستخدم: admin                   │
echo │   كلمة المرور: admin                    │
echo └─────────────────────────────────────────┘
echo.
echo لتشغيل النظام:
echo   1. شغل الملف run.bat
echo   2. أو استخدم الأمر: python manage.py runserver
echo.
echo ثم افتح المتصفح على العنوان:
echo   http://127.0.0.1:8000
echo.
echo ===============================================

pause

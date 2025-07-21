@echo off
echo ===============================================
echo        Finspilot - نظام المحاسبة المتكامل
echo ===============================================
echo.

echo تشغيل النظام...

if not exist finspilot_env (
    echo خطأ: البيئة الافتراضية غير موجودة
    echo يرجى تشغيل setup.bat أولاً
    pause
    exit /b 1
)

echo تفعيل البيئة الافتراضية...
call finspilot_env\Scripts\activate

echo.
echo تشغيل خادم Django...
echo.
echo النظام متاح على العنوان: http://127.0.0.1:8000
echo اضغط Ctrl+C لإيقاف الخادم
echo.

python manage.py runserver

pause

@echo off
REM سكريبت Windows للتحقق من قاعدة البيانات
echo 🚀 Finspilot - فحص قاعدة البيانات
echo.

REM تفعيل البيئة الافتراضية
call .venv\Scripts\activate.bat

REM تشغيل سكريبت الفحص
python check_database.py

REM إيقاف البيئة الافتراضية
deactivate

echo.
echo اضغط أي مفتاح للمتابعة...
pause > nul
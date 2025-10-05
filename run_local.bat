@echo off
REM Batch script لتشغيل مشروع Finspilot محلياً
echo 🚀 تشغيل مشروع Finspilot محلياً...
echo.

REM تشغيل الخادم
echo 📡 بدء تشغيل خادم Django على http://0.0.0.0:8000
echo لإيقاف الخادم اضغط Ctrl+C
echo.
.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
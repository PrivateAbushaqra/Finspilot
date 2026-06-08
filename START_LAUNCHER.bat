@echo off
chcp 65001 >nul 2>&1
color 0B
title FinsPilot-ERP - Launcher

cls
echo.
echo ═══════════════════════════════════════════════════════════════════
echo.
echo           🚀  FinsPilot-ERP - Modern Launcher  🚀
echo.
echo ═══════════════════════════════════════════════════════════════════
echo.
echo    📦  Starting the graphical interface...
echo    📦  جاري تشغيل الواجهة الرسومية...
echo.
echo ═══════════════════════════════════════════════════════════════════
echo.
timeout /t 2 /nobreak >nul

REM تحديد مسار البرنامج
SET "PROGRAM_DIR=%~dp0"
cd /d "%PROGRAM_DIR%"

REM البحث عن البيئة الافتراضية
SET "VENV_PYTHON="

IF EXIST "%PROGRAM_DIR%.venv-1\Scripts\pythonw.exe" (
    SET "VENV_PYTHON=%PROGRAM_DIR%.venv-1\Scripts\pythonw.exe"
    echo    ✅  Found Python environment: .venv-1
) ELSE IF EXIST "%PROGRAM_DIR%.venv\Scripts\pythonw.exe" (
    SET "VENV_PYTHON=%PROGRAM_DIR%.venv\Scripts\pythonw.exe"
    echo    ✅  Found Python environment: .venv
) ELSE IF EXIST "%PROGRAM_DIR%venv\Scripts\pythonw.exe" (
    SET "VENV_PYTHON=%PROGRAM_DIR%venv\Scripts\pythonw.exe"
    echo    ✅  Found Python environment: venv
) ELSE IF EXIST "%PROGRAM_DIR%venv_clean\Scripts\pythonw.exe" (
    SET "VENV_PYTHON=%PROGRAM_DIR%venv_clean\Scripts\pythonw.exe"
    echo    ✅  Found Python environment: venv_clean
) ELSE IF EXIST "%PROGRAM_DIR%.venv-1\Scripts\python.exe" (
    SET "VENV_PYTHON=%PROGRAM_DIR%.venv-1\Scripts\python.exe"
    echo    ✅  Found Python environment: .venv-1
) ELSE IF EXIST "%PROGRAM_DIR%.venv\Scripts\python.exe" (
    SET "VENV_PYTHON=%PROGRAM_DIR%.venv\Scripts\python.exe"
    echo    ✅  Found Python environment: .venv
) ELSE IF EXIST "%PROGRAM_DIR%venv\Scripts\python.exe" (
    SET "VENV_PYTHON=%PROGRAM_DIR%venv\Scripts\python.exe"
    echo    ✅  Found Python environment: venv
) ELSE IF EXIST "%PROGRAM_DIR%venv_clean\Scripts\python.exe" (
    SET "VENV_PYTHON=%PROGRAM_DIR%venv_clean\Scripts\python.exe"
    echo    ✅  Found Python environment: venv_clean
)

IF "%VENV_PYTHON%"=="" (
    where python >nul 2>&1
    IF %ERRORLEVEL%==0 (
        SET "VENV_PYTHON=python"
        echo    ✅  Using system Python from PATH
    )
)

IF "%VENV_PYTHON%"=="" (
    echo.
    echo    ❌  ERROR: Python virtual environment not found!
    echo    ❌  خطأ: لم يتم العثور على البيئة الافتراضية!
    echo.
    echo    📝  Please create a virtual environment first:
    echo    📝  الرجاء إنشاء بيئة افتراضية أولاً:
    echo.
    echo    python -m venv .venv-1
    echo    .venv-1\Scripts\activate
    echo    pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM التحقق من وجود ملف GUI
IF NOT EXIST "%PROGRAM_DIR%tools\pos_launcher_advanced.py" (
    echo.
    echo    ❌  ERROR: Launcher file not found!
    echo    ❌  خطأ: ملف التشغيل غير موجود!
    echo.
    echo    Expected: %PROGRAM_DIR%tools\pos_launcher_advanced.py
    echo.
    pause
    exit /b 1
)

echo.
echo    ✅  All checks passed!
echo    ✅  جميع الفحوصات نجحت!
echo.
echo    🚀  Launching GUI...
echo    🚀  تشغيل الواجهة الرسومية...
echo.
timeout /t 1 /nobreak >nul

REM تشغيل البرنامج
cd /d "%PROGRAM_DIR%"
start "" "%VENV_PYTHON%" "%PROGRAM_DIR%tools\pos_launcher_advanced.py"

echo    ✅  GUI launched successfully!
echo    ✅  تم تشغيل الواجهة بنجاح!
echo.
echo    💡  This window will close in 3 seconds...
echo    💡  ستغلق هذه النافذة خلال 3 ثوان...
echo.
timeout /t 3 /nobreak >nul
exit

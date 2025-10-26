@echo off
REM Finspilot Data Integrity Check Script
REM This script runs the scheduled integrity check for the accounting system

cd /d C:\Accounting_soft\finspilot

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

REM Run the integrity check
python manage.py scheduled_integrity_check

REM Log the execution
echo [%DATE% %TIME%] Integrity check completed >> integrity_check.log

pause
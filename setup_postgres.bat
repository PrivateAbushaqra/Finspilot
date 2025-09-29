@echo off
echo Setting up local PostgreSQL database for Finspilot...

REM Check if PostgreSQL is installed
where psql >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: PostgreSQL is not installed or not in PATH
    echo Please install PostgreSQL first from: https://www.postgresql.org/download/
    pause
    exit /b 1
)

REM Set PostgreSQL environment variables (adjust these as needed)
set PGHOST=localhost
set PGPORT=5432
set PGUSER=postgres

echo Please enter your PostgreSQL password when prompted...
echo Creating database 'finspilot_local'...

REM Create database
createdb -U postgres finspilot_local

if %errorlevel% equ 0 (
    echo SUCCESS: Database 'finspilot_local' created successfully!
    echo.
    echo Next steps:
    echo 1. Update your .env file with the correct PostgreSQL password
    echo 2. Set USE_LOCAL_POSTGRES=True in .env
    echo 3. Run: python manage.py migrate
    echo.
) else (
    echo ERROR: Failed to create database. Please check your PostgreSQL installation and credentials.
)

pause
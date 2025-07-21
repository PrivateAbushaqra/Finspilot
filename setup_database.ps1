# سكريبت إعداد قاعدة بيانات جديدة لنظام Finspilot المحاسبي
# PowerShell Script for Complete Database Setup

param(
    [switch]$ResetDatabase = $false,
    [switch]$ImportData = $false,
    [string]$BackupFile = ""
)

function Write-Header {
    param([string]$Title)
    Write-Host "=" * 70 -ForegroundColor Green
    Write-Host "  $Title" -ForegroundColor Green
    Write-Host "=" * 70 -ForegroundColor Green
}

function Write-Step {
    param([string]$Step, [int]$Number)
    Write-Host "`n[$Number] $Step" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

# التحقق من وجود Python و Django
function Test-Requirements {
    Write-Step "التحقق من المتطلبات الأساسية" 1
    
    try {
        $pythonVersion = python --version
        Write-Success "Python متوفر: $pythonVersion"
    }
    catch {
        Write-Error "Python غير مثبت أو غير متوفر في PATH"
        exit 1
    }
    
    try {
        python -c "import django; print(f'Django {django.get_version()}')"
        Write-Success "Django متوفر"
    }
    catch {
        Write-Error "Django غير مثبت"
        exit 1
    }
    
    # التحقق من البيئة الافتراضية
    if ($env:VIRTUAL_ENV) {
        Write-Success "البيئة الافتراضية نشطة: $env:VIRTUAL_ENV"
    } else {
        Write-Warning "لا توجد بيئة افتراضية نشطة"
        $response = Read-Host "هل تريد المتابعة؟ (y/n)"
        if ($response -ne 'y') {
            exit 1
        }
    }
}

# حذف قاعدة البيانات الحالية
function Reset-Database {
    Write-Step "حذف قاعدة البيانات الحالية" 2
    
    if (Test-Path "db.sqlite3") {
        Remove-Item "db.sqlite3" -Force
        Write-Success "تم حذف قاعدة البيانات القديمة"
    } else {
        Write-Warning "لا توجد قاعدة بيانات لحذفها"
    }
    
    # حذف ملفات الهجرات
    Write-Host "حذف ملفات الهجرات القديمة..."
    $migrationDirs = Get-ChildItem -Path . -Recurse -Directory -Name "migrations"
    
    foreach ($dir in $migrationDirs) {
        $migrationFiles = Get-ChildItem -Path $dir -Include "*.py" -Exclude "__init__.py"
        foreach ($file in $migrationFiles) {
            Remove-Item $file.FullName -Force
        }
    }
    Write-Success "تم حذف ملفات الهجرات القديمة"
}

# إنشاء الهجرات
function Create-Migrations {
    Write-Step "إنشاء الهجرات الجديدة" 3
    
    Write-Host "إنشاء هجرات جديدة..."
    $result = python manage.py makemigrations
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "تم إنشاء الهجرات بنجاح"
    } else {
        Write-Error "فشل في إنشاء الهجرات"
        Write-Host $result
        exit 1
    }
}

# تطبيق الهجرات
function Apply-Migrations {
    Write-Step "تطبيق الهجرات بالترتيب الصحيح" 4
    
    # الهجرات الأساسية
    Write-Host "تطبيق هجرات Django الأساسية..."
    python manage.py migrate contenttypes
    python manage.py migrate auth  
    python manage.py migrate sessions
    python manage.py migrate admin
    
    # هجرات التطبيقات الأساسية
    Write-Host "تطبيق هجرات التطبيقات الأساسية..."
    python manage.py migrate users
    python manage.py migrate core
    python manage.py migrate settings
    
    # باقي الهجرات
    Write-Host "تطبيق باقي الهجرات..."
    $result = python manage.py migrate
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "تم تطبيق جميع الهجرات بنجاح"
    } else {
        Write-Error "فشل في تطبيق الهجرات"
        exit 1
    }
}

# إنشاء البيانات الأساسية
function Create-DefaultData {
    Write-Step "إنشاء البيانات الأساسية" 5
    
    # إنشاء المستخدم الرئيسي
    Write-Host "إنشاء المستخدم الرئيسي..."
    python create_superadmin.py
    
    # إنشاء العملات
    Write-Host "إنشاء العملات الافتراضية..."
    python create_default_currencies.py
    
    # إنشاء المجموعات
    Write-Host "إنشاء المجموعات والصلاحيات..."
    python create_default_groups.py
    
    # إنشاء الحسابات المحاسبية
    Write-Host "إنشاء الحسابات المحاسبية..."
    python create_default_accounts.py
    
    Write-Success "تم إنشاء جميع البيانات الأساسية"
}

# جمع الملفات الثابتة
function Collect-StaticFiles {
    Write-Step "جمع الملفات الثابتة" 6
    
    $result = python manage.py collectstatic --noinput
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "تم جمع الملفات الثابتة بنجاح"
    } else {
        Write-Warning "تحذير في جمع الملفات الثابتة"
    }
}

# استيراد البيانات
function Import-BackupData {
    param([string]$BackupFilePath)
    
    if (-not $BackupFilePath) {
        Write-Warning "لم يتم تحديد ملف النسخة الاحتياطية"
        return
    }
    
    if (-not (Test-Path $BackupFilePath)) {
        Write-Error "ملف النسخة الاحتياطية غير موجود: $BackupFilePath"
        return
    }
    
    Write-Step "استيراد البيانات من النسخة الاحتياطية" 7
    
    Write-Host "استيراد البيانات من: $BackupFilePath"
    $result = python manage.py loaddata $BackupFilePath
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "تم استيراد البيانات بنجاح"
    } else {
        Write-Error "فشل في استيراد البيانات"
        Write-Host $result
    }
}

# التحقق من الإعداد
function Test-Setup {
    Write-Step "التحقق من نجاح الإعداد" 8
    
    Write-Host "فحص حالة الهجرات..."
    python manage.py showmigrations --plan | Out-Null
    
    Write-Host "فحص البيانات الأساسية..."
    $checkScript = @"
from users.models import User
from settings.models import Currency, CompanySettings  
from journal.models import Account

print(f'المستخدمين: {User.objects.count()}')
print(f'العملات: {Currency.objects.count()}')
print(f'الحسابات: {Account.objects.count()}')
print(f'إعدادات الشركة: {CompanySettings.objects.count()}')
"@
    
    $counts = python manage.py shell -c $checkScript
    Write-Host $counts
    
    Write-Success "تم التحقق من الإعداد بنجاح"
}

# الدالة الرئيسية
function Main {
    Write-Header "إعداد قاعدة بيانات جديدة - نظام Finspilot المحاسبي"
    
    # التحقق من المسار الحالي
    if (-not (Test-Path "manage.py")) {
        Write-Error "يجب تشغيل السكريبت من مجلد المشروع"
        exit 1
    }
    
    Test-Requirements
    
    if ($ResetDatabase) {
        Write-Warning "سيتم حذف قاعدة البيانات الحالية!"
        $confirm = Read-Host "هل أنت متأكد؟ (yes/no)"
        if ($confirm -ne "yes") {
            Write-Host "تم إلغاء العملية"
            exit 0
        }
        Reset-Database
    }
    
    Create-Migrations
    Apply-Migrations  
    Create-DefaultData
    Collect-StaticFiles
    
    if ($ImportData -and $BackupFile) {
        Import-BackupData $BackupFile
    }
    
    Test-Setup
    
    Write-Header "تم الانتهاء من إعداد قاعدة البيانات بنجاح!"
    
    Write-Host "`n🎉 قاعدة البيانات جاهزة للاستخدام!" -ForegroundColor Green
    Write-Host "`n📝 بيانات تسجيل الدخول:" -ForegroundColor Cyan
    Write-Host "   اسم المستخدم: superadmin" -ForegroundColor White
    Write-Host "   كلمة المرور: password" -ForegroundColor White
    Write-Host "`n🚀 لتشغيل الخادم:" -ForegroundColor Cyan  
    Write-Host "   python manage.py runserver" -ForegroundColor White
    Write-Host "`n⚠️  تذكر تغيير كلمة مرور المدير بعد تسجيل الدخول!" -ForegroundColor Yellow
}

# تشغيل السكريبت
try {
    Main
}
catch {
    Write-Error "حدث خطأ أثناء تشغيل السكريبت: $_"
    exit 1
}

# إعداد نظام المحاسبة Finspilot - نسخة محسّنة
# PowerShell Script

param(
    [switch]$FullSetup = $false,
    [switch]$SkipMigrations = $false
)

function Write-Header {
    param([string]$Title)
    Write-Host "=" * 60 -ForegroundColor Green
    Write-Host "  $Title" -ForegroundColor Green
    Write-Host "=" * 60 -ForegroundColor Green
}

function Write-Step {
    param([string]$Step, [int]$Number)
    Write-Host "`n[$Number] $Step" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

Write-Header "إعداد نظام المحاسبة Finspilot"

# التحقق من المتطلبات
Write-Step "التحقق من المتطلبات" 0
if (-not (Test-Path "manage.py")) {
    Write-Error "يجب تشغيل السكريبت من مجلد المشروع"
    exit 1
}

try {
    python --version | Out-Null
    Write-Success "Python متوفر"
} catch {
    Write-Error "Python غير متوفر"
    exit 1
}

if (-not $SkipMigrations) {
    Write-Step "إنشاء المهاجرات" 1
    $result = python manage.py makemigrations
    if ($LASTEXITCODE -eq 0) {
        Write-Success "تم إنشاء المهاجرات"
    } else {
        Write-Error "فشل في إنشاء المهاجرات"
        exit 1
    }

    Write-Step "تطبيق المهاجرات" 2
    $result = python manage.py migrate
    if ($LASTEXITCODE -eq 0) {
        Write-Success "تم تطبيق المهاجرات"
    } else {
        Write-Error "فشل في تطبيق المهاجرات"
        exit 1
    }
}

Write-Step "جمع الملفات الثابتة" 3
python manage.py collectstatic --noinput
Write-Success "تم جمع الملفات الثابتة"

Write-Step "إنشاء مستخدم المدير" 4
python create_superadmin.py
Write-Success "تم التحقق من مستخدم المدير"

Write-Step "إعداد العملات الافتراضية" 5
python create_default_currencies.py
Write-Success "تم إعداد العملات"

Write-Step "إنشاء المجموعات الافتراضية" 6
python create_default_groups.py
Write-Success "تم إنشاء المجموعات"

if ($FullSetup) {
    Write-Step "إنشاء الحسابات المحاسبية الافتراضية" 7
    python create_default_accounts.py
    Write-Success "تم إنشاء الحسابات المحاسبية"
}

Write-Header "تم الانتهاء من إعداد النظام بنجاح!"

Write-Host "`n🎉 النظام جاهز للاستخدام!" -ForegroundColor Green
Write-Host "`n📝 بيانات تسجيل الدخول:" -ForegroundColor Cyan
Write-Host "   اسم المستخدم: superadmin" -ForegroundColor White
Write-Host "   كلمة المرور: password" -ForegroundColor White
Write-Host "`n🚀 لتشغيل الخادم:" -ForegroundColor Cyan
Write-Host "   python manage.py runserver" -ForegroundColor White
Write-Host "`n📚 للمساعدة:" -ForegroundColor Cyan
Write-Host "   راجع ملف DATABASE_SETUP_GUIDE.md" -ForegroundColor White

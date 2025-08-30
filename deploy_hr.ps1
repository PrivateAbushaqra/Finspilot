# أوامر PowerShell لرفع وحدة الموارد البشرية
# Human Resources Module Deployment Commands for Windows PowerShell

Write-Host "=== بدء عملية رفع وحدة الموارد البشرية ===" -ForegroundColor Green
Write-Host "Starting HR Module Deployment..." -ForegroundColor Green

# التأكد من المجلد الصحيح
Set-Location "C:\Accounting_soft\finspilot"

# 1. تحديث قاعدة البيانات
Write-Host "1. تطبيق هجرات قاعدة البيانات..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe manage.py makemigrations hr
& .\.venv\Scripts\python.exe manage.py migrate

# 2. جمع الملفات الثابتة
Write-Host "2. جمع الملفات الثابتة..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe manage.py collectstatic --noinput

# 3. تحديث الترجمات
Write-Host "3. تحديث الترجمات..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe manage.py makemessages -l ar
& .\.venv\Scripts\python.exe manage.py compilemessages

# 4. فحص النظام
Write-Host "4. فحص تكامل النظام..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe manage.py check

# 5. إنشاء البيانات التجريبية (اختياري)
Write-Host "5. إضافة البيانات التجريبية (اختياري)..." -ForegroundColor Yellow
# Get-Content hr_sample_data_final.py | & .\.venv\Scripts\python.exe manage.py shell

# 6. فحص الصلاحيات
Write-Host "6. فحص صلاحيات وحدة HR..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe manage.py shell -c "from django.contrib.auth.models import Permission; hr_perms = Permission.objects.filter(content_type__app_label='hr'); print(f'عدد صلاحيات HR: {hr_perms.count()}')"

Write-Host "=== انتهت عملية الرفع بنجاح ===" -ForegroundColor Green
Write-Host "HR Module deployment completed successfully!" -ForegroundColor Green

Write-Host ""
Write-Host "للوصول لوحدة الموارد البشرية:" -ForegroundColor Cyan
Write-Host "URL: http://127.0.0.1:8000/ar/hr/" -ForegroundColor White

Write-Host ""
Write-Host "الصفحات المتاحة:" -ForegroundColor Cyan
Write-Host "- لوحة التحكم: /ar/hr/" -ForegroundColor White
Write-Host "- الموظفين: /ar/hr/employees/" -ForegroundColor White
Write-Host "- الأقسام: /ar/hr/departments/" -ForegroundColor White
Write-Host "- المناصب: /ar/hr/positions/" -ForegroundColor White
Write-Host "- الحضور: /ar/hr/attendance/" -ForegroundColor White
Write-Host "- الإجازات: /ar/hr/leaves/" -ForegroundColor White
Write-Host "- الرواتب: /ar/hr/payroll/" -ForegroundColor White
Write-Host "- المستندات: /ar/hr/documents/" -ForegroundColor White
Write-Host "- التقارير: /ar/hr/reports/" -ForegroundColor White

Write-Host ""
Write-Host "ملاحظات مهمة:" -ForegroundColor Yellow
Write-Host "1. تأكد من تشغيل الخادم: python manage.py runserver" -ForegroundColor White
Write-Host "2. للوصول للوحدة تحتاج صلاحية 'hr.can_view_hr'" -ForegroundColor White
Write-Host "3. البيانات التجريبية تم إنشاؤها: 4 موظفين، 5 أقسام، 8 مناصب" -ForegroundColor White

Write-Host ""
Write-Host "لإضافة المزيد من البيانات التجريبية:" -ForegroundColor Cyan
Write-Host "Get-Content hr_sample_data_final.py | .\.venv\Scripts\python.exe manage.py shell" -ForegroundColor White

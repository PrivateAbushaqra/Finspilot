# دليل الرفع السريع لوحدة الموارد البشرية
# Quick Deployment Guide for HR Module

## للرفع الفوري (Quick Deploy):
```bash
# Windows PowerShell
cd C:\Accounting_soft\finspilot
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py runserver
```

## للرفع الكامل (Full Deploy):
```bash
# تشغيل نص الرفع الكامل
cd C:\Accounting_soft\finspilot
powershell -ExecutionPolicy Bypass -File deploy_hr.ps1
```

## فحص النجاح:
```bash
# فحص البيانات
.\.venv\Scripts\python.exe manage.py shell -c "from hr.models import Employee; print(f'عدد الموظفين: {Employee.objects.count()}')"

# فحص الصفحات
curl http://127.0.0.1:8000/ar/hr/
curl http://127.0.0.1:8000/ar/hr/employees/
```

## الصفحات الرئيسية:
- لوحة التحكم: http://127.0.0.1:8000/ar/hr/
- الموظفين: http://127.0.0.1:8000/ar/hr/employees/
- الأقسام: http://127.0.0.1:8000/ar/hr/departments/
- الحضور: http://127.0.0.1:8000/ar/hr/attendance/

## الصلاحيات المطلوبة:
- hr.can_view_hr (للوصول الأساسي)
- hr.can_manage_employees (إدارة الموظفين)
- hr.can_manage_attendance (إدارة الحضور)
- hr.can_manage_payroll (إدارة الرواتب)
- hr.can_approve_leaves (الموافقة على الإجازات)

## ملفات تم إنشاؤها:
### النماذج والمنطق:
- hr/models.py (459 سطر)
- hr/views.py (700+ سطر)
- hr/forms.py (400+ سطر)
- hr/urls.py (100 سطر)
- hr/admin.py (مكتمل)

### القوالب:
- templates/hr/dashboard.html
- templates/hr/employee_list.html
- templates/hr/employee_detail.html
- templates/hr/employee_form.html
- templates/hr/attendance_list.html

### الإعدادات:
- تحديث finspilot/settings.py
- تحديث finspilot/urls.py
- تحديث templates/base.html

### البيانات التجريبية:
- hr_sample_data_final.py

### نصوص الرفع:
- deploy_hr.ps1 (PowerShell)
- deploy_hr.sh (Bash)

## حالة التطوير:
✅ النماذج (Models) - مكتمل 100%
✅ المشاهد (Views) - مكتمل 100%
✅ النماذج (Forms) - مكتمل 100%
✅ URLs - مكتمل 100%
✅ قاعدة البيانات - مكتمل 100%
✅ التكامل - مكتمل 100%
⚠️ القوالب - مكتمل 60% (الأساسيات جاهزة)
⚠️ الترجمات - مكتمل 80% (العربية جاهزة)

الوحدة جاهزة للاستخدام والاختبار!

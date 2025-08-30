#!/bin/bash

# أوامر الرفع لوحدة الموارد البشرية - نسخة PowerShell لـ Windows
# Human Resources Module Deployment Commands

echo "=== بدء عملية رفع وحدة الموارد البشرية ==="
echo "Starting HR Module Deployment..."

# 1. تحديث قاعدة البيانات
echo "1. تطبيق هجرات قاعدة البيانات..."
python manage.py makemigrations hr
python manage.py migrate

# 2. جمع الملفات الثابتة
echo "2. جمع الملفات الثابتة..."
python manage.py collectstatic --noinput

# 3. تحديث الترجمات
echo "3. تحديث الترجمات..."
python manage.py makemessages -l ar
python manage.py compilemessages

# 4. فحص النظام
echo "4. فحص تكامل النظام..."
python manage.py check

# 5. إنشاء البيانات التجريبية (اختياري)
echo "5. إضافة البيانات التجريبية (اختياري)..."
# python manage.py shell < hr_sample_data_final.py

# 6. إعادة تشغيل الخادم
echo "6. إعادة تشغيل خادم Django..."
# تحتاج لتشغيل هذا يدوياً: python manage.py runserver

echo "=== انتهت عملية الرفع بنجاح ==="
echo "HR Module deployment completed successfully!"

echo ""
echo "للوصول لوحدة الموارد البشرية:"
echo "URL: http://127.0.0.1:8000/ar/hr/"
echo ""
echo "الصفحات المتاحة:"
echo "- لوحة التحكم: /ar/hr/"
echo "- الموظفين: /ar/hr/employees/"
echo "- الأقسام: /ar/hr/departments/"
echo "- المناصب: /ar/hr/positions/"
echo "- الحضور: /ar/hr/attendance/"
echo "- الإجازات: /ar/hr/leaves/"
echo "- الرواتب: /ar/hr/payroll/"
echo "- المستندات: /ar/hr/documents/"
echo "- التقارير: /ar/hr/reports/"

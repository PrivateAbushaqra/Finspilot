#!/bin/bash

echo "==================================="
echo "إعداد نظام المحاسبة Finspilot"
echo "==================================="

echo "1. إنشاء المهاجرات..."
python manage.py makemigrations

echo "2. تطبيق المهاجرات..."
python manage.py migrate

echo "3. جمع الملفات الثابتة..."
python manage.py collectstatic --noinput

echo "4. إنشاء مستخدم المدير (إن لم يكن موجوداً)..."
python create_superadmin.py

echo "5. إعداد العملات الافتراضية..."
python create_default_currencies.py

echo "6. إنشاء المجموعات الافتراضية..."
python create_default_groups.py

echo "==================================="
echo "تم الانتهاء من إعداد النظام بنجاح!"
echo "يمكنك الآن تشغيل الخادم باستخدام:"
echo "python manage.py runserver"
echo "==================================="

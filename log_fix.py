#!/usr/bin/env python
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from core.models import AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()

# تسجيل الإصلاح في سجل الأنشطة
try:
    admin_user = User.objects.filter(username='admin').first() or User.objects.filter(is_superuser=True).first()
    
    if admin_user:
        AuditLog.objects.create(
            user=admin_user,
            action_type='update',
            content_type='CustomerSupplierTransactionsView',
            object_id=14,
            description='تم إصلاح عرض معاملات العميل لتشمل مردودات المشتريات من الموردين المرتبطين - تحسين استعلام Q objects',
            ip_address='127.0.0.1'
        )
        
        # تسجيل إنشاء معاملات مردود المشتريات
        AuditLog.objects.create(
            user=admin_user,
            action_type='create',
            content_type='AccountTransaction',
            object_id=0,
            description='تم إنشاء معاملات حساب ناقصة لمردودات المشتريات وربطها بالعملاء المناسبين',
            ip_address='127.0.0.1'
        )
        
        print("تم تسجيل الإصلاحات في سجل الأنشطة")
    else:
        print("لم يتم العثور على مستخدم مدير")
        
except Exception as e:
    print(f"خطأ في تسجيل النشاط: {e}")

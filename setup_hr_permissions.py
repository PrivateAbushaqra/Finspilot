#!/usr/bin/env python3
import os
import sys
import django

# إضافة مسار المشروع
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from users.models import User
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from hr.models import Employee

def create_hr_permissions():
    """إنشاء صلاحيات HR"""
    print("إنشاء صلاحيات الموارد البشرية...")
    
    # الحصول على content type لـ HR
    content_type = ContentType.objects.get_for_model(Employee)
    
    # صلاحيات HR
    permissions = [
        ('can_view_hr', 'Can view HR dashboard'),
        ('can_manage_employees', 'Can manage employees'),
        ('can_manage_payroll', 'Can manage payroll'),
        ('can_manage_attendance', 'Can manage attendance'),
        ('can_view_reports', 'Can view HR reports'),
    ]
    
    created_perms = []
    for codename, name in permissions:
        perm, created = Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={'name': name}
        )
        if created:
            created_perms.append(codename)
    
    if created_perms:
        print(f"تم إنشاء الصلاحيات: {', '.join(created_perms)}")
    else:
        print("جميع الصلاحيات موجودة مسبقاً")
    
    return True

def list_users():
    """عرض جميع المستخدمين"""
    print("\nالمستخدمون المتوفرون:")
    print("-" * 40)
    for user in User.objects.all():
        print(f"- {user.username} (superuser: {user.is_superuser})")
        if user.user_permissions.filter(codename__startswith='can_').exists():
            perms = user.user_permissions.filter(codename__startswith='can_').values_list('codename', flat=True)
            print(f"  الصلاحيات: {', '.join(perms)}")

def make_user_superuser(username):
    """جعل المستخدم super user"""
    try:
        user = User.objects.get(username=username)
        user.is_superuser = True
        user.is_staff = True
        user.save()
        print(f"تم جعل المستخدم {username} مدير نظام (superuser)")
        return True
    except User.DoesNotExist:
        print(f"المستخدم {username} غير موجود")
        return False

def give_hr_permissions(username):
    """إعطاء صلاحيات HR للمستخدم"""
    try:
        user = User.objects.get(username=username)
        content_type = ContentType.objects.get_for_model(Employee)
        
        # إعطاء صلاحية عرض HR
        perm = Permission.objects.get(codename='can_view_hr', content_type=content_type)
        user.user_permissions.add(perm)
        
        print(f"تم إعطاء صلاحيات HR للمستخدم {username}")
        return True
    except User.DoesNotExist:
        print(f"المستخدم {username} غير موجود")
        return False

if __name__ == '__main__':
    # إنشاء الصلاحيات
    create_hr_permissions()
    
    # عرض المستخدمين
    list_users()
    
    print("\n" + "="*50)
    print("لإعطاء صلاحيات HR لمستخدم معين:")
    print("python setup_hr_permissions.py give_permission اسم_المستخدم")
    print("\nلجعل مستخدم super user:")
    print("python setup_hr_permissions.py make_superuser اسم_المستخدم")
    
    # التحقق من المعاملات
    if len(sys.argv) > 2:
        action = sys.argv[1]
        username = sys.argv[2]
        
        if action == 'give_permission':
            give_hr_permissions(username)
        elif action == 'make_superuser':
            make_user_superuser(username)
        else:
            print("الأوامر المتاحة: give_permission, make_superuser")

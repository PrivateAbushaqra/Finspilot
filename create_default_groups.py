#!/usr/bin/env python
import os
import django
import sys

# إعداد Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'triangle.settings')
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

def create_default_groups():
    """إنشاء مجموعات افتراضية للنظام"""
    
    # المجموعات الافتراضية
    default_groups = [
        {
            'name': 'المدراء',
            'permissions': [
                'add_user', 'change_user', 'delete_user', 'view_user',
                'add_group', 'change_group', 'delete_group', 'view_group',
                'add_bank', 'change_bank', 'delete_bank', 'view_bank',
                'add_product', 'change_product', 'delete_product', 'view_product',
                'add_sale', 'change_sale', 'delete_sale', 'view_sale',
                'add_purchase', 'change_purchase', 'delete_purchase', 'view_purchase',
                'view_reports',
            ]
        },
        {
            'name': 'المحاسبين',
            'permissions': [
                'view_user',
                'add_bank', 'change_bank', 'view_bank',
                'add_sale', 'change_sale', 'view_sale',
                'add_purchase', 'change_purchase', 'view_purchase',
                'view_reports',
            ]
        },
        {
            'name': 'أمناء المخزن',
            'permissions': [
                'add_product', 'change_product', 'view_product',
                'view_inventory',
                'add_purchase', 'change_purchase', 'view_purchase',
            ]
        },
        {
            'name': 'البائعين',
            'permissions': [
                'add_sale', 'change_sale', 'view_sale',
                'view_product',
                'add_customer', 'change_customer', 'view_customer',
            ]
        },
        {
            'name': 'المستخدمين العاديين',
            'permissions': [
                'view_sale',
                'view_product',
                'view_customer',
            ]
        }
    ]
    
    print("إنشاء المجموعات الافتراضية...")
    
    for group_data in default_groups:
        group, created = Group.objects.get_or_create(name=group_data['name'])
        
        if created:
            print(f"تم إنشاء المجموعة: {group.name}")
        else:
            print(f"المجموعة موجودة مسبقاً: {group.name}")
        
        # إضافة الصلاحيات
        permissions = []
        for perm_codename in group_data['permissions']:
            try:
                perm = Permission.objects.get(codename=perm_codename)
                permissions.append(perm)
            except Permission.DoesNotExist:
                print(f"  - تحذير: الصلاحية '{perm_codename}' غير موجودة")
        
        group.permissions.set(permissions)
        print(f"  - تم تعيين {len(permissions)} صلاحية للمجموعة")
    
    print("\nتم إنشاء المجموعات الافتراضية بنجاح!")
    
    # عرض ملخص
    print("\nملخص المجموعات:")
    for group in Group.objects.all():
        print(f"- {group.name}: {group.permissions.count()} صلاحية")

if __name__ == '__main__':
    create_default_groups()

#!/usr/bin/env python
"""
إنشاء المستخدم superadmin المطلوب
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'triangle.settings')
django.setup()

from users.models import User

def create_superadmin():
    """إنشاء المستخدم superadmin"""
    
    if not User.objects.filter(username='superadmin').exists():
        user = User.objects.create_user(
            username='superadmin',
            email='superadmin@triangle.com',
            password='password',
            first_name='Super',
            last_name='Admin',
            user_type='superadmin',
            is_superuser=True,
            is_staff=True,
            can_access_sales=True,
            can_access_purchases=True,
            can_access_inventory=True,
            can_access_banks=True,
            can_access_reports=True,
            can_delete_invoices=True,
            can_edit_dates=True,
            can_edit_invoice_numbers=True,
            can_see_low_stock_alerts=True,
        )
        print(f'✓ تم إنشاء المستخدم: {user.username}')
        print(f'  - كلمة المرور: password')
    else:
        print('المستخدم superadmin موجود بالفعل')

if __name__ == '__main__':
    create_superadmin()

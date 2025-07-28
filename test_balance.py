#!/usr/bin/env python
"""اختبار ميزة عرض رصيد العميل/المورد"""

import os
import sys
import django
from pathlib import Path

# إضافة مجلد المشروع لمسار Python
project_path = Path(__file__).parent
sys.path.append(str(project_path))

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

# الآن يمكننا استيراد النماذج
from customers.models import CustomerSupplier

def test_customer_balance():
    """اختبار حساب رصيد العميل/المورد"""
    print("=== اختبار ميزة عرض رصيد العميل/المورد ===\n")
    
    customers = CustomerSupplier.objects.all()[:5]
    
    for customer in customers:
        print(f"العميل/المورد: {customer.name}")
        print(f"النوع: {customer.get_type_display()}")
        print(f"الرصيد المحفوظ: {customer.balance}")
        print(f"الرصيد الحالي: {customer.current_balance}")
        print("-" * 40)
    
    print("\n✅ تم اختبار الميزة بنجاح!")

if __name__ == "__main__":
    test_customer_balance()

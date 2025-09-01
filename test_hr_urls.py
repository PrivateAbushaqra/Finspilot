#!/usr/bin/env python
"""
سكريبت اختبار جميع روابط صفحات التقارير HR
"""
import os
import sys
import django
from django.test import Client
from django.contrib.auth.models import User

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

def test_hr_reports():
    """اختبار جميع صفحات التقارير HR"""
    
    # إنشاء عميل اختبار
    client = Client()
    
    # إنشاء مستخدم اختبار
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    # تسجيل الدخول
    client.login(username='testuser', password='testpass123')
    
    # قائمة URLs للاختبار
    test_urls = [
        '/ar/hr/reports/',
        '/ar/hr/reports/attendance/',
        '/ar/hr/reports/attendance/late/',
        '/ar/hr/reports/attendance/overtime/',
        '/ar/hr/reports/employees/',
        '/ar/hr/reports/employees/department/',
        '/ar/hr/reports/employees/new-hires/',
        '/ar/hr/reports/leave/summary/',
        '/ar/hr/reports/leave/balance/',
        '/ar/hr/reports/leave/upcoming/',
        '/ar/hr/reports/payroll/summary/',
        '/ar/hr/reports/payroll/breakdown/',
        '/ar/hr/reports/payroll/comparison/',
        '/ar/hr/reports/contracts/types/',
        '/ar/hr/reports/contracts/expiry/',
        '/ar/hr/reports/contracts/probation/',
        '/ar/hr/reports/performance/headcount/',
        '/ar/hr/reports/performance/turnover/',
        '/ar/hr/reports/performance/anniversary/',
    ]
    
    print("🔍 اختبار صفحات التقارير HR...")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for url in test_urls:
        try:
            response = client.get(url)
            if response.status_code == 200:
                print(f"✅ PASS - {url} - Status: 200")
                passed += 1
            else:
                print(f"❌ FAIL - {url} - Status: {response.status_code}")
                failed += 1
        except Exception as e:
            print(f"🚨 ERROR - {url} - Exception: {str(e)[:100]}")
            failed += 1
    
    print("=" * 60)
    print(f"📊 النتائج النهائية:")
    print(f"✅ تم اجتيازها: {passed}")
    print(f"❌ فشلت: {failed}")
    print(f"📈 نسبة النجاح: {(passed/(passed+failed)*100):.1f}%")
    
    return passed, failed

if __name__ == "__main__":
    test_hr_reports()

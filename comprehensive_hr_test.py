#!/usr/bin/env python
"""
اختبار شامل لجميع صفحات تقارير HR مع تسجيل الدخول
"""
import os
import sys
import django
from django.test import Client
from django.contrib.auth.models import User

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

def test_hr_reports_comprehensive():
    """اختبار شامل مع تسجيل الدخول"""
    
    print("=== اختبار شامل لصفحات تقارير HR ===\n")
    
    # إنشاء عميل اختبار
    client = Client()
    
    # البحث عن المستخدمين
    try:
        super_user = User.objects.get(username='super')
        print(f"✅ تم العثور على المستخدم super: {super_user.username}")
    except User.DoesNotExist:
        print("❌ لم يتم العثور على المستخدم super")
        return
    
    try:
        admin_user = User.objects.get(username='admin4')  
        print(f"✅ تم العثور على المستخدم admin4: {admin_user.username}")
    except User.DoesNotExist:
        print("❌ لم يتم العثور على المستخدم admin4")
        admin_user = super_user
    
    # تسجيل دخول بالمستخدم super
    client.force_login(super_user)
    print(f"🔐 تم تسجيل الدخول باستخدام: {super_user.username}\n")
    
    # قائمة الروابط المطلوب اختبارها
    test_urls = [
        # الروابط المحددة من المستخدم
        ('/ar/hr/reports/performance/headcount/', 'تقرير العدد الإجمالي'),
        ('/ar/hr/reports/payroll/summary/', 'ملخص الرواتب'),
        ('/ar/hr/reports/payroll/breakdown/', 'تفصيل الراتب'),
        ('/ar/hr/reports/performance/anniversary/', 'تقرير ذكرى العمل'),
        ('/ar/hr/reports/payroll/comparison/', 'مقارنة الرواتب'),
        
        # روابط إضافية للتأكد
        ('/ar/hr/reports/', 'الصفحة الرئيسية للتقارير'),
        ('/ar/hr/reports/attendance/', 'تقرير الحضور'),
        ('/ar/hr/reports/leave/upcoming/', 'الإجازات القادمة'),
        ('/ar/hr/reports/employees/department/', 'تقرير الأقسام'),
        ('/ar/hr/reports/employees/new-hires/', 'الموظفين الجدد'),
    ]
    
    print("🧪 بدء الاختبارات:")
    print("-" * 80)
    
    successful_tests = 0
    failed_tests = 0
    
    for i, (url, description) in enumerate(test_urls, 1):
        try:
            response = client.get(url)
            status_code = response.status_code
            
            if status_code == 200:
                print(f"{i:2d}. ✅ {description}")
                print(f"    📍 {url}")
                print(f"    📊 Status: {status_code} - نجح")
                
                # فحص محتوى الصفحة
                content = response.content.decode('utf-8', errors='ignore')
                if 'تقرير' in content or 'Reports' in content or 'table' in content.lower():
                    print(f"    📄 المحتوى: صفحة تحتوي على تقرير ✅")
                else:
                    print(f"    📄 المحتوى: صفحة لا تحتوي على تقرير ⚠️")
                
                successful_tests += 1
                
            elif status_code == 302:
                print(f"{i:2d}. 🔄 {description}")
                print(f"    📍 {url}")
                print(f"    📊 Status: {status_code} - إعادة توجيه")
                successful_tests += 1
                
            elif status_code == 404:
                print(f"{i:2d}. ❌ {description}")
                print(f"    📍 {url}")
                print(f"    📊 Status: {status_code} - الصفحة غير موجودة")
                failed_tests += 1
                
            elif status_code == 500:
                print(f"{i:2d}. ❌ {description}")
                print(f"    📍 {url}")
                print(f"    📊 Status: {status_code} - خطأ خادم")
                failed_tests += 1
                
            else:
                print(f"{i:2d}. ⚠️  {description}")
                print(f"    📍 {url}")
                print(f"    📊 Status: {status_code} - حالة غير متوقعة")
                failed_tests += 1
                
        except Exception as e:
            print(f"{i:2d}. 💥 {description}")
            print(f"    📍 {url}")
            print(f"    💀 خطأ: {str(e)[:100]}")
            failed_tests += 1
        
        print()
    
    print("=" * 80)
    print("📋 النتائج النهائية:")
    print(f"✅ اختبارات نجحت: {successful_tests}")
    print(f"❌ اختبارات فشلت: {failed_tests}")
    print(f"📊 معدل النجاح: {(successful_tests / len(test_urls)) * 100:.1f}%")
    
    if successful_tests == len(test_urls):
        print("🎉 جميع الاختبارات نجحت!")
    elif successful_tests >= len(test_urls) * 0.8:
        print("👍 معظم الاختبارات نجحت!")
    else:
        print("⚠️ يحتاج المزيد من الإصلاحات")
    
    return successful_tests, failed_tests

if __name__ == '__main__':
    test_hr_reports_comprehensive()

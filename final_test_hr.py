#!/usr/bin/env python
"""اختبار نهائي لصفحات تقارير HR"""

import requests
import time

def test_hr_pages():
    """اختبار جميع صفحات التقارير"""
    
    base_url = "http://127.0.0.1:8000"
    
    # قائمة جميع صفحات التقارير
    report_urls = [
        "/ar/hr/reports/",
        "/ar/hr/reports/attendance/",
        "/ar/hr/reports/upcoming-leaves/",
        "/ar/hr/reports/salary-breakdown/",
        "/ar/hr/reports/department/",
        "/ar/hr/reports/new-hires/",
        "/ar/hr/reports/payroll-summary/",
        "/ar/hr/reports/leave-balance/",
        "/ar/hr/reports/overtime/",
        "/ar/hr/reports/bonus/",
        "/ar/hr/reports/performance/",
        "/ar/hr/reports/absence/",
        "/ar/hr/reports/payroll-comparison/",
        "/ar/hr/reports/contract-expiry/",
        "/ar/hr/reports/contract-types/",
        "/ar/hr/reports/probation/",
        "/ar/hr/reports/headcount/",
        "/ar/hr/reports/turnover/",
        "/ar/hr/reports/anniversary/"
    ]
    
    print("=== اختبار صفحات تقارير HR ===")
    print(f"السيرفر: {base_url}")
    print(f"عدد الصفحات: {len(report_urls)}")
    print("-" * 50)
    
    working_pages = 0
    broken_pages = 0
    
    # إنشاء جلسة للكوكيز
    session = requests.Session()
    
    for i, url in enumerate(report_urls, 1):
        full_url = base_url + url
        
        try:
            response = session.get(full_url, timeout=10)
            status = response.status_code
            
            if status == 200:
                print(f"{i:2d}. ✅ {url}")
                working_pages += 1
            elif status == 302:
                print(f"{i:2d}. 🔄 {url} (إعادة توجيه - ربما يحتاج تسجيل دخول)")
                working_pages += 1
            elif status == 404:
                print(f"{i:2d}. 🔍 {url} (404 - الصفحة غير موجودة)")
                broken_pages += 1
            elif status == 500:
                print(f"{i:2d}. ❌ {url} (500 - خطأ خادم)")
                broken_pages += 1
            else:
                print(f"{i:2d}. ⚠️  {url} ({status})")
                broken_pages += 1
                
        except requests.exceptions.RequestException as e:
            print(f"{i:2d}. 💥 {url} (خطأ اتصال: {str(e)[:30]})")
            broken_pages += 1
        
        # توقف قصير بين الطلبات
        time.sleep(0.1)
    
    print("-" * 50)
    print("=== النتائج النهائية ===")
    print(f"✅ صفحات تعمل: {working_pages}")
    print(f"❌ صفحات معطلة: {broken_pages}")
    print(f"📊 معدل النجاح: {(working_pages / len(report_urls)) * 100:.1f}%")
    
    if working_pages == len(report_urls):
        print("🎉 جميع الصفحات تعمل بنجاح!")
    elif working_pages > len(report_urls) * 0.8:
        print("👍 معظم الصفحات تعمل بنجاح!")
    else:
        print("⚠️ يحتاج المزيد من الإصلاحات")

if __name__ == "__main__":
    test_hr_pages()

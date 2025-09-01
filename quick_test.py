#!/usr/bin/env python
"""اختبار سريع وبسيط للصفحات الخمس المطلوبة"""

import requests
import time

def test_final():
    """اختبار نهائي للصفحات الخمس"""
    
    base_url = "http://127.0.0.1:8000"
    
    pages = [
        ("تقرير العدد الإجمالي", "/ar/hr/reports/performance/headcount/"),
        ("ملخص الرواتب", "/ar/hr/reports/payroll/summary/"),
        ("تفصيل الراتب", "/ar/hr/reports/payroll/breakdown/"),
        ("تقرير ذكرى العمل", "/ar/hr/reports/performance/anniversary/"),
        ("مقارنة الرواتب", "/ar/hr/reports/payroll/comparison/")
    ]
    
    print("🧪 اختبار نهائي للصفحات الخمس المطلوبة")
    print("=" * 60)
    
    session = requests.Session()
    working = 0
    broken = 0
    
    for i, (name, url) in enumerate(pages, 1):
        full_url = base_url + url
        
        try:
            response = session.get(full_url, timeout=10)
            status = response.status_code
            
            if status == 200:
                print(f"{i}. ✅ {name} - يعمل بنجاح (200)")
                working += 1
            elif status == 302:
                print(f"{i}. 🔄 {name} - إعادة توجيه (302)")
                working += 1
            else:
                print(f"{i}. ❌ {name} - فشل ({status})")
                broken += 1
                
        except Exception as e:
            print(f"{i}. 💥 {name} - خطأ: {str(e)[:40]}")
            broken += 1
            
        time.sleep(0.5)
    
    print("=" * 60)
    print(f"✅ تعمل: {working}/5")
    print(f"❌ معطلة: {broken}/5")
    print(f"📊 معدل النجاح: {(working/5)*100:.0f}%")
    
    if working == 5:
        print("🎉 جميع الصفحات تعمل بنجاح!")
    else:
        print(f"⚠️ يحتاج إصلاح {broken} صفحة")

if __name__ == "__main__":
    test_final()

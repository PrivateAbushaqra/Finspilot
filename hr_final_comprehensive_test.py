#!/usr/bin/env python
"""اختبار نهائي شامل للتأكد من عمل جميع صفحات تقارير HR"""

import requests
import time
from datetime import datetime

def test_all_hr_pages():
    """اختبار شامل لجميع الصفحات"""
    
    base_url = "http://127.0.0.1:8000"
    
    # إنشاء جلسة
    session = requests.Session()
    
    # الصفحات المطلوب اختبارها
    test_pages = [
        {
            'url': '/ar/hr/reports/performance/headcount/',
            'name': 'تقرير العدد الإجمالي للموظفين',
            'priority': 'high'
        },
        {
            'url': '/ar/hr/reports/payroll/summary/',
            'name': 'ملخص الرواتب',
            'priority': 'high'
        },
        {
            'url': '/ar/hr/reports/payroll/breakdown/',
            'name': 'تفصيل تفكيك الراتب',
            'priority': 'high'
        },
        {
            'url': '/ar/hr/reports/performance/anniversary/',
            'name': 'تقرير ذكرى العمل',
            'priority': 'high'
        },
        {
            'url': '/ar/hr/reports/payroll/comparison/',
            'name': 'مقارنة الرواتب',
            'priority': 'high'
        },
        # صفحات إضافية للتأكد
        {
            'url': '/ar/hr/reports/',
            'name': 'الصفحة الرئيسية للتقارير',
            'priority': 'medium'
        },
        {
            'url': '/ar/hr/reports/attendance/',
            'name': 'تقرير الحضور',
            'priority': 'medium'
        }
    ]
    
    print(f"🕐 بدء الاختبار في: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print(f"🧪 اختبار {len(test_pages)} صفحة من تقارير HR")
    print("=" * 80)
    
    successful = 0
    failed = 0
    warnings = 0
    
    for i, page in enumerate(test_pages, 1):
        url = base_url + page['url']
        name = page['name']
        priority = page['priority']
        
        try:
            print(f"\n{i:2d}. اختبار: {name}")
            print(f"    🔗 {page['url']}")
            
            # إرسال الطلب
            response = session.get(url, timeout=15)
            status = response.status_code
            
            # تحليل النتيجة
            if status == 200:
                # فحص المحتوى
                content = response.content.decode('utf-8', errors='ignore')
                
                # التحقق من وجود أخطاء في المحتوى
                if 'error' in content.lower() or 'exception' in content.lower():
                    print(f"    ⚠️  تحذير: الصفحة تحتوي على أخطاء محتملة")
                    warnings += 1
                    if priority == 'high':
                        print(f"    🚨 أولوية عالية - يحتاج مراجعة فورية!")
                else:
                    print(f"    ✅ نجح - Status: {status}")
                    successful += 1
                    
            elif status == 302:
                print(f"    🔄 إعادة توجيه - Status: {status}")
                print(f"    📍 قد يحتاج تسجيل دخول")
                successful += 1
                
            elif status == 404:
                print(f"    ❌ فشل - الصفحة غير موجودة - Status: {status}")
                failed += 1
                if priority == 'high':
                    print(f"    🚨 أولوية عالية - مطلوب إصلاح فوري!")
                    
            elif status == 500:
                print(f"    ❌ فشل - خطأ خادم - Status: {status}")
                failed += 1
                if priority == 'high':
                    print(f"    🚨 أولوية عالية - مطلوب إصلاح فوري!")
                    
            else:
                print(f"    ⚠️  حالة غير متوقعة - Status: {status}")
                warnings += 1
                
        except requests.exceptions.Timeout:
            print(f"    ⏰ انتهت مهلة الاتصال")
            failed += 1
            
        except requests.exceptions.ConnectionError:
            print(f"    🔌 خطأ في الاتصال - تأكد من تشغيل السيرفر")
            failed += 1
            
        except Exception as e:
            print(f"    💥 خطأ غير متوقع: {str(e)[:50]}")
            failed += 1
            
        # توقف قصير بين الطلبات
        time.sleep(0.5)
    
    # النتائج النهائية
    print("\n" + "=" * 80)
    print("📊 النتائج النهائية:")
    print("=" * 80)
    print(f"✅ نجح: {successful}")
    print(f"⚠️  تحذيرات: {warnings}")
    print(f"❌ فشل: {failed}")
    print(f"📈 معدل النجاح: {(successful / len(test_pages)) * 100:.1f}%")
    
    # تقييم النتيجة
    if failed == 0 and warnings == 0:
        print("\n🎉 ممتاز! جميع الصفحات تعمل بشكل مثالي!")
        grade = "A+"
    elif failed == 0 and warnings <= 2:
        print("\n👍 جيد جداً! معظم الصفحات تعمل بنجاح مع تحذيرات قليلة")
        grade = "A"
    elif failed <= 2:
        print("\n👌 جيد! معظم الصفحات تعمل لكن هناك بعض المشاكل")
        grade = "B"
    else:
        print("\n⚠️ يحتاج المزيد من الإصلاحات")
        grade = "C"
    
    print(f"🏆 التقييم النهائي: {grade}")
    print(f"🕐 انتهى الاختبار في: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return successful, warnings, failed

if __name__ == "__main__":
    test_all_hr_pages()

#!/usr/bin/env python
"""
اختبار سريع لجميع صفحات التقارير HR
"""
import requests
from requests.sessions import Session

# URLs للاختبار
test_urls = [
    "http://127.0.0.1:8000/ar/hr/reports/",
    "http://127.0.0.1:8000/ar/hr/reports/attendance/",
    "http://127.0.0.1:8000/ar/hr/reports/leave/balance/",
    "http://127.0.0.1:8000/ar/hr/reports/attendance/late/",
    "http://127.0.0.1:8000/ar/hr/reports/employees/department/",
    "http://127.0.0.1:8000/ar/hr/reports/leave/upcoming/",
    "http://127.0.0.1:8000/ar/hr/reports/attendance/overtime/",
    "http://127.0.0.1:8000/ar/hr/reports/employees/new-hires/",
    "http://127.0.0.1:8000/ar/hr/reports/performance/headcount/",
    "http://127.0.0.1:8000/ar/hr/reports/contracts/expiry/",
    "http://127.0.0.1:8000/ar/hr/reports/payroll/summary/",
    "http://127.0.0.1:8000/ar/hr/reports/performance/turnover/",
    "http://127.0.0.1:8000/ar/hr/reports/contracts/types/",
    "http://127.0.0.1:8000/ar/hr/reports/payroll/breakdown/",
    "http://127.0.0.1:8000/ar/hr/reports/performance/anniversary/",
    "http://127.0.0.1:8000/ar/hr/reports/contracts/probation/",
    "http://127.0.0.1:8000/ar/hr/reports/payroll/comparison/",
]

def test_all_urls():
    session = Session()
    
    # محاولة تسجيل الدخول
    login_url = "http://127.0.0.1:8000/ar/auth/login/"
    login_data = {
        'username': 'super',
        'password': 'password',
        'csrfmiddlewaretoken': '',  # يحتاج للحصول عليه من النموذج
    }
    
    print("اختبار جميع صفحات التقارير...")
    print("=" * 50)
    
    for url in test_urls:
        try:
            response = session.get(url, timeout=10)
            status = "✅ يعمل" if response.status_code in [200, 302] else f"❌ خطأ {response.status_code}"
            print(f"{status} - {url}")
        except Exception as e:
            print(f"❌ خطأ - {url} - {str(e)}")
    
    print("=" * 50)
    print("انتهى الاختبار")

if __name__ == "__main__":
    test_all_urls()

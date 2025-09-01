#!/usr/bin/env python3
"""
تتبع مفصل لعملية تسجيل الدخول
"""

import requests
from bs4 import BeautifulSoup

def detailed_login_tracking():
    """تتبع مفصل لعملية تسجيل الدخول"""
    
    session = requests.Session()
    
    print("🔍 تتبع مفصل لعملية تسجيل الدخول")
    print("=" * 50)
    
    # الحصول على صفحة تسجيل الدخول العربية
    print("1. الوصول لصفحة تسجيل الدخول العربية...")
    login_page = session.get('http://127.0.0.1:8000/ar/auth/login/')
    print(f"   الاستجابة: {login_page.status_code}")
    print(f"   الرابط النهائي: {login_page.url}")
    
    if login_page.status_code == 200:
        soup = BeautifulSoup(login_page.text, 'html.parser')
        
        # البحث عن النموذج
        login_form = None
        forms = soup.find_all('form')
        for form in forms:
            # البحث عن نموذج تسجيل الدخول (يحتوي على username و password)
            if form.find('input', {'name': 'username'}) and form.find('input', {'name': 'password'}):
                login_form = form
                break
                
        if login_form:
            print(f"   تم العثور على نموذج تسجيل الدخول: {login_form.get('action', 'لا يوجد action')}")
            
            # البحث عن CSRF token
            csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            if csrf_input:
                csrf_token = csrf_input.get('value')
                print(f"   CSRF Token: {csrf_token[:20]}...")
                
                # تحضير بيانات النموذج
                login_data = {
                    'username': 'super',
                    'password': 'password',
                    'csrfmiddlewaretoken': csrf_token
                }
                
                print("2. إرسال بيانات تسجيل الدخول...")
                action_url = login_form.get('action') or '/ar/auth/login/'
                if not action_url.startswith('http'):
                    action_url = 'http://127.0.0.1:8000' + action_url
                
                print(f"   الإرسال إلى: {action_url}")
                
                # إرسال النموذج
                login_response = session.post(action_url, data=login_data, allow_redirects=False)
                print(f"   الاستجابة: {login_response.status_code}")
                
                # فحص الرؤوس
                print("   الرؤوس:")
                for header, value in login_response.headers.items():
                    if header.lower() in ['location', 'set-cookie']:
                        print(f"     {header}: {value}")
                
                if login_response.status_code == 302:
                    redirect_url = login_response.headers.get('location', '')
                    print(f"   إعادة التوجيه إلى: {redirect_url}")
                    
                    # تحويل الرابط النسبي إلى مطلق
                    if not redirect_url.startswith('http'):
                        redirect_url = 'http://127.0.0.1:8000' + redirect_url
                    
                    # تتبع إعادة التوجيه
                    print("3. تتبع إعادة التوجيه...")
                    final_response = session.get(redirect_url)
                    print(f"   الصفحة النهائية: {final_response.status_code}")
                    print(f"   الرابط النهائي: {final_response.url}")
                    
                    # فحص المحتوى
                    soup = BeautifulSoup(final_response.text, 'html.parser')
                    title = soup.find('title')
                    if title:
                        print(f"   العنوان: {title.get_text().strip()}")
                    
                    # البحث عن رسائل الخطأ
                    error_messages = soup.find_all(['div'], class_=['alert', 'error', 'message'])
                    if error_messages:
                        print("   رسائل الخطأ:")
                        for msg in error_messages:
                            print(f"     {msg.get_text().strip()}")
                    
                    # فحص المحتوى المرئي
                    visible_text = soup.get_text()
                    
                    # علامات نجاح تسجيل الدخول
                    success_indicators = ['لوحة التحكم', 'Dashboard', 'الرئيسية', 'تسجيل الخروج', 'Logout']
                    login_success = any(indicator in visible_text for indicator in success_indicators)
                    
                    if login_success:
                        print("✅ تم تسجيل الدخول بنجاح!")
                        
                        # الآن فحص المصطلحات الإنجليزية
                        print("4. فحص المصطلحات الإنجليزية...")
                        english_terms = [
                            'Dashboard', 'Home', 'Profile', 'Settings', 'Logout', 'Login',
                            'Add', 'Edit', 'Delete', 'Save', 'Cancel', 'Submit', 'Search',
                            'User', 'Admin', 'Account', 'System', 'Report', 'Invoice',
                            'Customer', 'Product', 'Sales', 'Purchase', 'Payment'
                        ]
                        
                        found_terms = []
                        for term in english_terms:
                            if term in visible_text:
                                count = visible_text.count(term)
                                found_terms.append(f"{term} ({count})")
                        
                        if found_terms:
                            print(f"❌ مصطلحات إنجليزية موجودة:")
                            for term in found_terms:
                                print(f"     - {term}")
                        else:
                            print("✅ لا توجد مصطلحات إنجليزية")
                        
                        # عرض جزء من المحتوى للمراجعة
                        print("\n📄 جزء من المحتوى (أول 800 حرف):")
                        print("-" * 50)
                        print(visible_text[:800])
                        print("-" * 50)
                        
                    else:
                        print("❌ فشل في تسجيل الدخول")
                        if 'تسجيل الدخول' in visible_text:
                            print("   المستخدم ما زال في صفحة تسجيل الدخول")
                            
                            # البحث عن رسائل خطأ في النموذج
                            form_errors = soup.find_all(['ul', 'div'], class_=['errorlist', 'errors'])
                            if form_errors:
                                print("   أخطاء النموذج:")
                                for error in form_errors:
                                    print(f"     {error.get_text().strip()}")
                            
                elif login_response.status_code == 200:
                    print("❌ لم تحدث إعادة توجيه - المحتوى:")
                    print(login_response.text[:500])
                else:
                    print(f"❌ خطأ غير متوقع: {login_response.status_code}")
                    
            else:
                print("❌ لم يتم العثور على CSRF token")
        else:
            print("❌ لم يتم العثور على نموذج تسجيل الدخول")
    else:
        print(f"❌ فشل في الوصول لصفحة تسجيل الدخول: {login_page.status_code}")

if __name__ == "__main__":
    detailed_login_tracking()

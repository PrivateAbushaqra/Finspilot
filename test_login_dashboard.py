#!/usr/bin/env python3
"""
اختبار تسجيل الدخول والوصول للوحة التحكم
"""

import requests
from bs4 import BeautifulSoup

def test_login_and_dashboard():
    """اختبار تسجيل الدخول والوصول للوحة التحكم"""
    
    session = requests.Session()
    
    print("🔐 اختبار تسجيل الدخول...")
    
    # الحصول على صفحة تسجيل الدخول
    login_page = session.get('http://127.0.0.1:8000/auth/login/')
    print(f"صفحة تسجيل الدخول: {login_page.status_code}")
    
    if login_page.status_code == 200:
        soup = BeautifulSoup(login_page.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        
        if csrf_input:
            csrf_token = csrf_input.get('value')
            print(f"CSRF Token: {csrf_token[:20]}...")
            
            # بيانات تسجيل الدخول
            login_data = {
                'username': 'super',
                'password': 'password',
                'csrfmiddlewaretoken': csrf_token
            }
            
            print("إرسال بيانات تسجيل الدخول...")
            login_response = session.post('http://127.0.0.1:8000/auth/login/', 
                                        data=login_data, 
                                        allow_redirects=False)
            
            print(f"استجابة تسجيل الدخول: {login_response.status_code}")
            
            if 'location' in login_response.headers:
                redirect_url = login_response.headers['location']
                print(f"إعادة التوجيه إلى: {redirect_url}")
                
                # تتبع إعادة التوجيه
                if not redirect_url.startswith('http'):
                    redirect_url = 'http://127.0.0.1:8000' + redirect_url
                    
                final_response = session.get(redirect_url)
                print(f"الصفحة النهائية: {final_response.status_code}")
                print(f"الرابط النهائي: {final_response.url}")
                
                # فحص المحتوى
                soup = BeautifulSoup(final_response.text, 'html.parser')
                title = soup.find('title')
                if title:
                    print(f"عنوان الصفحة: {title.get_text().strip()}")
                
                # البحث عن علامات تسجيل الدخول الناجح
                visible_text = soup.get_text()
                
                if 'لوحة التحكم' in visible_text or 'Dashboard' in visible_text:
                    print("✅ تم تسجيل الدخول بنجاح!")
                    
                    # البحث عن المصطلحات الإنجليزية
                    english_terms = ['Dashboard', 'Home', 'Profile', 'Settings', 'Logout', 
                                   'User', 'Admin', 'Account', 'System', 'Report']
                    
                    found_terms = []
                    for term in english_terms:
                        if term in visible_text:
                            found_terms.append(term)
                    
                    if found_terms:
                        print(f"❌ مصطلحات إنجليزية موجودة: {', '.join(found_terms)}")
                    else:
                        print("✅ لا توجد مصطلحات إنجليزية")
                        
                    # عرض جزء من المحتوى
                    print(f"\nجزء من المحتوى:")
                    print("-" * 50)
                    print(visible_text[:500])
                    
                else:
                    print("❌ فشل في تسجيل الدخول أو لم يتم الوصول للوحة التحكم")
                    print(f"المحتوى: {visible_text[:300]}")
            else:
                print("❌ لا توجد إعادة توجيه - فشل في تسجيل الدخول")
                print(f"المحتوى: {login_response.text[:300]}")
        else:
            print("❌ لم يتم العثور على CSRF token")
    else:
        print(f"❌ فشل في الوصول لصفحة تسجيل الدخول: {login_page.status_code}")

if __name__ == "__main__":
    test_login_and_dashboard()

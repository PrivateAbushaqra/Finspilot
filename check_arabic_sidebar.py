#!/usr/bin/env python3
"""
سكريبت لفحص النصوص الإنجليزية في الشريط الجانبي للصفحة العربية
"""
import os
import sys
import django
import requests
from bs4 import BeautifulSoup
import re

# إعداد Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

def login_and_check_sidebar():
    """تسجيل الدخول وفحص الشريط الجانبي"""
    
    # إنشاء جلسة
    session = requests.Session()
    
    # الحصول على صفحة تسجيل الدخول
    login_url = "http://127.0.0.1:8000/ar/auth/login/"
    response = session.get(login_url)
    
    if response.status_code != 200:
        print(f"خطأ في الوصول لصفحة تسجيل الدخول: {response.status_code}")
        return
    
    # استخراج CSRF token
    soup = BeautifulSoup(response.content, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
    
    if not csrf_token:
        print("لم يتم العثور على CSRF token")
        return
    
    csrf_value = csrf_token.get('value')
    
    # بيانات تسجيل الدخول
    login_data = {
        'username': 'super',
        'password': 'admin123',
        'csrfmiddlewaretoken': csrf_value
    }
    
    # تسجيل الدخول
    print("جاري تسجيل الدخول...")
    response = session.post(login_url, data=login_data)
    
    # فحص نجاح تسجيل الدخول
    if 'login' in response.url:
        print("فشل تسجيل الدخول - التحقق من بيانات الدخول")
        return
    
    print("تم تسجيل الدخول بنجاح!")
    
    # الوصول للصفحة الرئيسية العربية
    dashboard_url = 'http://127.0.0.1:8000/ar/'
    response = session.get(dashboard_url)
    
    if response.status_code != 200:
        print(f"خطأ في الوصول للصفحة الرئيسية: {response.status_code}")
        return
    
    # تحليل المحتوى
    soup = BeautifulSoup(response.content, 'html.parser')
    
    print("\n" + "="*50)
    print("فحص الشريط الجانبي للنصوص الإنجليزية")
    print("="*50)
    
    # البحث عن الشريط الجانبي
    sidebar = soup.find('nav', class_=lambda x: x and 'sidebar' in x.lower()) or \
              soup.find('div', class_=lambda x: x and 'sidebar' in x.lower()) or \
              soup.find('nav') or \
              soup.find('ul', class_='nav')
    
    if not sidebar:
        print("لم يتم العثور على الشريط الجانبي")
        # طباعة جزء من المحتوى للمساعدة في التشخيص
        print("\nمحتوى الصفحة (أول 1000 حرف):")
        print(soup.get_text()[:1000])
        return
    
    # البحث عن النصوص الإنجليزية في الشريط الجانبي
    english_texts = []
    
    # البحث عن جميع النصوص في الشريط الجانبي
    for element in sidebar.find_all(text=True):
        text = element.strip()
        if text and len(text) > 1:
            # فحص إذا كان النص يحتوي على أحرف إنجليزية
            if re.search(r'[A-Za-z]', text):
                # استبعاد الرموز والأيقونات
                if not re.match(r'^[^\w\s]*$', text):
                    english_texts.append(text)
    
    # إزالة التكرارات
    english_texts = list(set(english_texts))
    
    if english_texts:
        print(f"\nتم العثور على {len(english_texts)} نص إنجليزي:")
        print("-" * 30)
        for i, text in enumerate(english_texts, 1):
            print(f"{i}. {text}")
        
        # فحص محدد للنصوص المطلوبة
        print("\n" + "-" * 30)
        print("فحص النصوص المحددة:")
        
        target_texts = ['Bank Accounts', 'Global Search']
        for target in target_texts:
            found = any(target.lower() in text.lower() for text in english_texts)
            status = "✓ موجود" if found else "✗ غير موجود"
            print(f"- {target}: {status}")
            
    else:
        print("\nلم يتم العثور على نصوص إنجليزية في الشريط الجانبي")
    
    print("\n" + "="*50)
    print("انتهى الفحص")
    print("="*50)

if __name__ == "__main__":
    try:
        login_and_check_sidebar()
    except Exception as e:
        print(f"خطأ: {e}")
        import traceback
        traceback.print_exc()

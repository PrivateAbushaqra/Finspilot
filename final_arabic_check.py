#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import re

def check_final_arabic_texts():
    """Final check for Arabic sidebar texts with proper login"""
    
    session = requests.Session()
    login_url = "http://127.0.0.1:8000/ar/auth/login/"
    dashboard_url = "http://127.0.0.1:8000/ar/"
    
    # Get login page
    print("جاري الحصول على صفحة تسجيل الدخول...")
    response = session.get(login_url)
    
    if response.status_code != 200:
        print(f"خطأ في الوصول لصفحة تسجيل الدخول: {response.status_code}")
        return
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all forms and look for the login form (the one with username and password)
    forms = soup.find_all('form')
    login_form = None
    
    for form in forms:
        inputs = form.find_all('input')
        has_username = any(inp.get('name') == 'username' for inp in inputs)
        has_password = any(inp.get('type') == 'password' for inp in inputs)
        
        if has_username and has_password:
            login_form = form
            break
    
    if not login_form:
        print("لم يتم العثور على نموذج تسجيل الدخول")
        return
    
    print("تم العثور على نموذج تسجيل الدخول الصحيح")
    
    # Extract CSRF token
    csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
    if not csrf_input:
        print("لم يتم العثور على CSRF token")
        return
    
    csrf_token = csrf_input.get('value')
    print(f"تم استخراج CSRF token: {csrf_token[:20]}...")
    
    # Use the correct field names
    username_field = 'username'
    password_field = 'password'
    
    print(f"حقل اسم المستخدم: {username_field}")
    print(f"حقل كلمة المرور: {password_field}")
    
    # Prepare login data
    login_data = {
        username_field: 'super',
        password_field: 'admin123',
        'csrfmiddlewaretoken': csrf_token
    }
    
    print("جاري محاولة تسجيل الدخول...")
    response = session.post(login_url, data=login_data)
    
    print(f"استجابة تسجيل الدخول: {response.status_code}")
    
    # Check if login was successful by accessing dashboard
    response = session.get(dashboard_url)
    
    if response.status_code != 200:
        print(f"فشل الوصول للوحة القيادة: {response.status_code}")
        return
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Look for signs of successful login (like logout button or user menu)
    logout_link = soup.find('a', href=re.compile(r'logout'))
    user_menu = soup.find('a', string=re.compile(r'super|admin|المستخدم'))
    
    if logout_link or user_menu:
        print("✓ تم تسجيل الدخول بنجاح!")
    else:
        print("✗ فشل تسجيل الدخول")
        print("المحتوى المستلم:")
        print(soup.get_text()[:500] + "...")
        return
    
    # Now look for the sidebar or main navigation
    print("\nجاري البحث عن الشريط الجانبي أو القائمة الرئيسية...")
    
    # Try different selectors for sidebar
    possible_sidebars = [
        soup.find('nav', class_=re.compile(r'sidebar')),
        soup.find('div', class_=re.compile(r'sidebar')),
        soup.find('aside'),
        soup.find('div', id='sidebar'),
        soup.find('nav', id='sidebar')
    ]
    
    sidebar = None
    for potential_sidebar in possible_sidebars:
        if potential_sidebar:
            sidebar = potential_sidebar
            break
    
    if not sidebar:
        # Look for main navigation with many links
        print("لم يتم العثور على شريط جانبي، البحث عن القائمة الرئيسية...")
        all_navs = soup.find_all(['nav', 'div', 'ul'])
        for nav in all_navs:
            links = nav.find_all('a')
            if len(links) >= 8:  # Navigation with 8+ links is likely the main menu
                sidebar = nav
                print(f"تم العثور على قائمة رئيسية مع {len(links)} رابط")
                break
    
    if not sidebar:
        print("لم يتم العثور على أي قائمة تنقل رئيسية!")
        return
    
    print("تم العثور على القائمة الرئيسية!")
    print("="*50)
    
    # Extract all text from the sidebar and look for English texts
    sidebar_text = sidebar.get_text()
    english_texts = []
    
    # Split by lines and check each line
    lines = sidebar_text.split('\n')
    for line in lines:
        line = line.strip()
        if line and re.search(r'[A-Za-z]', line):
            # Check if it's mostly English (more than 50% English characters)
            english_chars = len(re.findall(r'[A-Za-z]', line))
            total_chars = len(re.sub(r'\s', '', line))
            if total_chars > 0 and english_chars / total_chars > 0.3:
                english_texts.append(line)
    
    print(f"تم العثور على {len(english_texts)} نص إنجليزي:")
    print("-" * 30)
    
    for i, text in enumerate(english_texts, 1):
        print(f"{i}. {text}")
    
    print("-" * 30)
    
    # Check specifically for our target texts
    sidebar_content = sidebar_text.lower()
    bank_accounts_found = 'bank accounts' in sidebar_content
    global_search_found = 'global search' in sidebar_content
    
    print(f"\nفحص النصوص المحددة:")
    print(f"- Bank Accounts: {'✓ موجود' if bank_accounts_found else '✗ غير موجود'}")
    print(f"- Global Search: {'✓ موجود' if global_search_found else '✗ غير موجود'}")
    
    print("\n" + "="*50)
    print("انتهى الفحص")
    print("="*50)
    
    return len(english_texts)

if __name__ == "__main__":
    check_final_arabic_texts()

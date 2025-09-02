#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import re

def final_comprehensive_check():
    """Final comprehensive check for English texts in Arabic sidebar"""
    
    session = requests.Session()
    login_url = "http://127.0.0.1:8000/ar/auth/login/"
    dashboard_url = "http://127.0.0.1:8000/ar/"
    
    print("🔍 الفحص النهائي الشامل للنصوص الإنجليزية في الشريط الجانبي العربي")
    print("="*70)
    
    # Step 1: Get login page and extract CSRF
    print("📄 الخطوة 1: جلب صفحة تسجيل الدخول...")
    response = session.get(login_url)
    
    if response.status_code != 200:
        print(f"❌ خطأ في الوصول لصفحة تسجيل الدخول: {response.status_code}")
        return 0
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find CSRF token from any form (they should all have the same token)
    csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
    if not csrf_input:
        print("❌ لم يتم العثور على CSRF token")
        return 0
    
    csrf_token = csrf_input.get('value')
    print(f"✅ تم استخراج CSRF token: {csrf_token[:20]}...")
    
    # Step 2: Login
    print("\n🔐 الخطوة 2: تسجيل الدخول...")
    login_data = {
        'username': 'super',
        'password': 'password',
        'csrfmiddlewaretoken': csrf_token
    }
    
    response = session.post(login_url, data=login_data, allow_redirects=True)
    print(f"📊 استجابة تسجيل الدخول: {response.status_code}")
    print(f"🔗 الرابط النهائي: {response.url}")
    
    # Step 3: Access dashboard
    print("\n🏠 الخطوة 3: الوصول للوحة القيادة...")
    response = session.get(dashboard_url)
    
    if response.status_code != 200:
        print(f"❌ فشل الوصول للوحة القيادة: {response.status_code}")
        return 0
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Check if login was successful
    logout_link = soup.find('a', href=re.compile(r'logout|auth/logout'))
    user_indicator = soup.find(string=re.compile(r'super|admin|مرحباً|أهلاً'))
    
    if logout_link or user_indicator:
        print("✅ تم تسجيل الدخول بنجاح!")
    else:
        print("❌ فشل تسجيل الدخول")
        print("🔍 محاولة البحث عن مؤشرات أخرى...")
        # Check page title
        title = soup.find('title')
        if title and 'login' not in title.get_text().lower():
            print("✅ تم تسجيل الدخول (بناءً على عنوان الصفحة)")
        else:
            return 0
    
    # Step 4: Find navigation/sidebar
    print("\n🧭 الخطوة 4: البحث عن الشريط الجانبي والقوائم...")
    
    # Try multiple methods to find the main navigation
    possible_sidebars = [
        soup.find('nav', class_=re.compile(r'sidebar|side-nav|main-nav')),
        soup.find('div', class_=re.compile(r'sidebar|side-nav|main-nav')),
        soup.find('aside'),
        soup.find(id=re.compile(r'sidebar|navigation|nav')),
        soup.find('ul', class_=re.compile(r'nav|menu')),
    ]
    
    sidebar = None
    for potential_sidebar in possible_sidebars:
        if potential_sidebar and len(potential_sidebar.find_all('a')) >= 5:
            sidebar = potential_sidebar
            break
    
    # If no sidebar found, look for any container with many navigation links
    if not sidebar:
        print("🔍 البحث عن أي حاوي يحتوي على روابط تنقل متعددة...")
        all_elements = soup.find_all(['div', 'nav', 'ul', 'section'])
        
        for element in all_elements:
            links = element.find_all('a')
            # Check if this element has many links that look like navigation
            nav_links = []
            for link in links:
                link_text = link.get_text().strip()
                if link_text and len(link_text) > 2 and len(link_text) < 50:
                    nav_links.append(link)
            
            if len(nav_links) >= 8:  # At least 8 navigation-like links
                sidebar = element
                print(f"✅ تم العثور على قائمة تنقل مع {len(nav_links)} رابط")
                break
    
    if not sidebar:
        print("❌ لم يتم العثور على شريط جانبي أو قائمة تنقل رئيسية!")
        print("🔍 عرض أول 1000 حرف من الصفحة للتشخيص:")
        print("-" * 50)
        print(soup.get_text()[:1000])
        print("-" * 50)
        return 0
    
    print("✅ تم العثور على القائمة الرئيسية!")
    
    # Step 5: Extract and analyze text
    print("\n📝 الخطوة 5: تحليل النصوص في القائمة...")
    
    # Get all text from sidebar
    sidebar_text = sidebar.get_text()
    
    # Find English texts
    english_texts = []
    
    # Method 1: Line by line analysis
    lines = sidebar_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if line contains English characters
        if re.search(r'[A-Za-z]', line):
            # Calculate ratio of English characters
            english_chars = len(re.findall(r'[A-Za-z]', line))
            total_chars = len(re.sub(r'\s+', '', line))
            
            if total_chars > 0 and english_chars / total_chars > 0.3:
                english_texts.append(line)
    
    # Method 2: Check individual links
    links = sidebar.find_all('a')
    for link in links:
        link_text = link.get_text().strip()
        if link_text and re.search(r'[A-Za-z]', link_text):
            english_chars = len(re.findall(r'[A-Za-z]', link_text))
            total_chars = len(re.sub(r'\s+', '', link_text))
            
            if total_chars > 0 and english_chars / total_chars > 0.3:
                if link_text not in english_texts:
                    english_texts.append(link_text)
    
    # Remove duplicates and clean up
    english_texts = list(set([text for text in english_texts if len(text.strip()) > 1]))
    english_texts.sort()
    
    # Step 6: Display results
    print(f"\n📊 النتائج النهائية:")
    print("="*50)
    print(f"🔢 عدد النصوص الإنجليزية المكتشفة: {len(english_texts)}")
    print("-"*30)
    
    if english_texts:
        for i, text in enumerate(english_texts, 1):
            print(f"{i:2d}. {text}")
    else:
        print("🎉 لا توجد نصوص إنجليزية! تم إكمال الترجمة بنسبة 100%!")
    
    print("-"*30)
    
    # Check specific target texts
    print(f"\n🎯 فحص النصوص المستهدفة:")
    sidebar_lower = sidebar_text.lower()
    
    bank_accounts_found = 'bank accounts' in sidebar_lower
    global_search_found = 'global search' in sidebar_lower
    
    print(f"- Bank Accounts: {'❌ موجود' if bank_accounts_found else '✅ مترجم'}")
    print(f"- Global Search: {'❌ موجود' if global_search_found else '✅ مترجم'}")
    
    # Final status
    if len(english_texts) == 0:
        print(f"\n🎉 تهانينا! تم إكمال الترجمة بنسبة 100%!")
        print(f"✅ جميع النصوص في الشريط الجانبي العربي أصبحت مترجمة!")
    else:
        completion_rate = max(0, 100 - (len(english_texts) * 5))  # Rough calculation
        print(f"\n📈 نسبة الإكمال: {completion_rate}%")
        print(f"🔄 يتبقى ترجمة {len(english_texts)} نص")
    
    print("="*70)
    print("انتهى الفحص النهائي")
    print("="*70)
    
    return len(english_texts)

if __name__ == "__main__":
    final_comprehensive_check()

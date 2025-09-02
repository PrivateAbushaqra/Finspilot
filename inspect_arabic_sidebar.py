#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import re

def inspect_arabic_sidebar():
    """Inspect the exact HTML structure of the Arabic sidebar"""
    
    session = requests.Session()
    login_url = "http://127.0.0.1:8000/ar/auth/login/"
    dashboard_url = "http://127.0.0.1:8000/ar/"
    
    # Get login page first
    print("جاري جلب صفحة تسجيل الدخول...")
    response = session.get(login_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract CSRF token
    csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
    if not csrf_input:
        print("لم يتم العثور على CSRF token")
        return
    csrf_token = csrf_input['value']
    
    # Login
    login_data = {
        'username': 'super',
        'password': 'admin123',
        'csrfmiddlewaretoken': csrf_token
    }
    
    print("جاري تسجيل الدخول...")
    response = session.post(login_url, data=login_data)
    
    if response.status_code == 200:
        print("تم تسجيل الدخول بنجاح!")
    else:
        print(f"فشل تسجيل الدخول: {response.status_code}")
        return
    
    # Get dashboard page
    print("جاري جلب صفحة لوحة القيادة...")
    response = session.get(dashboard_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the sidebar
    sidebar = soup.find('nav', class_='sidebar')
    if not sidebar:
        sidebar = soup.find('div', class_='sidebar')
    if not sidebar:
        sidebar = soup.find(id='sidebar')
    
    if sidebar:
        print("تم العثور على الشريط الجانبي!")
        print("="*60)
        print("محتوى الشريط الجانبي:")
        print("="*60)
        print(sidebar.prettify())
    else:
        print("لم يتم العثور على الشريط الجانبي!")
        
        # Let's search more broadly
        print("\nالبحث عن جميع عناصر التنقل والقوائم...")
        
        # Look for any element that might contain navigation
        all_possible_navs = soup.find_all(['nav', 'div', 'aside', 'ul'], class_=re.compile(r'sidebar|menu|nav|navigation|main-menu|side-menu', re.I))
        print(f"تم العثور على {len(all_possible_navs)} عنصر تنقل محتمل:")
        
        for i, nav in enumerate(all_possible_navs):
            print(f"\n--- عنصر تنقل {i+1} ---")
            print(f"Tag: {nav.name}, Class: {nav.get('class', [])}")
            print(nav.prettify()[:800] + "..." if len(str(nav)) > 800 else nav.prettify())
        
        # Also look for any div that contains many links
        print("\n\nالبحث عن القوائم التي تحتوي على روابط متعددة...")
        divs_with_links = soup.find_all('div')
        for div in divs_with_links:
            links = div.find_all('a')
            if len(links) >= 5:  # Divs with 5 or more links might be navigation
                print(f"\n--- عنصر يحتوي على {len(links)} رابط ---")
                print(f"Class: {div.get('class', [])}")
                print(div.prettify()[:800] + "..." if len(str(div)) > 800 else div.prettify())

if __name__ == "__main__":
    inspect_arabic_sidebar()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup

def try_different_credentials():
    """Try different username/password combinations"""
    
    # Common credentials to try
    credentials = [
        ('super', 'admin123'),
        ('admin', 'admin123'),
        ('super', 'password'),
        ('admin', 'password'),
        ('super', '123456'),
        ('admin', '123456'),
        ('super', 'super'),
        ('admin', 'admin'),
    ]
    
    session = requests.Session()
    login_url = "http://127.0.0.1:8000/ar/auth/login/"
    
    for username, password in credentials:
        print(f"جاري المحاولة: {username} / {password}")
        
        # Get fresh session for each attempt
        response = session.get(login_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if not csrf_input:
            print("  - لم يتم العثور على CSRF token")
            continue
        
        csrf_token = csrf_input.get('value')
        
        login_data = {
            'username': username,
            'password': password,
            'csrfmiddlewaretoken': csrf_token
        }
        
        response = session.post(login_url, data=login_data)
        
        # Check if we're redirected or if we see a different page
        if response.url != login_url:
            print(f"  ✓ نجح تسجيل الدخول! تم التوجيه إلى: {response.url}")
            return username, password, session
        
        # Check dashboard access
        dashboard_response = session.get("http://127.0.0.1:8000/ar/")
        soup = BeautifulSoup(dashboard_response.content, 'html.parser')
        
        # Look for signs of successful login
        if soup.find('a', href='/ar/auth/logout/') or soup.find(string=lambda text: text and username in text):
            print(f"  ✓ نجح تسجيل الدخول! المستخدم: {username}")
            return username, password, session
        else:
            print(f"  ✗ فشل تسجيل الدخول")
    
    print("فشل في جميع المحاولات")
    return None, None, None

if __name__ == "__main__":
    try_different_credentials()

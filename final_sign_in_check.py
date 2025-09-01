#!/usr/bin/env python3
"""
فحص نهائي للتأكد من عدم وجود "Sign In" في الصفحة
"""

import requests
from bs4 import BeautifulSoup
import re

def check_sign_in_completely():
    """فحص شامل للـ Sign In"""
    
    try:
        # طلب صفحة تسجيل الدخول
        url = 'http://127.0.0.1:8000/'
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ خطأ في الاتصال: {response.status_code}")
            return
            
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        print("=== فحص شامل لـ 'Sign In' ===")
        
        # 1. فحص في النص المرئي
        visible_text = soup.get_text()
        sign_in_count_visible = visible_text.count('Sign In')
        print(f"1. عدد 'Sign In' في النص المرئي: {sign_in_count_visible}")
        
        # 2. فحص في كامل HTML
        sign_in_count_html = html_content.count('Sign In')
        print(f"2. عدد 'Sign In' في كامل HTML: {sign_in_count_html}")
        
        # 3. فحص في العنوان title
        title = soup.find('title')
        if title and 'Sign In' in title.get_text():
            print("3. ❌ يوجد 'Sign In' في العنوان")
        else:
            print("3. ✅ لا يوجد 'Sign In' في العنوان")
            
        # 4. فحص في الأزرار
        buttons = soup.find_all('button')
        sign_in_buttons = 0
        for button in buttons:
            if 'Sign In' in button.get_text():
                sign_in_buttons += 1
                print(f"   ❌ زر يحتوي على 'Sign In': {button.get_text().strip()}")
                
        if sign_in_buttons == 0:
            print("4. ✅ لا توجد أزرار تحتوي على 'Sign In'")
        else:
            print(f"4. ❌ يوجد {sign_in_buttons} أزرار تحتوي على 'Sign In'")
            
        # 5. فحص input من نوع submit
        submit_inputs = soup.find_all('input', {'type': 'submit'})
        for inp in submit_inputs:
            if inp.get('value') and 'Sign In' in inp.get('value'):
                print(f"   ❌ input submit يحتوي على 'Sign In': {inp.get('value')}")
                
        # 6. البحث عن أي تاغ يحتوي على Sign In
        print("\n=== تفاصيل مواقع 'Sign In' ===")
        if 'Sign In' in html_content:
            lines = html_content.split('\n')
            for i, line in enumerate(lines, 1):
                if 'Sign In' in line:
                    print(f"السطر {i}: {line.strip()}")
                    
        # 7. الخلاصة
        print(f"\n=== الخلاصة ===")
        if sign_in_count_visible == 0:
            print("✅ لا يوجد 'Sign In' مرئي للمستخدم")
        else:
            print(f"❌ يوجد {sign_in_count_visible} مرة 'Sign In' مرئية للمستخدم")
            
        if sign_in_count_html == 0:
            print("✅ لا يوجد 'Sign In' في كامل HTML")
        else:
            print(f"❌ يوجد {sign_in_count_html} مرة 'Sign In' في HTML")
            
    except Exception as e:
        print(f"❌ خطأ في الفحص: {e}")

if __name__ == "__main__":
    check_sign_in_completely()

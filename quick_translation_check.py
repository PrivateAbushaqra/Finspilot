#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import sys
import os
from bs4 import BeautifulSoup
import re

def quick_check():
    """فحص سريع للمصطلحات الإنجليزية"""
    
    try:
        print("🔍 فحص سريع للترجمات...")
        
        # تسجيل الدخول
        session = requests.Session()
        login_url = 'http://127.0.0.1:8000/ar/auth/login/'
        
        print("📡 الاتصال بالخادم...")
        response = session.get(login_url)
        
        if response.status_code != 200:
            print(f"❌ خطأ في الاتصال: {response.status_code}")
            return
            
        # الحصول على CSRF token
        soup = BeautifulSoup(response.content, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
        
        # تسجيل الدخول
        login_data = {
            'username': 'super',
            'password': 'super',
            'csrfmiddlewaretoken': csrf_token
        }
        
        response = session.post(login_url, data=login_data)
        
        if 'ar/' in response.url:
            print("✅ تم تسجيل الدخول بنجاح")
            
            # فحص النص
            soup = BeautifulSoup(response.content, 'html.parser')
            text_content = soup.get_text()
            
            # البحث عن الكلمات الإنجليزية
            english_pattern = r'\b[A-Za-z]+\b'
            english_words = re.findall(english_pattern, text_content)
            
            # تصفية الكلمات الشائعة
            common_words = {'FinsPilot', 'CSRF', 'HTML', 'CSS', 'JS', 'Super', 'Administrator'}
            filtered_words = [word for word in english_words if word not in common_words and len(word) > 1]
            
            unique_words = list(set(filtered_words))
            
            print(f"📊 عدد الكلمات الإنجليزية المتبقية: {len(unique_words)}")
            print(f"📈 إجمالي التكرارات: {len(filtered_words)}")
            
            if unique_words:
                print("\n📝 عينة من الكلمات المتبقية:")
                for i, word in enumerate(unique_words[:20]):
                    count = filtered_words.count(word)
                    print(f"   {i+1}. {word} ({count} مرة)")
            else:
                print("🎉 لا توجد كلمات إنجليزية متبقية!")
        else:
            print("❌ فشل في تسجيل الدخول")
            
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")

if __name__ == "__main__":
    quick_check()

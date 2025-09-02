#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import time

def check_global_search_translation():
    """التحقق من ترجمة Global Search في النسخة العربية"""
    
    print("🔍 فحص ترجمة Global Search في النسخة العربية")
    print("=" * 50)
    
    try:
        # انتظار حتى يعمل الخادم
        time.sleep(3)
        
        session = requests.Session()
        
        # محاولة الوصول للصفحة العربية
        arabic_url = "http://127.0.0.1:8001/ar/"
        
        print(f"📡 محاولة الوصول إلى: {arabic_url}")
        
        response = session.get(arabic_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ تم الوصول للصفحة العربية بنجاح")
            
            # تحليل المحتوى
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # البحث عن النص في الشريط الجانبي
            search_links = soup.find_all('a', href='/ar/search/')
            
            if search_links:
                for link in search_links:
                    text_content = link.get_text(strip=True)
                    print(f"🔍 وجدت رابط البحث: '{text_content}'")
                    
                    if "البحث العام" in text_content:
                        print("✅ ممتاز! Global Search مترجم إلى 'البحث العام'")
                        return True
                    elif "Global Search" in text_content:
                        print("❌ المشكلة: لا يزال النص بالإنجليزية 'Global Search'")
                        return False
                    else:
                        print(f"⚠️ نص غير متوقع: '{text_content}'")
            else:
                print("❌ لم يتم العثور على رابط البحث")
                
            # البحث في جميع النصوص
            page_text = soup.get_text()
            if "البحث العام" in page_text:
                print("✅ 'البحث العام' موجود في الصفحة")
                return True
            elif "Global Search" in page_text:
                print("❌ 'Global Search' لا يزال موجود بالإنجليزية")
                return False
                
        else:
            print(f"❌ خطأ في الوصول للصفحة: كود الاستجابة {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ لا يمكن الوصول للخادم - تأكد من أن Django يعمل")
    except Exception as e:
        print(f"❌ خطأ: {e}")
    
    return False

if __name__ == "__main__":
    result = check_global_search_translation()
    if result:
        print("\n🎉 النتيجة: الترجمة تعمل بشكل صحيح!")
    else:
        print("\n⚠️ النتيجة: يحتاج إصلاح")

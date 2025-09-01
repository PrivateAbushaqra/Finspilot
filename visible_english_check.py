#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فحص مخصص للنصوص الإنجليزية المرئية فقط في النسخة العربية
Check only visible English texts in Arabic version
"""

import requests
import re
from bs4 import BeautifulSoup
import time

def check_visible_english_only():
    print("🔍 فحص النصوص الإنجليزية المرئية فقط في النسخة العربية...")
    print("=" * 60)
    
    try:
        time.sleep(2)
        response = requests.get('http://127.0.0.1:8000/ar/', timeout=10)
        
        # استخدام BeautifulSoup لتحليل HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # إزالة العناصر غير المرئية
        for script in soup(["script", "style", "meta", "link"]):
            script.decompose()
        
        # الحصول على النص المرئي فقط
        visible_text = soup.get_text()
        
        # تنظيف النص
        visible_text = re.sub(r'\s+', ' ', visible_text).strip()
        
        # المصطلحات الإنجليزية المهمة للواجهة
        critical_terms = [
            'Dashboard', 'Settings', 'Logout', 'Login',
            'Home', 'Profile', 'Reports', 'Admin',
            'Sales', 'Purchases', 'Inventory', 'Accounts',
            'Add', 'Edit', 'Delete', 'Save', 'Cancel',
            'Search', 'Filter', 'Export', 'Import'
        ]
        
        print(f"📄 النص المرئي: {len(visible_text):,} حرف")
        print(f"🔎 البحث عن {len(critical_terms)} مصطلحاً مهماً...")
        
        found_critical = {}
        
        for term in critical_terms:
            # البحث عن الكلمات الكاملة فقط
            pattern = r'\b' + re.escape(term) + r'\b'
            matches = re.findall(pattern, visible_text, re.IGNORECASE)
            if matches:
                found_critical[term] = len(matches)
        
        print("\n📊 النتائج:")
        print("-" * 40)
        
        if found_critical:
            print(f"⚠️ تم العثور على {len(found_critical)} مصطلحاً مهماً بالإنجليزية:")
            for term, count in found_critical.items():
                print(f"   • {term}: {count} مرة")
            
            # عرض جزء من النص حول كل مصطلح
            print("\n📝 السياق:")
            for term in found_critical.keys():
                pattern = r'.{0,50}\b' + re.escape(term) + r'\b.{0,50}'
                contexts = re.findall(pattern, visible_text, re.IGNORECASE)
                if contexts:
                    print(f"\n🔍 {term}:")
                    for i, context in enumerate(contexts[:3]):  # أول 3 فقط
                        print(f"   {i+1}. ...{context.strip()}...")
            
            return False
        else:
            print("✅ ممتاز! لا توجد مصطلحات إنجليزية مهمة مرئية")
            print("🎉 واجهة المستخدم العربية نظيفة!")
            return True
            
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return False
    
    finally:
        print("=" * 60)

def check_sidebar_specifically():
    """فحص مخصص للقائمة الجانبية تحديداً"""
    print("\n🎯 فحص مخصص للقائمة الجانبية...")
    print("-" * 40)
    
    try:
        response = requests.get('http://127.0.0.1:8000/ar/', timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن القائمة الجانبية
        sidebar = soup.find('div', class_='sidebar') or soup.find('nav', class_='sidebar')
        
        if sidebar:
            sidebar_text = sidebar.get_text()
            sidebar_text = re.sub(r'\s+', ' ', sidebar_text).strip()
            
            print(f"📋 نص القائمة الجانبية: {len(sidebar_text)} حرف")
            
            # المصطلحات المتوقعة في القائمة الجانبية
            sidebar_terms = ['Dashboard', 'Settings', 'Logout', 'Reports', 'Sales', 'Purchases']
            
            found_in_sidebar = []
            for term in sidebar_terms:
                if re.search(r'\b' + re.escape(term) + r'\b', sidebar_text, re.IGNORECASE):
                    found_in_sidebar.append(term)
            
            if found_in_sidebar:
                print(f"❌ مصطلحات إنجليزية في القائمة الجانبية: {', '.join(found_in_sidebar)}")
                print(f"📝 محتوى القائمة الجانبية:\n{sidebar_text[:500]}...")
                return False
            else:
                print("✅ القائمة الجانبية نظيفة من النصوص الإنجليزية")
                return True
        else:
            print("⚠️ لم يتم العثور على القائمة الجانبية")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في فحص القائمة الجانبية: {e}")
        return False

if __name__ == "__main__":
    visible_clean = check_visible_english_only()
    sidebar_clean = check_sidebar_specifically()
    
    print(f"\n🏆 النتيجة النهائية:")
    print(f"   النصوص المرئية: {'✅ نظيفة' if visible_clean else '❌ تحتاج إصلاح'}")
    print(f"   القائمة الجانبية: {'✅ نظيفة' if sidebar_clean else '❌ تحتاج إصلاح'}")
    
    if visible_clean and sidebar_clean:
        print("\n🎉 النسخة العربية نظيفة تماماً من النصوص الإنجليزية المرئية!")
    else:
        print("\n⚠️ يوجد نصوص إنجليزية مرئية تحتاج إلى إصلاح")
    
    exit(0 if (visible_clean and sidebar_clean) else 1)

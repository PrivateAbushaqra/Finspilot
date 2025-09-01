#!/usr/bin/env python3
"""
فحص شامل للصفحة العربية لتحديد جميع النصوص الإنجليزية
"""

import requests
from bs4 import BeautifulSoup
import json

def check_arabic_page_english_texts():
    """فحص شامل للنصوص الإنجليزية في الصفحة العربية"""
    
    try:
        # الوصول للصفحة العربية
        url = 'http://127.0.0.1:8000/ar/'
        
        # إعدادات الجلسة لتسجيل الدخول
        session = requests.Session()
        
        # الحصول على CSRF token
        login_page = session.get('http://127.0.0.1:8000/login/')
        soup = BeautifulSoup(login_page.text, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
        
        # تسجيل الدخول
        login_data = {
            'username': 'super',
            'password': 'password',
            'csrfmiddlewaretoken': csrf_token
        }
        
        login_response = session.post('http://127.0.0.1:8000/login/', data=login_data)
        
        # الوصول للصفحة العربية بعد تسجيل الدخول
        response = session.get(url, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ خطأ في الوصول للصفحة: {response.status_code}")
            return
            
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        print("=" * 80)
        print("🔍 فحص شامل للنصوص الإنجليزية في الصفحة العربية")
        print("=" * 80)
        print(f"📍 الرابط: {url}")
        print(f"📊 حالة الاستجابة: {response.status_code}")
        print(f"📄 حجم المحتوى: {len(html_content)} حرف")
        
        # استخراج النص المرئي
        visible_text = soup.get_text()
        print(f"📝 حجم النص المرئي: {len(visible_text)} حرف")
        
        # قائمة المصطلحات الإنجليزية للبحث عنها
        english_terms = [
            'Dashboard', 'Home', 'Profile', 'Settings', 'Logout', 'Login',
            'Add', 'Edit', 'Delete', 'Save', 'Cancel', 'Submit', 'Back',
            'Next', 'Previous', 'Search', 'Filter', 'Sort', 'Print',
            'Export', 'Import', 'Create', 'Update', 'View', 'Details',
            'User', 'Admin', 'Management', 'System', 'Report', 'Reports',
            'Account', 'Accounts', 'Invoice', 'Payment', 'Receipt',
            'Customer', 'Supplier', 'Product', 'Inventory', 'Sales',
            'Purchase', 'Revenue', 'Expense', 'Journal', 'Bank',
            'Cash', 'Asset', 'Liability', 'Equity', 'Balance',
            'Income', 'Statement', 'Total', 'Amount', 'Quantity',
            'Price', 'Date', 'Name', 'Description', 'Status',
            'Type', 'Category', 'Code', 'Number', 'ID', 'Reference',
            'From', 'To', 'Start', 'End', 'Today', 'Yesterday',
            'Week', 'Month', 'Year', 'Daily', 'Monthly', 'Yearly',
            'Success', 'Error', 'Warning', 'Info', 'Message',
            'Loading', 'Please wait', 'Processing', 'Complete',
            'Yes', 'No', 'OK', 'Cancel', 'Close', 'Open',
            'New', 'Old', 'Active', 'Inactive', 'Enabled', 'Disabled'
        ]
        
        # البحث عن المصطلحات الإنجليزية
        found_terms = {}
        total_english_words = 0
        
        for term in english_terms:
            count = visible_text.count(term)
            if count > 0:
                found_terms[term] = count
                total_english_words += count
        
        print("\n📊 النتائج:")
        print("-" * 50)
        
        if found_terms:
            print(f"❌ تم العثور على {len(found_terms)} مصطلحاً إنجليزياً:")
            print(f"📈 العدد الإجمالي للكلمات الإنجليزية: {total_english_words}")
            print("\n📝 التفاصيل:")
            
            for term, count in sorted(found_terms.items()):
                print(f"   • {term}: {count} مرة")
            
            print(f"\n🔴 الخلاصة: الصفحة العربية تحتوي على نصوص إنجليزية!")
        else:
            print("✅ ممتاز! لا توجد مصطلحات إنجليزية")
            print("🎉 الصفحة العربية نظيفة!")
        
        # فحص العناصر المهمة
        print("\n" + "=" * 50)
        print("🎯 فحص العناصر المهمة:")
        print("=" * 50)
        
        # العنوان
        title = soup.find('title')
        if title:
            title_text = title.get_text().strip()
            print(f"📋 العنوان: {title_text}")
            
        # القائمة الجانبية
        sidebar = soup.find('div', class_='sidebar') or soup.find('nav') or soup.find('div', {'id': 'sidebar'})
        if sidebar:
            sidebar_text = sidebar.get_text()
            print(f"📂 نص القائمة الجانبية ({len(sidebar_text)} حرف):")
            # طباعة أول 500 حرف من القائمة الجانبية
            print(f"   {sidebar_text[:500]}...")
        
        # المحتوى الرئيسي
        main_content = soup.find('main') or soup.find('div', class_='content') or soup.find('div', {'id': 'content'})
        if main_content:
            main_text = main_content.get_text()
            print(f"📄 المحتوى الرئيسي ({len(main_text)} حرف):")
            # طباعة أول 300 حرف من المحتوى الرئيسي
            print(f"   {main_text[:300]}...")
        
        # فحص الجافاسكريپت والترجمات
        print("\n" + "=" * 50)
        print("🔧 فحص نصوص الجافاسكريپت:")
        print("=" * 50)
        
        script_tags = soup.find_all('script')
        js_english_count = 0
        for script in script_tags:
            if script.string:
                for term in english_terms:
                    js_english_count += script.string.count(f'"{term}"') + script.string.count(f"'{term}'")
        
        print(f"📊 عدد المصطلحات الإنجليزية في الجافاسكريپت: {js_english_count}")
        
        # النتيجة النهائية
        print("\n" + "=" * 80)
        print("🏆 النتيجة النهائية:")
        print("=" * 80)
        
        if found_terms:
            print("❌ الصفحة تحتوي على نصوص إنجليزية تحتاج إصلاح")
            print(f"📊 إجمالي المصطلحات الإنجليزية المرئية: {total_english_words}")
            print(f"📊 إجمالي المصطلحات في الجافاسكريپت: {js_english_count}")
        else:
            print("✅ الصفحة نظيفة من النصوص الإنجليزية المرئية")
            
        # حفظ التقرير
        report = {
            'url': url,
            'status_code': response.status_code,
            'total_english_terms': len(found_terms),
            'total_english_words': total_english_words,
            'found_terms': found_terms,
            'js_english_count': js_english_count,
            'title': title.get_text().strip() if title else None
        }
        
        with open('arabic_page_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        print(f"\n💾 تم حفظ التقرير في: arabic_page_report.json")
        
    except Exception as e:
        print(f"❌ خطأ في الفحص: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_arabic_page_english_texts()

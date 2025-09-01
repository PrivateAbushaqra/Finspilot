#!/usr/bin/env python3
"""
فحص شامل للنصوص الإنجليزية في لوحة التحكم العربية
"""

import requests
from bs4 import BeautifulSoup
import time

def comprehensive_arabic_dashboard_check():
    """فحص شامل للوحة التحكم العربية بعد تسجيل الدخول الصحيح"""
    
    try:
        session = requests.Session()
        
        print("=" * 80)
        print("🎯 فحص شامل للنصوص الإنجليزية في لوحة التحكم العربية")
        print("=" * 80)
        
        # خطوة 1: الحصول على صفحة تسجيل الدخول
        print("1️⃣ الحصول على صفحة تسجيل الدخول...")
        login_page = session.get('http://127.0.0.1:8000/')
        
        if login_page.status_code != 200:
            print(f"❌ فشل في الوصول لصفحة تسجيل الدخول: {login_page.status_code}")
            return
            
        print(f"✅ تم الوصول لصفحة تسجيل الدخول: {login_page.status_code}")
        
        # خطوة 2: استخراج CSRF token
        soup = BeautifulSoup(login_page.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        
        if not csrf_input:
            print("❌ لم يتم العثور على CSRF token")
            return
            
        csrf_token = csrf_input.get('value')
        print(f"✅ تم الحصول على CSRF token: {csrf_token[:20]}...")
        
        # خطوة 3: تسجيل الدخول
        print("3️⃣ تسجيل الدخول...")
        login_data = {
            'username': 'super',
            'password': 'password',
            'csrfmiddlewaretoken': csrf_token
        }
        
        login_response = session.post('http://127.0.0.1:8000/auth/login/', data=login_data, allow_redirects=True)
        print(f"✅ استجابة تسجيل الدخول: {login_response.status_code}")
        print(f"📍 الرابط النهائي بعد التوجيه: {login_response.url}")
        
        # خطوة 4: الوصول للوحة التحكم العربية
        print("4️⃣ الوصول للوحة التحكم العربية...")
        dashboard_response = session.get('http://127.0.0.1:8000/ar/', allow_redirects=True)
        print(f"✅ استجابة لوحة التحكم: {dashboard_response.status_code}")
        print(f"📍 الرابط النهائي: {dashboard_response.url}")
        
        if dashboard_response.status_code != 200:
            print(f"❌ فشل في الوصول للوحة التحكم: {dashboard_response.status_code}")
            return
            
        # خطوة 5: تحليل المحتوى
        soup = BeautifulSoup(dashboard_response.text, 'html.parser')
        visible_text = soup.get_text()
        
        print(f"\n📊 معلومات الصفحة:")
        print(f"   📄 حجم المحتوى: {len(dashboard_response.text)} حرف")
        print(f"   👁️ حجم النص المرئي: {len(visible_text)} حرف")
        
        # العنوان
        title = soup.find('title')
        if title:
            print(f"   📋 العنوان: {title.get_text().strip()}")
        
        # خطوة 6: البحث عن المصطلحات الإنجليزية
        print(f"\n🔍 البحث عن المصطلحات الإنجليزية...")
        
        # قائمة شاملة من المصطلحات الإنجليزية
        english_terms = [
            # Navigation & UI
            'Dashboard', 'Home', 'Profile', 'Settings', 'Logout', 'Login',
            'Menu', 'Navigation', 'Sidebar', 'Header', 'Footer', 'Content',
            
            # Actions
            'Add', 'Edit', 'Delete', 'Save', 'Cancel', 'Submit', 'Back', 'Next', 
            'Previous', 'Search', 'Filter', 'Sort', 'Print', 'Export', 'Import',
            'Create', 'Update', 'View', 'Details', 'Show', 'Hide', 'Open', 'Close',
            
            # Users & Admin
            'User', 'Users', 'Admin', 'Administrator', 'Management', 'System',
            'Account', 'Accounts', 'Username', 'Password', 'Permission', 'Role',
            
            # Financial Terms
            'Invoice', 'Invoices', 'Payment', 'Payments', 'Receipt', 'Receipts',
            'Customer', 'Customers', 'Supplier', 'Suppliers', 'Product', 'Products',
            'Inventory', 'Sales', 'Purchase', 'Purchases', 'Revenue', 'Revenues',
            'Expense', 'Expenses', 'Journal', 'Bank', 'Banks', 'Cash', 'Cashbox',
            'Asset', 'Assets', 'Liability', 'Liabilities', 'Equity', 'Balance',
            'Income', 'Statement', 'Total', 'Amount', 'Quantity', 'Price',
            
            # Common Words
            'Date', 'Name', 'Description', 'Status', 'Type', 'Category', 'Code',
            'Number', 'ID', 'Reference', 'From', 'To', 'Start', 'End', 'Today',
            'Yesterday', 'Week', 'Month', 'Year', 'Daily', 'Monthly', 'Yearly',
            
            # Status Messages
            'Success', 'Error', 'Warning', 'Info', 'Message', 'Loading',
            'Please wait', 'Processing', 'Complete', 'Yes', 'No', 'OK',
            'New', 'Old', 'Active', 'Inactive', 'Enabled', 'Disabled',
            
            # Reports
            'Report', 'Reports', 'Analytics', 'Chart', 'Table', 'Summary'
        ]
        
        # البحث في النص المرئي
        found_terms = {}
        total_count = 0
        
        for term in english_terms:
            count = visible_text.count(term)
            if count > 0:
                found_terms[term] = count
                total_count += count
        
        print(f"\n📊 نتائج البحث:")
        print("-" * 50)
        
        if found_terms:
            print(f"❌ تم العثور على {len(found_terms)} مصطلحاً إنجليزياً مرئياً")
            print(f"📈 العدد الإجمالي: {total_count} كلمة")
            print(f"\n📝 قائمة المصطلحات الإنجليزية الموجودة:")
            
            for term, count in sorted(found_terms.items(), key=lambda x: x[1], reverse=True):
                print(f"   ❌ {term}: {count} مرة")
                
        else:
            print("✅ ممتاز! لا توجد مصطلحات إنجليزية مرئية")
        
        # خطوة 7: فحص العناصر المهمة
        print(f"\n🎯 فحص العناصر المهمة:")
        print("-" * 50)
        
        # الشريط العلوي والقائمة
        navbar = soup.find('nav') or soup.find('div', class_='navbar')
        if navbar:
            navbar_text = navbar.get_text()
            print(f"🧭 الشريط العلوي: {len(navbar_text)} حرف")
            # البحث عن كلمات إنجليزية في الشريط العلوي
            navbar_english = []
            for term in english_terms[:20]:  # أهم 20 مصطلح
                if term in navbar_text:
                    navbar_english.append(term)
            if navbar_english:
                print(f"   ❌ مصطلحات إنجليزية: {', '.join(navbar_english)}")
            else:
                print(f"   ✅ نظيف من المصطلحات الإنجليزية")
        
        # القائمة الجانبية
        sidebar = soup.find('div', class_='sidebar') or soup.find('aside')
        if sidebar:
            sidebar_text = sidebar.get_text()
            print(f"📂 القائمة الجانبية: {len(sidebar_text)} حرف")
            # البحث عن كلمات إنجليزية في القائمة الجانبية
            sidebar_english = []
            for term in english_terms[:30]:  # أهم 30 مصطلح
                if term in sidebar_text:
                    sidebar_english.append(term)
            if sidebar_english:
                print(f"   ❌ مصطلحات إنجليزية: {', '.join(sidebar_english)}")
            else:
                print(f"   ✅ نظيف من المصطلحات الإنجليزية")
        
        # المحتوى الرئيسي
        main_content = soup.find('main') or soup.find('div', class_='content')
        if main_content:
            main_text = main_content.get_text()
            print(f"📄 المحتوى الرئيسي: {len(main_text)} حرف")
        
        # خطوة 8: عرض جزء من المحتوى للمراجعة
        print(f"\n📝 جزء من المحتوى المرئي (أول 1000 حرف):")
        print("-" * 50)
        print(visible_text[:1000])
        print("-" * 50)
        
        # النتيجة النهائية
        print(f"\n🏆 النتيجة النهائية:")
        print("=" * 50)
        
        if found_terms:
            print(f"❌ لوحة التحكم العربية تحتوي على {len(found_terms)} مصطلحاً إنجليزياً")
            print(f"📊 إجمالي الكلمات الإنجليزية: {total_count}")
            print(f"🔧 يحتاج إصلاح الترجمة")
            
            # حفظ المصطلحات في ملف للمراجعة
            with open('english_terms_found.txt', 'w', encoding='utf-8') as f:
                f.write("المصطلحات الإنجليزية الموجودة في لوحة التحكم العربية:\n")
                f.write("=" * 60 + "\n")
                for term, count in sorted(found_terms.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"{term}: {count} مرة\n")
            print(f"💾 تم حفظ التقرير في: english_terms_found.txt")
            
        else:
            print(f"✅ لوحة التحكم العربية نظيفة من المصطلحات الإنجليزية!")
            print(f"🎉 الترجمة مكتملة بنجاح")
        
    except Exception as e:
        print(f"❌ خطأ في الفحص: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    comprehensive_arabic_dashboard_check()

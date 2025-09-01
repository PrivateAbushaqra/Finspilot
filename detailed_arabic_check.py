#!/usr/bin/env python3
"""
فحص مفصل للصفحة العربية بعد تسجيل الدخول
"""

import requests
from bs4 import BeautifulSoup

def detailed_arabic_page_check():
    """فحص مفصل للصفحة العربية"""
    
    try:
        session = requests.Session()
        
        # الحصول على صفحة تسجيل الدخول أولاً
        login_page = session.get('http://127.0.0.1:8000/')
        print(f"صفحة تسجيل الدخول: {login_page.status_code}")
        
        if login_page.status_code == 200:
            soup = BeautifulSoup(login_page.text, 'html.parser')
            
            # البحث عن نموذج تسجيل الدخول
            form = soup.find('form')
            if form:
                csrf_input = form.find('input', {'name': 'csrfmiddlewaretoken'})
                if csrf_input:
                    csrf_token = csrf_input.get('value')
                    
                    # تسجيل الدخول
                    login_data = {
                        'username': 'super',
                        'password': 'password',
                        'csrfmiddlewaretoken': csrf_token
                    }
                    
                    # إرسال بيانات تسجيل الدخول
                    action_url = form.get('action') or '/login/'
                    if not action_url.startswith('http'):
                        action_url = 'http://127.0.0.1:8000' + action_url
                        
                    login_response = session.post(action_url, data=login_data)
                    print(f"استجابة تسجيل الدخول: {login_response.status_code}")
                    
                    # الآن محاولة الوصول للصفحة العربية
                    arabic_response = session.get('http://127.0.0.1:8000/ar/')
                    print(f"الصفحة العربية: {arabic_response.status_code}")
                    
                    if arabic_response.status_code == 200:
                        soup = BeautifulSoup(arabic_response.text, 'html.parser')
                        visible_text = soup.get_text()
                        
                        print("=" * 80)
                        print("🔍 محتوى الصفحة العربية بعد تسجيل الدخول")
                        print("=" * 80)
                        print(f"حجم النص المرئي: {len(visible_text)} حرف")
                        
                        # طباعة أول 2000 حرف من النص المرئي
                        print("\n📄 النص المرئي:")
                        print("-" * 50)
                        print(visible_text[:2000])
                        print("-" * 50)
                        
                        # البحث عن مصطلحات إنجليزية شائعة
                        english_terms = [
                            'Dashboard', 'Home', 'Profile', 'Settings', 'Logout', 'Login',
                            'Add', 'Edit', 'Delete', 'Save', 'Cancel', 'Submit', 'Back',
                            'Next', 'Previous', 'Search', 'Filter', 'Sort', 'Print',
                            'Export', 'Import', 'Create', 'Update', 'View', 'Details',
                            'User', 'Users', 'Admin', 'Management', 'System', 'Report', 'Reports',
                            'Account', 'Accounts', 'Invoice', 'Invoices', 'Payment', 'Payments',
                            'Receipt', 'Receipts', 'Customer', 'Customers', 'Supplier', 'Suppliers',
                            'Product', 'Products', 'Inventory', 'Sales', 'Purchase', 'Purchases',
                            'Revenue', 'Revenues', 'Expense', 'Expenses', 'Journal', 'Bank', 'Banks',
                            'Cash', 'Cashbox', 'Asset', 'Assets', 'Liability', 'Liabilities',
                            'Equity', 'Balance', 'Income', 'Statement', 'Total', 'Amount',
                            'Quantity', 'Price', 'Date', 'Name', 'Description', 'Status',
                            'Type', 'Category', 'Code', 'Number', 'ID', 'Reference',
                            'Loading', 'Success', 'Error', 'Warning', 'Info', 'Message',
                            'Yes', 'No', 'OK', 'Cancel', 'Close', 'Open', 'New', 'Active'
                        ]
                        
                        print("\n🔍 البحث عن المصطلحات الإنجليزية:")
                        print("=" * 50)
                        
                        found_terms = {}
                        total_count = 0
                        
                        for term in english_terms:
                            count = visible_text.count(term)
                            if count > 0:
                                found_terms[term] = count
                                total_count += count
                        
                        if found_terms:
                            print(f"❌ تم العثور على {len(found_terms)} مصطلحاً إنجليزياً:")
                            print(f"📊 العدد الإجمالي: {total_count} كلمة")
                            print("\n📝 التفاصيل:")
                            
                            for term, count in sorted(found_terms.items()):
                                print(f"   • {term}: {count} مرة")
                                
                            print("\n🔴 خلاصة: الصفحة العربية تحتوي على نصوص إنجليزية!")
                        else:
                            print("✅ لا توجد مصطلحات إنجليزية مرئية")
                            
                        # فحص العناصر المهمة
                        print("\n" + "=" * 50)
                        print("🎯 فحص العناصر المهمة:")
                        print("=" * 50)
                        
                        # العنوان
                        title = soup.find('title')
                        if title:
                            print(f"📋 العنوان: {title.get_text().strip()}")
                        
                        # الملاحة
                        nav_elements = soup.find_all(['nav', 'div'], class_=['navbar', 'nav', 'navigation', 'sidebar'])
                        for i, nav in enumerate(nav_elements):
                            nav_text = nav.get_text()[:200]
                            print(f"🧭 عنصر ملاحة {i+1}: {nav_text}...")
                            
                    else:
                        print(f"❌ فشل في الوصول للصفحة العربية: {arabic_response.status_code}")
                        print(f"المحتوى: {arabic_response.text[:500]}")
                else:
                    print("❌ لم يتم العثور على CSRF token")
            else:
                print("❌ لم يتم العثور على نموذج تسجيل الدخول")
        else:
            print(f"❌ فشل في الوصول لصفحة تسجيل الدخول: {login_page.status_code}")
            
    except Exception as e:
        print(f"❌ خطأ في الفحص: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    detailed_arabic_page_check()

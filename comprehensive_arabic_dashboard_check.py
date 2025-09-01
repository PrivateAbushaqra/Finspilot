#!/usr/bin/env python3
"""
فحص شامل للنصوص الإنجليزية في لوحة التحكم بعد تسجيل الدخول الناجح
"""

import requests
from bs4 import BeautifulSoup
import re

def check_dashboard_after_login():
    """فحص لوحة التحكم بعد تسجيل الدخول الناجح"""
    
    try:
        session = requests.Session()
        
        print("=" * 80)
        print("🔍 فحص شامل للنصوص الإنجليزية في لوحة التحكم العربية")
        print("=" * 80)
        
        # خطوة 1: الوصول لصفحة تسجيل الدخول
        print("1️⃣ الوصول لصفحة تسجيل الدخول...")
        login_page = session.get('http://127.0.0.1:8000/ar/auth/login/')
        
        if login_page.status_code != 200:
            print(f"❌ فشل في الوصول لصفحة تسجيل الدخول: {login_page.status_code}")
            return
            
        soup = BeautifulSoup(login_page.text, 'html.parser')
        
        # البحث عن نموذج تسجيل الدخول الصحيح
        login_form = None
        forms = soup.find_all('form')
        for form in forms:
            if form.find('input', {'name': 'username'}) and form.find('input', {'name': 'password'}):
                login_form = form
                break
        
        if not login_form:
            print("❌ لم يتم العثور على نموذج تسجيل الدخول")
            return
            
        # الحصول على CSRF token
        csrf_input = login_form.find('input', {'name': 'csrfmiddlewaretoken'})
        if not csrf_input:
            print("❌ لم يتم العثور على CSRF token")
            return
            
        csrf_token = csrf_input.get('value')
        print(f"✅ تم الحصول على CSRF token")
        
        # خطوة 2: تسجيل الدخول
        print("2️⃣ تسجيل الدخول بالمستخدم super...")
        login_data = {
            'username': 'super',
            'password': 'password',
            'csrfmiddlewaretoken': csrf_token
        }
        
        action_url = login_form.get('action') or '/ar/auth/login/'
        if not action_url.startswith('http'):
            action_url = 'http://127.0.0.1:8000' + action_url
            
        login_response = session.post(action_url, data=login_data, allow_redirects=True)
        
        print(f"✅ استجابة تسجيل الدخول: {login_response.status_code}")
        print(f"📍 الرابط النهائي: {login_response.url}")
        
        # التحقق من نجاح تسجيل الدخول
        soup = BeautifulSoup(login_response.text, 'html.parser')
        
        # إذا كان ما زال في صفحة تسجيل الدخول، نجرب الوصول للوحة التحكم مباشرة
        if 'auth/login' in login_response.url:
            print("3️⃣ محاولة الوصول للوحة التحكم مباشرة...")
            dashboard_response = session.get('http://127.0.0.1:8000/ar/', allow_redirects=True)
            
            if dashboard_response.status_code == 200:
                soup = BeautifulSoup(dashboard_response.text, 'html.parser')
                print(f"✅ تم الوصول للوحة التحكم: {dashboard_response.url}")
            else:
                print(f"❌ فشل في الوصول للوحة التحكم: {dashboard_response.status_code}")
                return
        
        # خطوة 3: تحليل المحتوى
        visible_text = soup.get_text()
        
        # معلومات الصفحة
        title = soup.find('title')
        page_title = title.get_text().strip() if title else "لا يوجد عنوان"
        
        print(f"\n📊 معلومات الصفحة:")
        print(f"   📋 العنوان: {page_title}")
        print(f"   📄 حجم المحتوى: {len(soup.text)} حرف")
        print(f"   👁️ حجم النص المرئي: {len(visible_text)} حرف")
        
        # خطوة 4: البحث الشامل عن المصطلحات الإنجليزية
        print(f"\n🔍 البحث الشامل عن المصطلحات الإنجليزية...")
        
        # قائمة شاملة بالمصطلحات الإنجليزية
        english_terms = [
            # الواجهة الرئيسية
            'Dashboard', 'Home', 'Main', 'Index', 'Overview',
            
            # التنقل والقوائم
            'Navigation', 'Menu', 'Sidebar', 'Header', 'Footer', 'Navbar',
            'Breadcrumb', 'Tab', 'Tabs', 'Panel', 'Panels',
            
            # الإجراءات
            'Add', 'Create', 'New', 'Edit', 'Update', 'Modify', 'Delete', 'Remove',
            'Save', 'Submit', 'Cancel', 'Back', 'Return', 'Continue', 'Next',
            'Previous', 'Prev', 'First', 'Last', 'Finish', 'Complete',
            
            # البحث والتصفية
            'Search', 'Find', 'Filter', 'Sort', 'Order', 'Group', 'Show', 'Hide',
            'View', 'Display', 'List', 'Grid', 'Table', 'Chart', 'Graph',
            
            # الطباعة والتصدير
            'Print', 'Export', 'Import', 'Download', 'Upload', 'File', 'Files',
            
            # المستخدمين والإدارة
            'User', 'Users', 'Admin', 'Administrator', 'Management', 'Manager',
            'Profile', 'Account', 'Accounts', 'Settings', 'Configuration', 'Config',
            'Preferences', 'Options', 'System', 'Setup', 'Installation',
            
            # التسجيل والجلسات
            'Login', 'Logout', 'Sign In', 'Sign Out', 'Sign Up', 'Register',
            'Authentication', 'Session', 'Password', 'Username', 'Email',
            
            # الصلاحيات والأدوار
            'Permission', 'Permissions', 'Role', 'Roles', 'Access', 'Security',
            'Authorization', 'Group', 'Groups',
            
            # المالية والمحاسبة
            'Finance', 'Financial', 'Accounting', 'Account', 'Invoice', 'Invoices',
            'Payment', 'Payments', 'Receipt', 'Receipts', 'Transaction', 'Transactions',
            'Journal', 'Entry', 'Entries', 'Balance', 'Total', 'Subtotal',
            'Amount', 'Price', 'Cost', 'Revenue', 'Revenues', 'Income',
            'Expense', 'Expenses', 'Profit', 'Loss', 'Asset', 'Assets',
            'Liability', 'Liabilities', 'Equity', 'Capital', 'Cash', 'Bank', 'Banks',
            
            # العملاء والموردين
            'Customer', 'Customers', 'Client', 'Clients', 'Supplier', 'Suppliers',
            'Vendor', 'Vendors', 'Contact', 'Contacts',
            
            # المنتجات والمخزون
            'Product', 'Products', 'Item', 'Items', 'Service', 'Services',
            'Inventory', 'Stock', 'Quantity', 'Unit', 'Units', 'Category', 'Categories',
            
            # المبيعات والمشتريات
            'Sales', 'Sale', 'Purchase', 'Purchases', 'Order', 'Orders',
            'Quotation', 'Quotations', 'Estimate', 'Estimates',
            
            # التقارير والإحصائيات
            'Report', 'Reports', 'Analytics', 'Statistics', 'Stats', 'Summary',
            'Details', 'Analysis', 'Overview', 'Performance', 'Metrics',
            
            # التواريخ والأوقات
            'Date', 'Time', 'Today', 'Yesterday', 'Tomorrow', 'Week', 'Month',
            'Year', 'Daily', 'Weekly', 'Monthly', 'Yearly', 'Annual',
            'From', 'To', 'Between', 'Start', 'End', 'Begin', 'Finish',
            
            # الحالات والأوضاع
            'Status', 'State', 'Active', 'Inactive', 'Enabled', 'Disabled',
            'Published', 'Draft', 'Pending', 'Approved', 'Rejected', 'Cancelled',
            'Open', 'Closed', 'Completed', 'Processing', 'Success', 'Failed',
            
            # الرسائل والإشعارات
            'Message', 'Messages', 'Notification', 'Notifications', 'Alert', 'Alerts',
            'Warning', 'Error', 'Info', 'Information', 'Notice', 'Confirmation',
            
            # الأوصاف والتفاصيل
            'Name', 'Title', 'Description', 'Note', 'Notes', 'Comment', 'Comments',
            'Remark', 'Remarks', 'Code', 'ID', 'Number', 'Reference', 'Ref',
            'Type', 'Kind', 'Size', 'Color', 'Weight', 'Length', 'Width', 'Height',
            
            # الجودة والتحقق
            'Quality', 'Valid', 'Invalid', 'Required', 'Optional', 'Mandatory',
            'Available', 'Unavailable', 'Empty', 'Full', 'None', 'All', 'Any',
            
            # الإجراءات العامة
            'Loading', 'Please wait', 'Processing', 'Working', 'Saving', 'Deleting',
            'Updating', 'Creating', 'Sending', 'Receiving', 'Connecting',
            
            # الردود والتأكيدات
            'Yes', 'No', 'OK', 'Cancel', 'Confirm', 'Accept', 'Decline', 'Agree',
            'Disagree', 'True', 'False', 'On', 'Off', 'Enable', 'Disable',
            
            # التكنولوجيا والنظام
            'Technology', 'Software', 'Hardware', 'Database', 'Server', 'Client',
            'Application', 'Program', 'Module', 'Component', 'Feature', 'Function',
            'Tool', 'Tools', 'Utility', 'Helper', 'Support', 'Help', 'About',
            
            # النسخ الاحتياطي والاستعادة
            'Backup', 'Restore', 'Recovery', 'Archive', 'History', 'Log', 'Logs',
            
            # الموارد البشرية
            'HR', 'Human Resources', 'Employee', 'Employees', 'Staff', 'Department',
            'Departments', 'Position', 'Positions', 'Salary', 'Salaries', 'Payroll',
            'Attendance', 'Leave', 'Vacation', 'Holiday'
        ]
        
        # البحث عن المصطلحات
        found_terms = {}
        total_english_words = 0
        
        for term in english_terms:
            # البحث بحساسية للأحرف (case-sensitive) و بدونها
            count_exact = visible_text.count(term)
            count_lower = visible_text.lower().count(term.lower()) - count_exact
            
            total_count = count_exact + count_lower
            if total_count > 0:
                found_terms[term] = total_count
                total_english_words += total_count
        
        # النتائج
        print(f"\n📊 نتائج البحث:")
        print("-" * 60)
        
        if found_terms:
            print(f"❌ تم العثور على {len(found_terms)} مصطلحاً إنجليزياً")
            print(f"📈 إجمالي الكلمات الإنجليزية: {total_english_words}")
            
            print(f"\n📝 قائمة المصطلحات الإنجليزية الموجودة:")
            print("-" * 60)
            
            # ترتيب المصطلحات حسب عدد المرات
            sorted_terms = sorted(found_terms.items(), key=lambda x: x[1], reverse=True)
            
            for i, (term, count) in enumerate(sorted_terms, 1):
                print(f"{i:2d}. {term:<20} : {count} مرة")
                
        else:
            print("✅ ممتاز! لا توجد مصطلحات إنجليزية مرئية")
        
        # خطوة 5: فحص العناصر المهمة
        print(f"\n🎯 فحص العناصر المهمة:")
        print("-" * 60)
        
        # الشريط العلوي
        navbar = soup.find('nav') or soup.find('div', class_='navbar')
        if navbar:
            navbar_text = navbar.get_text()
            navbar_english = []
            for term in english_terms[:30]:  # أهم 30 مصطلح
                if term in navbar_text:
                    navbar_english.append(term)
            
            print(f"🧭 الشريط العلوي:")
            if navbar_english:
                print(f"   ❌ مصطلحات إنجليزية: {', '.join(navbar_english)}")
            else:
                print(f"   ✅ نظيف من المصطلحات الإنجليزية")
        
        # القائمة الجانبية
        sidebar = soup.find('div', class_='sidebar') or soup.find('aside')
        if sidebar:
            sidebar_text = sidebar.get_text()
            sidebar_english = []
            for term in english_terms[:50]:  # أهم 50 مصطلح
                if term in sidebar_text:
                    sidebar_english.append(term)
            
            print(f"📂 القائمة الجانبية:")
            if sidebar_english:
                print(f"   ❌ مصطلحات إنجليزية: {', '.join(sidebar_english)}")
            else:
                print(f"   ✅ نظيف من المصطلحات الإنجليزية")
        
        # خطوة 6: عرض جزء من المحتوى
        print(f"\n📄 عينة من المحتوى المرئي (أول 1500 حرف):")
        print("-" * 60)
        print(visible_text[:1500])
        print("-" * 60)
        
        # خطوة 7: النتيجة النهائية
        print(f"\n🏆 النتيجة النهائية:")
        print("=" * 60)
        
        if found_terms:
            print(f"❌ لوحة التحكم العربية تحتوي على نصوص إنجليزية!")
            print(f"📊 عدد المصطلحات المختلفة: {len(found_terms)}")
            print(f"📈 إجمالي الكلمات الإنجليزية: {total_english_words}")
            print(f"🔧 يحتاج إصلاح فوري للترجمة")
            
            # حفظ التقرير المفصل
            with open('arabic_dashboard_english_terms.txt', 'w', encoding='utf-8') as f:
                f.write("تقرير المصطلحات الإنجليزية في لوحة التحكم العربية\n")
                f.write("=" * 60 + "\n")
                f.write(f"تاريخ الفحص: {page_title}\n")
                f.write(f"عدد المصطلحات: {len(found_terms)}\n")
                f.write(f"إجمالي الكلمات: {total_english_words}\n\n")
                f.write("قائمة المصطلحات:\n")
                f.write("-" * 40 + "\n")
                
                for i, (term, count) in enumerate(sorted_terms, 1):
                    f.write(f"{i:2d}. {term:<20} : {count} مرة\n")
                    
                f.write("\n" + "=" * 60 + "\n")
                f.write("عينة من المحتوى:\n")
                f.write(visible_text[:2000])
            
            print(f"💾 تم حفظ التقرير المفصل في: arabic_dashboard_english_terms.txt")
            
        else:
            print(f"✅ لوحة التحكم العربية نظيفة من المصطلحات الإنجليزية!")
            print(f"🎉 الترجمة مكتملة بنجاح")
        
        print("\n" + "=" * 80)
        print("🔚 انتهى الفحص")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ خطأ في الفحص: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_dashboard_after_login()

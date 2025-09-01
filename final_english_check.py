#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فحص شامل ونهائي للنصوص الإنجليزية في النسخة العربية
Final comprehensive check for English texts in Arabic version
"""

import requests
import re
import time

def comprehensive_english_check():
    print("🔍 بدء الفحص الشامل للنصوص الإنجليزية في النسخة العربية...")
    print("=" * 60)
    
    try:
        # انتظار قليل للتأكد من تشغيل الخادم
        time.sleep(2)
        
        # جلب محتوى الصفحة العربية
        print("📥 جاري جلب محتوى الصفحة العربية...")
        response = requests.get('http://127.0.0.1:8000/ar/', timeout=10)
        content = response.text
        
        # قائمة شاملة بالمصطلحات الإنجليزية المحتملة
        english_terms = [
            # المصطلحات الأساسية
            'Dashboard', 'Settings', 'Logout', 'Login',
            'Home', 'Profile', 'Admin', 'User', 'Users',
            'Reports', 'Settings', 'Configuration',
            
            # المصطلحات المالية والمحاسبية
            'Sales', 'Purchases', 'Inventory', 'Accounts',
            'Journal', 'Assets', 'Liabilities', 'Revenue',
            'Expenses', 'Invoice', 'Receipt', 'Payment',
            'Customer', 'Supplier', 'Product', 'Service',
            
            # مصطلحات الموارد البشرية
            'Employee', 'Employees', 'Department', 'Position',
            'Attendance', 'Leave', 'Salary', 'Payroll',
            
            # مصطلحات واجهة المستخدم
            'Add', 'Edit', 'Delete', 'Save', 'Cancel',
            'Submit', 'Search', 'Filter', 'Sort', 'Export',
            'Import', 'Print', 'Download', 'Upload',
            'Back', 'Next', 'Previous', 'Continue',
            
            # أزرار وعناصر التحكم
            'Button', 'Form', 'Table', 'List', 'View',
            'Create', 'Update', 'Remove', 'Clear', 'Reset',
            
            # رسائل النظام
            'Success', 'Error', 'Warning', 'Info',
            'Loading', 'Please wait', 'Confirmation',
            'Are you sure', 'Yes', 'No', 'OK', 'Close'
        ]
        
        print(f"🔎 البحث عن {len(english_terms)} مصطلحاً إنجليزياً...")
        
        found_terms = {}
        total_english_words = 0
        
        # البحث عن كل مصطلح
        for term in english_terms:
            # البحث بدون تحسس لحالة الأحرف
            matches = re.findall(r'\b' + re.escape(term) + r'\b', content, re.IGNORECASE)
            if matches:
                count = len(matches)
                found_terms[term] = count
                total_english_words += count
        
        # عرض النتائج
        print("\n📊 نتائج الفحص:")
        print("-" * 40)
        
        if found_terms:
            print(f"❌ تم العثور على {len(found_terms)} مصطلحاً إنجليزياً:")
            print(f"📈 العدد الإجمالي للكلمات الإنجليزية: {total_english_words}")
            print("\n📝 التفاصيل:")
            
            for term, count in sorted(found_terms.items()):
                print(f"   • {term}: {count} مرة")
                
            print(f"\n🔴 الخلاصة: النسخة العربية تحتوي على نصوص إنجليزية!")
            return False
            
        else:
            print("✅ ممتاز! لم يتم العثور على أي مصطلحات إنجليزية")
            print("🎉 النسخة العربية نظيفة تماماً من النصوص الإنجليزية")
            print(f"📄 تم فحص {len(content):,} حرف في الصفحة")
            return True
            
    except requests.exceptions.ConnectionError:
        print("❌ خطأ: لا يمكن الاتصال بالخادم على http://127.0.0.1:8000")
        print("💡 تأكد من تشغيل خادم Django")
        return False
        
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        return False
    
    finally:
        print("=" * 60)
        print("🏁 انتهى الفحص")

if __name__ == "__main__":
    success = comprehensive_english_check()
    exit(0 if success else 1)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import re
from urllib.parse import urljoin

def check_arabic_page_for_english(url):
    """فحص الصفحة للبحث عن نصوص إنجليزية"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return f'خطأ {response.status_code}'
        
        content = response.text
        
        # البحث عن النصوص الإنجليزية الشائعة في القوائم
        english_terms = [
            'Dashboard', 'Human Resources', 'Sales', 'Purchases', 
            'Inventory', 'Bank Accounts', 'Cash Boxes', 'Reports',
            'Settings', 'Logout', 'Global Search', 'System Management',
            'Journal Entries', 'Categories', 'Products', 'Customers',
            'Suppliers', 'Add User', 'Users List', 'HR Dashboard',
            'Attendance', 'Leave Requests', 'Payroll', 'HR Reports',
            'Add Category', 'Add Product', 'Categories List', 'Products List',
            'Customers List', 'Suppliers List', 'Payment Receipts',
            'Payment Vouchers', 'Vouchers List', 'Create Sales Invoice',
            'Create Purchase Invoice', 'Sales Invoices List', 'Purchase Invoices List'
        ]
        
        found_english = []
        for term in english_terms:
            # البحث عن النص في سياق HTML (ليس في attributes)
            pattern = f'>[^<]*{re.escape(term)}[^<]*<'
            if re.search(pattern, content, re.IGNORECASE):
                found_english.append(term)
        
        return found_english
        
    except Exception as e:
        return f'خطأ: {e}'

def main():
    # اختبار الصفحات الرئيسية
    test_urls = [
        'http://127.0.0.1:8000/ar/',
        'http://127.0.0.1:8000/ar/login/',
        'http://127.0.0.1:8000/ar/hr/dashboard/'
    ]

    print('فحص شامل للنصوص الإنجليزية في النسخة العربية:')
    print('=' * 70)

    all_english_found = []

    for url in test_urls:
        print(f'\nفحص: {url}')
        print('-' * 50)
        
        result = check_arabic_page_for_english(url)
        
        if isinstance(result, list):
            if result:
                print(f'⚠️  وُجدت نصوص إنجليزية: {len(result)}')
                for term in result[:10]:  # أول 10 نصوص
                    print(f'   • {term}')
                all_english_found.extend(result)
            else:
                print('✅ لم توجد نصوص إنجليزية')
        else:
            print(f'❌ {result}')

    print('\n' + '=' * 70)
    print('النتيجة النهائية:')

    if all_english_found:
        unique_english = list(set(all_english_found))
        print(f'❌ وُجدت {len(unique_english)} نصوص إنجليزية فريدة')
        print('النصوص التي تحتاج إصلاح:')
        for term in sorted(unique_english):
            print(f'   • {term}')
    else:
        print('✅ لم توجد أي نصوص إنجليزية في النسخة العربية')

    print('\n' + '=' * 70)

if __name__ == "__main__":
    main()

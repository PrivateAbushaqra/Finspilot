#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def add_missing_translations():
    """Add missing JavaScript translations to base.html"""
    
    base_file = "templates/base.html"
    
    # Read the current file
    with open(base_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the exact location to insert - before the closing brace of TRANSLATIONS
    target_line = "        'التقنيات': 'Technologies'\n    };"
    
    if target_line not in content:
        print("Could not find the target location in TRANSLATIONS")
        return False
    
    # New translations to add for the remaining 20 texts
    new_translations = """,
        
        // Missing translations for remaining 20 texts (English to Arabic in this section)
        'System Management - For Super Admin and Admin': 'إدارة النظام - للمدير العام والمدير',
        'System Management': 'إدارة النظام',
        'Purchases': 'المشتريات',
        'Assets & Liabilities': 'الأصول والخصوم',
        'Backup and Restore': 'النسخ الاحتياطي والاستعادة',
        'Journal Entries': 'القيود المحاسبية',
        'Human Resources': 'الموارد البشرية',
        'Customers & Suppliers': 'العملاء والموردين',
        'Cashboxes': 'الصناديق',
        'Payment Vouchers': 'سندات الدفع',
        'JoFotara Settings': 'إعدادات جوفوترة',
        'Bank Accounts (visible if group grants view or edit banks account)': 'الحسابات البنكية (مرئية إذا كانت المجموعة تمنح عرض أو تعديل حساب البنوك)',
        'Inventory': 'المخزون',
        'Reports': 'التقارير',
        'Print Design Settings': 'إعدادات تصميم الطباعة',
        'Products & Categories': 'المنتجات والفئات',
        'Revenues & Expenses': 'الإيرادات والمصروفات',
        'Dashboard': 'لوحة القيادة',
        'Payment Receipts': 'إيصالات الدفع',
        'Sales': 'المبيعات'"""
    
    # Replace the target with target + new translations
    updated_target = "        'التقنيات': 'Technologies'" + new_translations + "\n    };"
    new_content = content.replace(target_line, updated_target)
    
    # Write the updated content
    with open(base_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✓ Added 20 missing JavaScript translations to base.html")
    return True

if __name__ == "__main__":
    add_missing_translations()

#!/usr/bin/env python
"""
سكريبت شامل لإضافة ترجمات Django - الدفعة الثانية
"""

import re

# قائمة الترجمات المطلوبة
translations_to_add = [
    ('msgid "Cash Boxes"', 'msgstr "الصناديق النقدية"'),
    ('msgid "Cashboxes"', 'msgstr "الصناديق"'),
    ('msgid "Cashboxes List"', 'msgstr "قائمة الصناديق"'),
    ('msgid "Payment Vouchers"', 'msgstr "سندات الدفع"'),
    ('msgid "Payment Receipts"', 'msgstr "سندات القبض"'),
    ('msgid "Create Manual Entry"', 'msgstr "إنشاء قيد يدوي"'),
    ('msgid "All Entries"', 'msgstr "جميع القيود"'),
    ('msgid "Entries List"', 'msgstr "قائمة القيود"'),
    ('msgid "Entries by Type"', 'msgstr "القيود حسب النوع"'),
    ('msgid "Chart of Accounts"', 'msgstr "دليل الحسابات"'),
    ('msgid "Accounts List"', 'msgstr "قائمة الحسابات"'),
    ('msgid "Add Account"', 'msgstr "إضافة حساب"'),
    ('msgid "Trial Balance"', 'msgstr "ميزان المراجعة"'),
    ('msgid "Profit and Loss"', 'msgstr "الأرباح والخسائر"'),
    ('msgid "Assets List"', 'msgstr "قائمة الأصول"'),
    ('msgid "Liabilities List"', 'msgstr "قائمة الخصوم"'),
    ('msgid "Revenues & Expenses"', 'msgstr "الإيرادات والمصروفات"'),
    ('msgid "Customers List"', 'msgstr "قائمة العملاء"'),
    ('msgid "Suppliers List"', 'msgstr "قائمة الموردين"'),
    ('msgid "All Customers & Suppliers"', 'msgstr "جميع العملاء والموردين"'),
    ('msgid "Products List"', 'msgstr "قائمة المنتجات"'),
    ('msgid "Categories List"', 'msgstr "قائمة الفئات"'),
    ('msgid "Manage Categories"', 'msgstr "إدارة الفئات"'),
    ('msgid "Categories & Products"', 'msgstr "الفئات والمنتجات"'),
    ('msgid "View Inventory"', 'msgstr "عرض المخزون"'),
    ('msgid "Inventory Movement"', 'msgstr "حركة المخزون"'),
    ('msgid "Stock Alerts"', 'msgstr "تنبيهات المخزون"'),
    ('msgid "Sales Invoices List"', 'msgstr "قائمة فواتير المبيعات"'),
    ('msgid "Sales Returns List"', 'msgstr "قائمة مردودات المبيعات"'),
    ('msgid "Create Sales Return"', 'msgstr "إنشاء مردود مبيعات"'),
    ('msgid "Sales Statement"', 'msgstr "كشف المبيعات"'),
    ('msgid "Sales Returns Statement"', 'msgstr "كشف مردودات المبيعات"'),
    ('msgid "Purchase Invoices List"', 'msgstr "قائمة فواتير المشتريات"'),
    ('msgid "Purchase Returns List"', 'msgstr "قائمة مردودات المشتريات"'),
    ('msgid "Create Purchase Return"', 'msgstr "إنشاء مردود مشتريات"'),
    ('msgid "Purchase Statement"', 'msgstr "كشف المشتريات"'),
    ('msgid "Purchase Return Statement"', 'msgstr "كشف مردودات المشتريات"'),
    ('msgid "Vouchers List"', 'msgstr "قائمة السندات"'),
    ('msgid "Receipts List"', 'msgstr "قائمة الإيصالات"'),
    ('msgid "Add Payment Voucher"', 'msgstr "إضافة سند دفع"'),
    ('msgid "Add Payment Receipt"', 'msgstr "إضافة سند قبض"'),
    ('msgid "Add New Entry"', 'msgstr "إضافة قيد جديد"'),
]

# قراءة ملف الترجمة
with open('locale/ar/LC_MESSAGES/django.po', 'r', encoding='utf-8') as f:
    content = f.read()

# إضافة الترجمات
for search_text, replacement in translations_to_add:
    # البحث عن النص مع msgstr فارغ
    pattern = re.escape(search_text) + r'\s*msgstr\s*""'
    if re.search(pattern, content):
        new_text = search_text + '\n' + replacement
        content = re.sub(pattern, new_text, content)
        print(f"✓ تمت إضافة ترجمة: {search_text}")
    else:
        print(f"✗ لم يتم العثور على: {search_text}")

# حفظ الملف المحدث
with open('locale/ar/LC_MESSAGES/django.po', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nتم الانتهاء من إضافة الترجمات الإضافية!")

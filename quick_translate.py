#!/usr/bin/env python
"""
سكريبت سريع لإضافة ترجمات Django
"""

import re

# قائمة الترجمات المطلوبة
translations_to_add = [
    ('msgid "System Management"', 'msgstr "إدارة النظام"'),
    ('msgid "Add Customer/Supplier"', 'msgstr "إضافة عميل/مورد"'),
    ('msgid "Journal Entries"', 'msgstr "القيود المحاسبية"'),
    ('msgid "Assets & Liabilities"', 'msgstr "الأصول والخصوم"'),
    ('msgid "Point of Sale"', 'msgstr "نقطة البيع"'),
    ('msgid "Create Sales Invoice"', 'msgstr "إنشاء فاتورة مبيعات"'),
    ('msgid "Products & Categories"', 'msgstr "المنتجات والفئات"'),
    ('msgid "Add Product"', 'msgstr "إضافة منتج"'),
    ('msgid "Add Category"', 'msgstr "إضافة فئة"'),
    ('msgid "Warehouses"', 'msgstr "المستودعات"'),
    ('msgid "Users List"', 'msgstr "قائمة المستخدمين"'),
    ('msgid "Add User"', 'msgstr "إضافة مستخدم"'),
    ('msgid "System Settings"', 'msgstr "إعدادات النظام"'),
    ('msgid "Backup and Restore"', 'msgstr "النسخ الاحتياطي والاستعادة"'),
    ('msgid "Activity Log"', 'msgstr "سجل الأنشطة"'),
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

print("\nتم الانتهاء من إضافة الترجمات!")

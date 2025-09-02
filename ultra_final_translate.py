#!/usr/bin/env python
"""
سكريبت الترجمة النهائي للنصوص الـ 21 المتبقية
"""

import re

# قائمة النصوص الـ 21 المتبقية
remaining_texts = {
    "HR Reports": "تقارير الموارد البشرية",
    "Print Design Settings": "إعدادات تصميم الطباعة", 
    "Bank Accounts (visible if group grants view or edit banks account)": "الحسابات البنكية (ظاهرة إذا كانت المجموعة تمنح عرض أو تحرير الحسابات البنكية)",
    "System Management - For Super Admin and Admin": "إدارة النظام - للمشرف العام والمدير",
    "Products & Categories": "المنتجات والفئات"
}

# قراءة ملف الترجمة
with open('locale/ar/LC_MESSAGES/django.po', 'r', encoding='utf-8') as f:
    content = f.read()

print("إضافة الترجمات للنصوص المتبقية...")
print("=" * 50)

count = 0
for english_text, arabic_text in remaining_texts.items():
    # البحث عن النص مع msgstr فارغ
    pattern = rf'msgid "{re.escape(english_text)}"\s*msgstr\s*""'
    if re.search(pattern, content):
        new_text = f'msgid "{english_text}"\nmsgstr "{arabic_text}"'
        content = re.sub(pattern, new_text, content)
        print(f"✓ تمت إضافة ترجمة: {english_text}")
        count += 1
    else:
        print(f"✗ لم يتم العثور على: {english_text}")

# حفظ الملف المحدث
with open('locale/ar/LC_MESSAGES/django.po', 'w', encoding='utf-8') as f:
    f.write(content)

print("=" * 50)
print(f"تم إضافة {count} ترجمة أخيرة!")

# البحث عن بعض النصوص الأخرى التي قد تكون مفقودة
additional_searches = [
    "msgid \"Human Resources\"",
    "msgid \"JoFotara Settings\"",
    "msgid \"Cashboxes\"", 
    "msgid \"Revenues & Expenses\"",
    "msgid \"Backup and Restore\""
]

print("\nفحص النصوص الأخرى المفقودة...")
for search in additional_searches:
    if search in content:
        print(f"✓ موجود: {search}")
    else:
        print(f"✗ مفقود: {search}")

print("\nانتهى المعالجة النهائية!")

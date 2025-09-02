#!/usr/bin/env python
"""
سكريبت لإضافة ترجمات النصوص المتبقية من قائمة الـ 44
"""

import re

# قائمة النصوص المتبقية التي رأيناها في آخر فحص
remaining_texts = [
    "Sales Reports", "Groups & Permissions", "Checks Management", 
    "System Management", "Leave Requests", "Advanced", "Transfers List",
    "Debit Notes", "JoFotara Settings", "Purchase Reports", 
    "Tax Report", "Recurring Revenue", "Payroll", "Print Design Settings",
    "Positions", "Document Number Management", "Print Design", 
    "Sales Report By Sales Person", "Customer Statement", 
    "Comprehensive Search", "Attendance", "HR Dashboard", 
    "Departments", "Credit Notes", "Backup", "Employees"
]

# قاموس الترجمات
translations = {
    "Sales Reports": "تقارير المبيعات",
    "Groups & Permissions": "المجموعات والصلاحيات", 
    "Checks Management": "إدارة الشيكات",
    "Leave Requests": "طلبات الإجازة",
    "Advanced": "متقدم",
    "Transfers List": "قائمة التحويلات",
    "Debit Notes": "إشعارات الخصم",
    "JoFotara Settings": "إعدادات جوفطرة",
    "Purchase Reports": "تقارير المشتريات",
    "Tax Report": "تقرير الضريبة",
    "Recurring Revenue": "الإيرادات المتكررة",
    "Payroll": "كشف الرواتب",
    "Print Design Settings": "إعدادات تصميم الطباعة",
    "Positions": "المناصب",
    "Document Number Management": "إدارة أرقام المستندات",
    "Print Design": "تصميم الطباعة",
    "Sales Report By Sales Person": "تقرير المبيعات حسب المندوب",
    "Customer Statement": "كشف حساب العميل",
    "Comprehensive Search": "البحث الشامل",
    "Attendance": "الحضور",
    "HR Dashboard": "لوحة تحكم الموارد البشرية",
    "Departments": "الأقسام",
    "Credit Notes": "إشعارات دائنة",
    "Backup": "النسخ الاحتياطي",
    "Employees": "الموظفين"
}

# قراءة ملف الترجمة
with open('locale/ar/LC_MESSAGES/django.po', 'r', encoding='utf-8') as f:
    content = f.read()

print("البحث عن النصوص وإضافة ترجماتها...")
print("=" * 50)

count = 0
for english_text, arabic_text in translations.items():
    # البحث عن النص مع msgstr فارغ
    pattern = rf'msgid "{re.escape(english_text)}"\s*msgstr\s*""'
    if re.search(pattern, content):
        new_text = f'msgid "{english_text}"\nmsgstr "{arabic_text}"'
        content = re.sub(pattern, new_text, content)
        print(f"✓ تمت إضافة ترجمة: {english_text} → {arabic_text}")
        count += 1
    else:
        print(f"✗ لم يتم العثور على: {english_text}")

# حفظ الملف المحدث
with open('locale/ar/LC_MESSAGES/django.po', 'w', encoding='utf-8') as f:
    f.write(content)

print("=" * 50)
print(f"تم إضافة {count} ترجمة جديدة!")
print("الانتهاء من المعالجة.")

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكريبت لإيجاد النصوص الإنجليزية التي تحتاج ترجمة
"""
import os
import re

def find_untranslated_english_text():
    """البحث عن النصوص الإنجليزية غير المترجمة"""
    
    print("🔍 البحث عن النصوص الإنجليزية غير المترجمة...")
    
    # قراءة ملف الترجمة الحالي
    translation_file = 'locale/ar/LC_MESSAGES/django.po'
    translated_strings = set()
    
    if os.path.exists(translation_file):
        with open(translation_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # استخراج النصوص المترجمة
            msgid_pattern = r'msgid "([^"]*)"'
            for match in re.finditer(msgid_pattern, content):
                translated_strings.add(match.group(1))
    
    # قائمة النصوص الإنجليزية الشائعة التي يجب ترجمتها
    common_texts_to_translate = [
        # الأساسيات
        "Dashboard", "Home", "Settings", "Profile", "Logout", "Login",
        "Menu", "Close", "Open", "Show", "Hide", "Cancel", "Save", "Delete",
        "Edit", "Add", "New", "Update", "Submit", "Search", "Filter",
        "Clear", "Reset", "Back", "Next", "Previous", "Continue",
        
        # الحالات
        "Active", "Inactive", "Enabled", "Disabled", "Yes", "No",
        "Success", "Error", "Warning", "Info", "Loading", "Please wait",
        
        # التواريخ والأوقات
        "Today", "Yesterday", "Tomorrow", "This week", "This month", 
        "This year", "Last month", "Last year", "Date", "Time",
        
        # المحاسبة
        "Total", "Amount", "Balance", "Credit", "Debit", "Invoice",
        "Receipt", "Payment", "Sales", "Purchases", "Customer", "Supplier",
        "Product", "Inventory", "Revenue", "Expense", "Assets", "Liabilities",
        "Journal", "Account", "Transaction", "Entry",
        
        # الموارد البشرية
        "Employee", "Department", "Position", "Salary", "Attendance",
        "Leave", "Overtime", "Payroll", "Benefits", "Performance",
        
        # التقارير
        "Report", "Reports", "Statistics", "Chart", "Graph", "Export",
        "Print", "Download", "PDF", "Excel", "CSV",
        
        # النظام
        "System", "Admin", "User", "Role", "Permission", "Group",
        "Configuration", "Backup", "Restore", "Import", "Export",
        
        # الرسائل
        "Message", "Alert", "Notification", "Confirmation", "Warning",
        "Error occurred", "Success", "Failed", "Completed", "Processing"
    ]
    
    # العثور على النصوص غير المترجمة
    untranslated = []
    for text in common_texts_to_translate:
        if text not in translated_strings:
            untranslated.append(text)
    
    print("\n📋 النصوص الإنجليزية التي تحتاج ترجمة:")
    print("=" * 50)
    
    if untranslated:
        for i, text in enumerate(untranslated, 1):
            print(f"{i}. {text}")
    else:
        print("✅ جميع النصوص مترجمة!")
    
    print(f"\n📊 عدد النصوص غير المترجمة: {len(untranslated)}")
    
    # اقتراح ترجمات
    suggested_translations = {
        "Dashboard": "لوحة التحكم",
        "Home": "الرئيسية", 
        "Settings": "الإعدادات",
        "Profile": "الملف الشخصي",
        "Logout": "تسجيل الخروج",
        "Login": "تسجيل الدخول",
        "Menu": "القائمة",
        "Close": "إغلاق",
        "Open": "فتح",
        "Show": "عرض",
        "Hide": "إخفاء",
        "Cancel": "إلغاء",
        "Save": "حفظ",
        "Delete": "حذف",
        "Edit": "تعديل",
        "Add": "إضافة",
        "New": "جديد",
        "Update": "تحديث",
        "Submit": "إرسال",
        "Search": "بحث",
        "Filter": "تصفية",
        "Clear": "مسح",
        "Reset": "إعادة تعيين",
        "Back": "رجوع",
        "Next": "التالي",
        "Previous": "السابق",
        "Continue": "متابعة",
        "Active": "نشط",
        "Inactive": "غير نشط",
        "Enabled": "مفعل",
        "Disabled": "معطل",
        "Yes": "نعم",
        "No": "لا",
        "Success": "نجح",
        "Error": "خطأ",
        "Warning": "تحذير",
        "Info": "معلومات",
        "Loading": "جاري التحميل",
        "Please wait": "يرجى الانتظار",
        "Today": "اليوم",
        "Yesterday": "أمس",
        "Tomorrow": "غداً",
        "This week": "هذا الأسبوع",
        "This month": "هذا الشهر",
        "This year": "هذا العام",
        "Last month": "الشهر الماضي",
        "Last year": "العام الماضي",
        "Date": "التاريخ",
        "Time": "الوقت",
        "Total": "الإجمالي",
        "Amount": "المبلغ",
        "Balance": "الرصيد",
        "Credit": "دائن",
        "Debit": "مدين",
        "Invoice": "فاتورة",
        "Receipt": "إيصال",
        "Payment": "دفعة",
        "Sales": "المبيعات",
        "Purchases": "المشتريات",
        "Customer": "العميل",
        "Supplier": "المورد",
        "Product": "المنتج",
        "Inventory": "المخزون",
        "Revenue": "الإيرادات",
        "Expense": "المصروفات",
        "Assets": "الأصول",
        "Liabilities": "الخصوم",
        "Journal": "دفتر اليومية",
        "Account": "الحساب",
        "Transaction": "المعاملة",
        "Entry": "القيد",
        "Employee": "الموظف",
        "Department": "القسم",
        "Position": "المنصب",
        "Salary": "الراتب",
        "Attendance": "الحضور",
        "Leave": "الإجازة",
        "Overtime": "العمل الإضافي",
        "Payroll": "كشف الراتب",
        "Benefits": "المزايا",
        "Performance": "الأداء",
        "Report": "تقرير",
        "Reports": "التقارير",
        "Statistics": "الإحصائيات",
        "Chart": "الرسم البياني",
        "Graph": "المخطط",
        "Export": "تصدير",
        "Print": "طباعة",
        "Download": "تحميل",
        "PDF": "ملف PDF",
        "Excel": "ملف Excel",
        "CSV": "ملف CSV",
        "System": "النظام",
        "Admin": "المدير",
        "User": "المستخدم",
        "Role": "الدور",
        "Permission": "الصلاحية",
        "Group": "المجموعة",
        "Configuration": "التكوين",
        "Backup": "النسخ الاحتياطي",
        "Restore": "الاستعادة",
        "Import": "استيراد",
        "Export": "تصدير",
        "Message": "الرسالة",
        "Alert": "تنبيه",
        "Notification": "الإشعار",
        "Confirmation": "التأكيد",
        "Warning": "تحذير",
        "Error occurred": "حدث خطأ",
        "Success": "نجح",
        "Failed": "فشل",
        "Completed": "مكتمل",
        "Processing": "معالجة"
    }
    
    # إنشاء ملف ترجمات جديد
    if untranslated:
        print("\n📝 إنشاء ملف الترجمات الإضافية...")
        with open('additional_translations.po', 'w', encoding='utf-8') as f:
            f.write("# Additional translations for FinsPilot\n")
            f.write("# Generated automatically\n\n")
            
            for text in untranslated:
                f.write(f'msgid "{text}"\n')
                if text in suggested_translations:
                    f.write(f'msgstr "{suggested_translations[text]}"\n\n')
                else:
                    f.write(f'msgstr ""\n\n')
        
        print("✅ تم إنشاء ملف additional_translations.po")
    
    return untranslated

if __name__ == "__main__":
    find_untranslated_english_text()

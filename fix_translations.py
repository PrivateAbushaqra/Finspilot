#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكريبت لإصلاح ملف الترجمات العربية
يقوم بملء جميع الترجمات الفارغة بالنص العربي المطلوب
"""

import re
import os

def fix_arabic_translations():
    """إصلاح ملف الترجمات العربية"""
    po_file_path = r"c:\Accounting_soft\finspilot\locale\ar\LC_MESSAGES\django.po"
    
    if not os.path.exists(po_file_path):
        print(f"الملف غير موجود: {po_file_path}")
        return False
    
    # قراءة محتوى الملف
    with open(po_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("بدء إصلاح ملف الترجمات...")
    
    # استبدال الترجمات الفارغة بسيط
    content = content.replace('msgstr ""', 'msgstr "تتم الترجمة"')
    
    # تعبير نمطي للعثور على الترجمات الفارغة للنصوص العربية
    arabic_pattern = r'msgid\s+"([^"]*[\u0600-\u06FF][^"]*)"\s*\nmsgstr\s+"[^"]*"'
    
    def fix_arabic_msgstr(match):
        """إصلاح الترجمات للنصوص العربية"""
        msgid_text = match.group(1)
        return f'msgid "{msgid_text}"\nmsgstr "{msgid_text}"'
    
    # إصلاح الترجمات العربية
    content = re.sub(arabic_pattern, fix_arabic_msgstr, content, flags=re.MULTILINE)
    
    # ترجمات محددة للكلمات الإنجليزية الشائعة
    translations = {
        # Navigation
        '"Dashboard"': '"لوحة التحكم"',
        '"Home"': '"الرئيسية"', 
        '"Accounts"': '"الحسابات"',
        '"Sales"': '"المبيعات"',
        '"Purchases"': '"المشتريات"',
        '"Inventory"': '"المخزون"',
        '"HR"': '"الموارد البشرية"',
        '"Human Resources"': '"الموارد البشرية"',
        '"Reports"': '"التقارير"',
        '"Settings"': '"الإعدادات"',
        '"Logout"': '"تسجيل الخروج"',
        
        # Basic Actions
        '"Add"': '"إضافة"',
        '"Edit"': '"تعديل"',
        '"Delete"': '"حذف"',
        '"View"': '"عرض"',
        '"Save"': '"حفظ"',
        '"Cancel"': '"إلغاء"',
        '"Search"': '"بحث"',
        '"Filter"': '"تصفية"',
        '"Export"': '"تصدير"',
        '"Import"': '"استيراد"',
        '"Print"': '"طباعة"',
        
        # HR Module
        '"Employees"': '"الموظفون"',
        '"Employee"': '"موظف"',
        '"Departments"': '"الأقسام"',
        '"Department"': '"قسم"',
        '"Positions"': '"المناصب"',
        '"Position"': '"منصب"',
        '"Attendance"': '"الحضور والانصراف"',
        '"Leave Requests"': '"طلبات الإجازات"',
        '"Payroll"': '"الرواتب"',
        
        # Basic Information
        '"Name"': '"الاسم"',
        '"Description"': '"الوصف"',
        '"Date"': '"التاريخ"',
        '"Status"': '"الحالة"',
        '"Amount"': '"المبلغ"',
        '"Total"': '"الإجمالي"',
        '"Active"': '"نشط"',
        '"Inactive"': '"غير نشط"',
        
        # Messages
        '"Successfully created"': '"تم الإنشاء بنجاح"',
        '"Successfully updated"': '"تم التحديث بنجاح"',
        '"Successfully deleted"': '"تم الحذف بنجاح"',
        '"Error occurred"': '"حدث خطأ"',
        '"Permission denied"': '"تم رفض الإذن"',
        '"Not found"': '"غير موجود"',
        
        # Other common terms
        '"Customer"': '"عميل"',
        '"Customers"': '"العملاء"',
        '"Invoice"': '"فاتورة"',
        '"Invoices"': '"الفواتير"',
        '"Product"': '"منتج"',
        '"Products"': '"المنتجات"',
        '"Supplier"': '"مورد"',
        '"Suppliers"': '"الموردين"',
        '"Company"': '"الشركة"',
        '"User"': '"مستخدم"',
        '"Users"': '"المستخدمون"',
        '"Admin"': '"مدير"',
        '"Manager"': '"مدير"',
        '"Type"': '"النوع"',
        '"Code"': '"الرمز"',
        '"Number"': '"الرقم"',
        '"Price"': '"السعر"',
        '"Quantity"': '"الكمية"',
        '"Email"': '"البريد الإلكتروني"',
        '"Phone"': '"الهاتف"',
        '"Address"': '"العنوان"',
        '"Notes"': '"ملاحظات"',
        '"First Name"': '"الاسم الأول"',
        '"Last Name"': '"الاسم الأخير"',
        '"Today"': '"اليوم"',
        '"Loading..."': '"جاري التحميل..."',
        '"Please wait..."': '"يرجى الانتظار..."',
        '"Yes"': '"نعم"',
        '"No"': '"لا"',
        '"Confirm"': '"تأكيد"',
        '"Success"': '"نجح"',
        '"Error"': '"خطأ"',
        '"Warning"': '"تحذير"',
        '"Information"': '"معلومات"',
        '"Close"': '"إغلاق"',
        '"Back"': '"رجوع"',
        '"Continue"': '"متابعة"',
        '"Submit"': '"إرسال"',
        '"New"': '"جديد"',
        '"Update"': '"تحديث"',
        '"Create"': '"إنشاء"',
        '"Remove"': '"إزالة"',
        '"Show"': '"إظهار"',
        '"Hide"': '"إخفاء"',
        '"Help"': '"مساعدة"',
        '"About"': '"حول"',
        '"Contact"': '"اتصال"',
        '"Language"': '"اللغة"',
        '"Arabic"': '"العربية"',
        '"English"': '"الإنجليزية"',
        '"Balance"': '"الرصيد"',
        '"Debit"': '"مدين"',
        '"Credit"': '"دائن"',
        '"Cash"': '"نقدي"',
        '"Bank"': '"بنك"',
        '"Payment"': '"دفعة"',
        '"Receipt"': '"إيصال"',
        '"Daily"': '"يومي"',
        '"Weekly"': '"أسبوعي"',
        '"Monthly"': '"شهري"',
        '"Yearly"': '"سنوي"',
        '"Total Sales"': '"إجمالي المبيعات"',
        '"Total Purchases"': '"إجمالي المشتريات"',
        '"Stock"': '"المخزون"',
        '"Low Stock"': '"مخزون منخفض"',
        '"Out of Stock"': '"نفد المخزون"',
        '"Enabled"': '"مفعل"',
        '"Disabled"': '"معطل"',
        '"Pending"': '"في الانتظار"',
        '"Approved"': '"موافق عليه"',
        '"Rejected"': '"مرفوض"',
        '"File"': '"ملف"',
        '"Upload"': '"رفع"',
        '"Download"': '"تحميل"',
        '"Actions"': '"الإجراءات"',
        '"Options"': '"الخيارات"',
        '"Previous"': '"السابق"',
        '"Next"': '"التالي"',
        '"Page"': '"صفحة"',
        '"Permissions"': '"الصلاحيات"',
        '"Groups"': '"المجموعات"',
    }
    
    # تطبيق الترجمات المحددة
    for english, arabic in translations.items():
        # استبدال msgstr للكلمات الإنجليزية
        pattern = f'msgid {english}\nmsgstr "تتم الترجمة"'
        replacement = f'msgid {english}\nmsgstr {arabic}'
        content = content.replace(pattern, replacement)
    
    # حفظ الملف المحدث
    with open(po_file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("تم إصلاح ملف الترجمات بنجاح!")
    
    # عد الترجمات المتبقية الفارغة
    empty_count = content.count('msgstr "تتم الترجمة"')
    print(f"عدد الترجمات المتبقية التي تحتاج ترجمة: {empty_count}")
    
    return True

if __name__ == "__main__":
    fix_arabic_translations()

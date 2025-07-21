#!/usr/bin/env python
"""
سكريبت تصدير البيانات من قاعدة البيانات الحالية
يُنشئ نسخة احتياطية يمكن استيرادها لاحقاً
"""

import os
import sys
import django
from datetime import datetime
import json

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.core.management import call_command
from django.core import serializers
from django.apps import apps
from io import StringIO

def export_clean_data():
    """تصدير البيانات بتنظيف للاستيراد الآمن"""
    
    # التطبيقات المهمة للنسخ الاحتياطي
    important_apps = [
        'settings',     # إعدادات الشركة والعملات
        'users',        # المستخدمين
        'accounts',     # الحسابات المحاسبية
        'customers',    # العملاء والموردين  
        'products',     # المنتجات
        'banks',        # الحسابات البنكية
        'cashboxes',    # الصناديق
        'sales',        # المبيعات
        'purchases',    # المشتريات
        'inventory',    # المخزون
        'receipts',     # سندات القبض
        'payments',     # سندات الدفع
        'journal',      # القيود المحاسبية
        'revenues_expenses',  # الإيرادات والمصاريف
        'assets_liabilities', # الأصول والالتزامات
    ]
    
    # النماذج المستبعدة (لأسباب أمنية أو تقنية)
    excluded_models = [
        'sessions.session',           # جلسات المستخدمين
        'admin.logentry',            # سجلات الإدارة
        'contenttypes.contenttype',  # أنواع المحتوى (سيُنشأ تلقائياً)
        'auth.permission',           # الصلاحيات (ستُنشأ تلقائياً)
        'core.auditlog',            # سجلات التدقيق القديمة
    ]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"finspilot_backup_{timestamp}.json"
    clean_backup_filename = f"finspilot_clean_backup_{timestamp}.json"
    
    print("🔄 بدء عملية تصدير البيانات...")
    print(f"📅 التاريخ والوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # تصدير كامل للمراجعة
    print("\n1️⃣ إنشاء نسخة احتياطية كاملة...")
    try:
        with open(backup_filename, 'w', encoding='utf-8') as f:
            call_command('dumpdata', 
                        '--natural-foreign', 
                        '--natural-primary',
                        '--indent=2',
                        stdout=f)
        print(f"✅ تم إنشاء النسخة الكاملة: {backup_filename}")
    except Exception as e:
        print(f"❌ خطأ في النسخة الكاملة: {e}")
        return False
    
    # تصدير منظف للاستيراد
    print("\n2️⃣ إنشاء نسخة احتياطية منظفة للاستيراد...")
    
    # بناء قائمة الاستبعاد
    exclude_args = []
    for model in excluded_models:
        exclude_args.extend(['--exclude', model])
    
    try:
        with open(clean_backup_filename, 'w', encoding='utf-8') as f:
            call_command('dumpdata',
                        '--natural-foreign',
                        '--natural-primary', 
                        '--indent=2',
                        *exclude_args,
                        stdout=f)
        print(f"✅ تم إنشاء النسخة المنظفة: {clean_backup_filename}")
    except Exception as e:
        print(f"❌ خطأ في النسخة المنظفة: {e}")
        return False
    
    # تصدير تطبيق محدد
    print("\n3️⃣ إنشاء نسخ احتياطية للتطبيقات المهمة...")
    for app_name in important_apps:
        app_backup_filename = f"finspilot_{app_name}_backup_{timestamp}.json"
        try:
            with open(app_backup_filename, 'w', encoding='utf-8') as f:
                call_command('dumpdata',
                           app_name,
                           '--natural-foreign',
                           '--natural-primary',
                           '--indent=2',
                           stdout=f)
            print(f"✅ {app_name}: {app_backup_filename}")
        except Exception as e:
            print(f"⚠️ تحذير - {app_name}: {e}")
    
    # إنشاء تقرير
    print("\n📊 إنشاء تقرير النسخة الاحتياطية...")
    create_backup_report(timestamp, backup_filename, clean_backup_filename)
    
    print("\n" + "="*60)
    print("🎉 تم الانتهاء من تصدير البيانات بنجاح!")
    print("="*60)
    print(f"📁 الملفات المُنشأة:")
    print(f"   📄 النسخة الكاملة: {backup_filename}")
    print(f"   🧹 النسخة المنظفة: {clean_backup_filename}")
    print(f"   📋 التقرير: backup_report_{timestamp}.txt")
    print("\n💡 نصائح:")
    print("   - استخدم النسخة المنظفة للاستيراد إلى قاعدة بيانات جديدة")
    print("   - احتفظ بالنسخة الكاملة للمراجعة والأرشفة")
    print("   - تأكد من نسخ الملفات إلى مكان آمن")
    
    return True

def create_backup_report(timestamp, full_backup, clean_backup):
    """إنشاء تقرير مفصل عن النسخة الاحتياطية"""
    
    report_filename = f"backup_report_{timestamp}.txt"
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write("تقرير النسخة الاحتياطية - نظام Finspilot المحاسبي\n")
        f.write("="*60 + "\n\n")
        
        f.write(f"📅 تاريخ النسخة: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"📁 النسخة الكاملة: {full_backup}\n")
        f.write(f"🧹 النسخة المنظفة: {clean_backup}\n\n")
        
        # إحصائيات قاعدة البيانات
        f.write("📊 إحصائيات قاعدة البيانات:\n")
        f.write("-" * 30 + "\n")
        
        try:
            from users.models import User
            from settings.models import Currency, CompanySettings
            from customers.models import Customer
            from products.models import Product
            from sales.models import SalesInvoice
            from purchases.models import PurchaseInvoice
            from journal.models import Account, JournalEntry
            
            f.write(f"👥 المستخدمين: {User.objects.count()}\n")
            f.write(f"💱 العملات: {Currency.objects.count()}\n")
            f.write(f"🏢 إعدادات الشركة: {CompanySettings.objects.count()}\n")
            f.write(f"👨‍💼 العملاء/الموردين: {Customer.objects.count()}\n")
            f.write(f"📦 المنتجات: {Product.objects.count()}\n")
            f.write(f"💰 فواتير المبيعات: {SalesInvoice.objects.count()}\n")
            f.write(f"🛒 فواتير المشتريات: {PurchaseInvoice.objects.count()}\n")
            f.write(f"🏦 الحسابات: {Account.objects.count()}\n")
            f.write(f"📝 القيود المحاسبية: {JournalEntry.objects.count()}\n")
            
        except Exception as e:
            f.write(f"❌ خطأ في جمع الإحصائيات: {e}\n")
        
        f.write("\n📝 ملاحظات:\n")
        f.write("-" * 12 + "\n")
        f.write("- تم استبعاد الجلسات وسجلات التدقيق من النسخة المنظفة\n")
        f.write("- تحقق من صحة البيانات قبل الاستيراد\n")
        f.write("- قم بنسخ الملفات إلى مكان آمن\n")
        f.write("- استخدم النسخة المنظفة للاستيراد\n")

def main():
    """الدالة الرئيسية"""
    
    # التحقق من وجود قاعدة البيانات
    if not os.path.exists('db.sqlite3'):
        print("❌ لا توجد قاعدة بيانات للتصدير")
        return False
    
    # تأكيد العملية
    print("🔄 سيتم تصدير البيانات من قاعدة البيانات الحالية")
    confirm = input("هل تريد المتابعة؟ (y/n): ").lower().strip()
    
    if confirm not in ['y', 'yes', 'نعم']:
        print("❌ تم إلغاء العملية")
        return False
    
    return export_clean_data()

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)

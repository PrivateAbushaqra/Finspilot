#!/usr/bin/env python
"""
فحص حالة قاعدة البيانات والتحقق من صحة الإعداد
"""

import os
import sys
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.core.management import call_command
from django.db import connection
from io import StringIO

def check_database_status():
    """فحص حالة قاعدة البيانات"""
    
    print("=" * 60)
    print("🔍 فحص حالة قاعدة البيانات - نظام Finspilot")
    print("=" * 60)
    print(f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. فحص وجود ملف قاعدة البيانات
    print("\n1️⃣ فحص ملف قاعدة البيانات:")
    if os.path.exists('db.sqlite3'):
        size = os.path.getsize('db.sqlite3')
        print(f"   ✅ الملف موجود - الحجم: {size:,} بايت")
    else:
        print("   ❌ ملف قاعدة البيانات غير موجود")
        return False
    
    # 2. فحص الاتصال بقاعدة البيانات
    print("\n2️⃣ فحص الاتصال:")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("   ✅ الاتصال ناجح")
    except Exception as e:
        print(f"   ❌ فشل الاتصال: {e}")
        return False
    
    # 3. فحص حالة الهجرات
    print("\n3️⃣ فحص حالة الهجرات:")
    try:
        output = StringIO()
        call_command('showmigrations', '--plan', stdout=output)
        migrations_output = output.getvalue()
        
        applied = migrations_output.count('[X]')
        unapplied = migrations_output.count('[ ]')
        
        print(f"   ✅ الهجرات المطبقة: {applied}")
        if unapplied > 0:
            print(f"   ⚠️ الهجرات غير المطبقة: {unapplied}")
        else:
            print("   ✅ جميع الهجرات مطبقة")
            
    except Exception as e:
        print(f"   ❌ خطأ في فحص الهجرات: {e}")
    
    # 4. فحص البيانات الأساسية
    print("\n4️⃣ فحص البيانات الأساسية:")
    
    try:
        from users.models import User
        users_count = User.objects.count()
        superusers_count = User.objects.filter(is_superuser=True).count()
        print(f"   👥 المستخدمين: {users_count} (منهم {superusers_count} مدير)")
        
        # فحص وجود superadmin
        if User.objects.filter(username='superadmin').exists():
            print("   ✅ المستخدم superadmin موجود")
        else:
            print("   ⚠️ المستخدم superadmin غير موجود")
            
    except Exception as e:
        print(f"   ❌ خطأ في فحص المستخدمين: {e}")
    
    try:
        from settings.models import Currency, CompanySettings
        currencies_count = Currency.objects.count()
        company_settings_count = CompanySettings.objects.count()
        print(f"   💱 العملات: {currencies_count}")
        print(f"   🏢 إعدادات الشركة: {company_settings_count}")
        
        if currencies_count == 0:
            print("   ⚠️ لا توجد عملات - قم بتشغيل create_default_currencies.py")
            
    except Exception as e:
        print(f"   ❌ خطأ في فحص الإعدادات: {e}")
    
    try:
        from journal.models import Account
        accounts_count = Account.objects.count()
        print(f"   🏦 الحسابات المحاسبية: {accounts_count}")
        
        if accounts_count == 0:
            print("   ⚠️ لا توجد حسابات - قم بتشغيل create_default_accounts.py")
            
    except Exception as e:
        print(f"   ❌ خطأ في فحص الحسابات: {e}")
    
    # 5. فحص البيانات التشغيلية
    print("\n5️⃣ فحص البيانات التشغيلية:")
    
    try:
        from customers.models import Customer
        from products.models import Product
        from sales.models import SalesInvoice
        from purchases.models import PurchaseInvoice
        
        customers_count = Customer.objects.count()
        products_count = Product.objects.count()
        sales_count = SalesInvoice.objects.count()
        purchases_count = PurchaseInvoice.objects.count()
        
        print(f"   👨‍💼 العملاء/الموردين: {customers_count}")
        print(f"   📦 المنتجات: {products_count}")
        print(f"   💰 فواتير المبيعات: {sales_count}")
        print(f"   🛒 فواتير المشتريات: {purchases_count}")
        
    except Exception as e:
        print(f"   ❌ خطأ في فحص البيانات التشغيلية: {e}")
    
    # 6. فحص التطبيقات
    print("\n6️⃣ فحص التطبيقات المثبتة:")
    
    from django.apps import apps
    installed_apps = [app.label for app in apps.get_app_configs()]
    
    required_apps = [
        'core', 'users', 'settings', 'accounts', 'customers', 'products',
        'sales', 'purchases', 'inventory', 'banks', 'cashboxes', 'journal',
        'receipts', 'payments', 'revenues_expenses', 'assets_liabilities'
    ]
    
    print(f"   📱 التطبيقات المثبتة: {len(installed_apps)}")
    
    missing_apps = []
    for app in required_apps:
        if app in installed_apps:
            print(f"   ✅ {app}")
        else:
            print(f"   ❌ {app} - غير موجود")
            missing_apps.append(app)
    
    if missing_apps:
        print(f"   ⚠️ تطبيقات مفقودة: {', '.join(missing_apps)}")
    
    # 7. التقييم العام
    print("\n7️⃣ التقييم العام:")
    
    issues = []
    
    if not os.path.exists('db.sqlite3'):
        issues.append("ملف قاعدة البيانات مفقود")
    
    if unapplied > 0:
        issues.append(f"{unapplied} هجرات غير مطبقة")
        
    try:
        if not User.objects.filter(username='superadmin').exists():
            issues.append("المستخدم superadmin مفقود")
        
        if Currency.objects.count() == 0:
            issues.append("العملات غير معرّفة")
            
        if Account.objects.count() == 0:
            issues.append("الحسابات المحاسبية غير معرّفة")
    except:
        issues.append("خطأ في الوصول للبيانات")
    
    if missing_apps:
        issues.append(f"تطبيقات مفقودة: {len(missing_apps)}")
    
    if not issues:
        print("   🎉 قاعدة البيانات سليمة وجاهزة للاستخدام!")
        print("\n💡 للبدء:")
        print("   python manage.py runserver")
        print("   ثم اذهب إلى: http://127.0.0.1:8000/admin/")
        print("   اسم المستخدم: superadmin")
        print("   كلمة المرور: password")
        
    else:
        print("   ⚠️ تم العثور على مشاكل:")
        for issue in issues:
            print(f"      - {issue}")
        
        print("\n🔧 للإصلاح:")
        print("   .\setup_database.ps1 -ResetDatabase")
        print("   أو")
        print("   .\setup_system.ps1 -FullSetup")
    
    print("\n" + "=" * 60)
    return len(issues) == 0

if __name__ == "__main__":
    try:
        success = check_database_status()
        if not success:
            print("❌ تم العثور على مشاكل في قاعدة البيانات")
            sys.exit(1)
        else:
            print("✅ قاعدة البيانات سليمة")
            sys.exit(0)
    except Exception as e:
        print(f"❌ خطأ في فحص قاعدة البيانات: {e}")
        sys.exit(1)

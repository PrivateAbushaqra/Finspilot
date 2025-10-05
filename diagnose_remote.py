"""
سكريبت تشخيص مشاكل الاستعادة على الريموت

استخدام:
1. انسخ هذا الملف إلى المجلد الرئيسي للمشروع على الريموت
2. نفّذ: python diagnose_remote.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from core.models import AuditLog
from datetime import datetime, timedelta

def print_header(title):
    print("\n" + "="*80)
    print(title)
    print("="*80)

def count_all_data():
    """حساب جميع السجلات في قاعدة البيانات"""
    print_header("1️⃣ حساب السجلات في قاعدة البيانات")
    
    total = 0
    records = {}
    
    for app_config in apps.get_app_configs():
        # تجاهل تطبيقات Django الداخلية
        if app_config.name.startswith('django.'):
            continue
            
        for model in app_config.get_models():
            try:
                count = model.objects.count()
                if count > 0:
                    label = model._meta.label
                    records[label] = count
                    total += count
            except Exception as e:
                pass
    
    print(f"\n📊 إجمالي السجلات: {total}")
    print(f"📊 عدد الجداول: {len(records)}")
    
    if total == 0:
        print("\n❌ لا توجد أي بيانات في قاعدة البيانات!")
        print("   السبب المحتمل: عملية الاستعادة فشلت أو لم تكتمل")
        return False
    
    print("\n🔝 أكبر 15 جدول:")
    sorted_records = sorted(records.items(), key=lambda x: x[1], reverse=True)[:15]
    for label, count in sorted_records:
        print(f"   - {label}: {count} سجل")
    
    return True

def check_users():
    """التحقق من المستخدمين"""
    print_header("2️⃣ فحص المستخدمين")
    
    User = get_user_model()
    
    total_users = User.objects.count()
    superusers = User.objects.filter(is_superuser=True).count()
    active_users = User.objects.filter(is_active=True).count()
    
    print(f"\n👥 إجمالي المستخدمين: {total_users}")
    print(f"🔐 المستخدمين ذوي الصلاحيات العليا: {superusers}")
    print(f"✅ المستخدمين النشطين: {active_users}")
    
    if total_users == 0:
        print("\n❌ لا يوجد أي مستخدمين!")
        print("   السبب: عملية الاستعادة لم تستعد جدول المستخدمين")
        return False
    
    if superusers == 0:
        print("\n⚠️ لا يوجد مستخدمين بصلاحيات عليا!")
        
    print("\n📋 قائمة المستخدمين:")
    for user in User.objects.all()[:10]:
        status = "🔐" if user.is_superuser else "👤"
        active = "✅" if user.is_active else "❌"
        print(f"   {status} {user.username} {active}")
    
    return True

def check_recent_audit_logs():
    """فحص سجلات الأحداث الأخيرة"""
    print_header("3️⃣ فحص سجلات الأحداث (آخر 24 ساعة)")
    
    try:
        yesterday = datetime.now() - timedelta(days=1)
        recent_logs = AuditLog.objects.filter(
            timestamp__gte=yesterday
        ).order_by('-timestamp')[:20]
        
        if recent_logs.count() == 0:
            print("\n⚠️ لا توجد سجلات أحداث في آخر 24 ساعة")
        else:
            print(f"\n📝 آخر {recent_logs.count()} حدث:")
            for log in recent_logs:
                user = log.user.username if log.user else 'system'
                print(f"   [{log.timestamp.strftime('%H:%M:%S')}] {user}: {log.action_type}")
                if 'restore' in log.action_type.lower() or 'backup' in log.action_type.lower():
                    print(f"      📌 {log.description}")
        
        # البحث عن سجلات الاستعادة
        restore_logs = AuditLog.objects.filter(
            action_type__icontains='restore'
        ).order_by('-timestamp')[:5]
        
        if restore_logs.count() > 0:
            print(f"\n🔄 آخر عمليات استعادة:")
            for log in restore_logs:
                user = log.user.username if log.user else 'system'
                print(f"   [{log.timestamp.strftime('%Y-%m-%d %H:%M')}] {user}")
                print(f"      {log.description}")
                
    except Exception as e:
        print(f"\n❌ خطأ في قراءة سجلات الأحداث: {e}")

def check_important_data():
    """فحص البيانات المهمة"""
    print_header("4️⃣ فحص البيانات الأساسية")
    
    checks = [
        ('المنتجات', 'products.Product'),
        ('العملاء', 'customers.Customer'),
        ('فواتير المبيعات', 'sales.SalesInvoice'),
        ('فواتير المشتريات', 'purchases.PurchaseInvoice'),
        ('الحسابات', 'journal.Account'),
        ('القيود المحاسبية', 'journal.JournalEntry'),
        ('الصناديق', 'cashboxes.Cashbox'),
        ('الحسابات البنكية', 'banks.BankAccount'),
    ]
    
    has_data = False
    
    for name, model_label in checks:
        try:
            app_label, model_name = model_label.split('.')
            model = apps.get_model(app_label, model_name)
            count = model.objects.count()
            
            if count > 0:
                print(f"   ✅ {name}: {count}")
                has_data = True
            else:
                print(f"   ⚠️ {name}: فارغ")
        except Exception as e:
            print(f"   ❌ {name}: خطأ ({e})")
    
    return has_data

def check_database_sequences():
    """فحص sequences في PostgreSQL"""
    print_header("5️⃣ فحص Database Sequences")
    
    try:
        with connection.cursor() as cursor:
            # جلب معلومات sequences
            cursor.execute("""
                SELECT 
                    schemaname,
                    sequencename,
                    last_value
                FROM pg_sequences 
                WHERE schemaname = 'public'
                ORDER BY last_value DESC
                LIMIT 10
            """)
            
            sequences = cursor.fetchall()
            
            if sequences:
                print("\n📊 أكبر 10 sequences:")
                for schema, seq_name, last_val in sequences:
                    print(f"   - {seq_name}: {last_val}")
            else:
                print("\n⚠️ لا توجد sequences")
                
    except Exception as e:
        print(f"\n❌ خطأ في فحص sequences: {e}")
        print("   ملاحظة: قد تكون قاعدة البيانات ليست PostgreSQL")

def check_database_connection():
    """فحص الاتصال بقاعدة البيانات"""
    print_header("0️⃣ فحص الاتصال بقاعدة البيانات")
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"\n✅ الاتصال بقاعدة البيانات ناجح")
            print(f"📊 الإصدار: {version}")
            
            # حجم قاعدة البيانات
            cursor.execute("SELECT pg_database_size(current_database())")
            size_bytes = cursor.fetchone()[0]
            size_mb = size_bytes / (1024 * 1024)
            print(f"💾 حجم قاعدة البيانات: {size_mb:.2f} MB")
            
    except Exception as e:
        print(f"\n❌ فشل الاتصال بقاعدة البيانات: {e}")
        return False
    
    return True

def main():
    print("\n" + "🔍" * 40)
    print("تشخيص مشاكل الاستعادة على الريموت")
    print("🔍" * 40)
    
    # فحص الاتصال
    if not check_database_connection():
        print("\n❌ توقف التشخيص: لا يمكن الاتصال بقاعدة البيانات")
        return
    
    # فحص البيانات
    has_data = count_all_data()
    
    # فحص المستخدمين
    has_users = check_users()
    
    # فحص السجلات
    check_recent_audit_logs()
    
    # فحص البيانات المهمة
    has_important_data = check_important_data()
    
    # فحص sequences
    check_database_sequences()
    
    # الخلاصة
    print_header("📋 الخلاصة والتوصيات")
    
    if not has_data:
        print("\n❌ المشكلة: قاعدة البيانات فارغة تماماً")
        print("\n💡 الحل:")
        print("   1. تأكد من أن ملف النسخة الاحتياطية صحيح")
        print("   2. جرّب استعادة النسخة مرة أخرى")
        print("   3. فعّل خيار 'مسح البيانات قبل الاستعادة'")
        print("   4. افحص سجلات الأخطاء (Logs) على Render")
        
    elif not has_users:
        print("\n⚠️ المشكلة: لا يوجد مستخدمين")
        print("\n💡 الحل:")
        print("   1. قد تكون عملية الاستعادة فشلت في جدول المستخدمين")
        print("   2. أنشئ مستخدم superuser جديد: python manage.py createsuperuser")
        print("   3. جرّب استعادة النسخة مرة أخرى")
        
    elif not has_important_data:
        print("\n⚠️ المشكلة: البيانات الأساسية مفقودة")
        print("\n💡 الحل:")
        print("   1. عملية الاستعادة لم تكتمل بشكل صحيح")
        print("   2. جرّب استعادة النسخة مرة أخرى مع تفعيل 'مسح البيانات'")
        print("   3. افحص سجلات الأخطاء للتأكد من عدم وجود أخطاء FK أو Integrity")
        
    else:
        print("\n✅ قاعدة البيانات تحتوي على بيانات")
        print("\n💡 إذا كنت لا ترى البيانات في الواجهة:")
        print("   1. قم بتسجيل الخروج ثم الدخول مرة أخرى")
        print("   2. امسح Cache المتصفح")
        print("   3. تأكد من أن المستخدم لديه صلاحيات العرض")
        print("   4. افحص الفلاتر المطبقة على قوائم البيانات")
    
    print("\n" + "="*80)
    print("انتهى التشخيص")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()

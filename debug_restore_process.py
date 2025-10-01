#!/usr/bin/env python
"""
سكريپت مراقبة وتشخيص عملية استعادة النسخ الاحتياطية
"""
import os
import sys
import django
import json
import logging
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.apps import apps
from django.db import connection

User = get_user_model()

# إعداد التسجيل
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def count_records_by_app():
    """عد السجلات حسب التطبيق"""
    total_records = 0
    app_counts = {}
    
    for app_config in apps.get_app_configs():
        app_name = app_config.name
        if app_name.startswith('django.') or app_name in ['__pycache__']:
            continue
            
        models = app_config.get_models()
        app_total = 0
        
        for model in models:
            try:
                count = model.objects.count()
                app_total += count
            except Exception:
                pass
        
        if app_total > 0:
            app_counts[app_name] = app_total
            total_records += app_total
    
    return total_records, app_counts

def test_restore_with_debugging(filepath, file_type):
    """اختبار استعادة مع تشخيص مفصل"""
    print(f"\n🔍 تشخيص عملية الاستعادة لملف {file_type}")
    print(f"📄 الملف: {os.path.basename(filepath)}")
    print("=" * 60)
    
    # 1. فحص الملف قبل الاستعادة
    print("1️⃣ فحص الملف:")
    try:
        file_size = os.path.getsize(filepath)
        print(f"   ✅ حجم الملف: {file_size:,} بايت")
        
        if file_type == 'JSON':
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"   ✅ بنية JSON صحيحة")
            print(f"   📊 معلومات الملف:")
            print(f"      - عدد الجداول في الملف: {data['metadata'].get('total_tables', 0)}")
            print(f"      - عدد السجلات في الملف: {data['metadata'].get('total_records', 0)}")
            print(f"      - عدد التطبيقات: {len(data.get('data', {}))}")
        
        elif file_type == 'XLSX':
            import openpyxl
            workbook = openpyxl.load_workbook(filepath, read_only=True)
            sheets = workbook.sheetnames
            print(f"   ✅ بنية XLSX صحيحة")
            print(f"   📊 معلومات الملف:")
            print(f"      - عدد أوراق العمل: {len(sheets)}")
            workbook.close()
            
    except Exception as e:
        print(f"   ❌ خطأ في فحص الملف: {e}")
        return False
    
    # 2. فحص قاعدة البيانات قبل الاستعادة
    print(f"\n2️⃣ حالة قاعدة البيانات قبل الاستعادة:")
    before_total, before_apps = count_records_by_app()
    print(f"   📊 إجمالي السجلات: {before_total}")
    for app_name, count in before_apps.items():
        print(f"      - {app_name}: {count} سجل")
    
    # 3. تنفيذ عملية الاستعادة
    print(f"\n3️⃣ تنفيذ عملية الاستعادة:")
    try:
        # إنشاء عميل اختبار
        client = Client()
        
        # تسجيل الدخول
        user = User.objects.get(username='super')
        client.force_login(user)
        print("   ✅ تم تسجيل الدخول")
        
        # قراءة الملف
        with open(filepath, 'rb') as f:
            file_content = f.read()
        
        filename = os.path.basename(filepath)
        content_type = 'application/json' if file_type == 'JSON' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        uploaded_file = SimpleUploadedFile(
            filename,
            file_content,
            content_type=content_type
        )
        print("   ✅ تم تحضير الملف للرفع")
        
        # إرسال طلب الاستعادة
        print("   🔄 إرسال طلب الاستعادة...")
        response = client.post('/ar/backup/restore-backup/', {
            'clear_data': 'false',  # عدم مسح البيانات
        }, files={'backup_file': uploaded_file})
        
        print(f"   📡 رد الخادم: HTTP {response.status_code}")
        
        # فحص رد الخادم
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"   📄 استجابة JSON:")
                print(f"      - success: {result.get('success', 'غير محدد')}")
                print(f"      - message: {result.get('message', 'لا توجد رسالة')}")
                if 'error' in result:
                    print(f"      - error: {result.get('error')}")
                if 'progress_id' in result:
                    print(f"      - progress_id: {result.get('progress_id')}")
                    
                if result.get('success'):
                    print("   ✅ بدأ النظام عملية الاستعادة")
                else:
                    print(f"   ❌ النظام رفض الاستعادة: {result.get('error', 'سبب غير معروف')}")
                    return False
                    
            except json.JSONDecodeError:
                # محاولة قراءة كـ HTML
                content = response.content.decode('utf-8', errors='ignore')
                print(f"   📄 استجابة HTML/Text:")
                print(f"      محتوى الاستجابة (أول 500 حرف): {content[:500]}")
                
                # البحث عن مؤشرات النجاح
                success_indicators = ['success', 'started', 'تم بدء', 'نجح']
                is_success = any(indicator in content.lower() for indicator in success_indicators)
                
                if is_success:
                    print("   ✅ يبدو أن العملية بدأت (استجابة HTML)")
                else:
                    print("   ❌ لا توجد مؤشرات نجاح في الاستجابة")
                    return False
        else:
            print(f"   ❌ خطأ HTTP: {response.status_code}")
            try:
                content = response.content.decode('utf-8', errors='ignore')
                print(f"      محتوى الخطأ: {content[:300]}")
            except:
                pass
            return False
            
    except Exception as e:
        print(f"   ❌ خطأ في عملية الاستعادة: {e}")
        return False
    
    # 4. انتظار قصير ثم فحص النتائج
    print(f"\n4️⃣ فحص النتائج بعد الاستعادة:")
    import time
    time.sleep(2)  # انتظار قصير
    
    after_total, after_apps = count_records_by_app()
    print(f"   📊 إجمالي السجلات بعد الاستعادة: {after_total}")
    
    # مقارنة النتائج
    if after_total > before_total:
        difference = after_total - before_total
        print(f"   ✅ تمت إضافة {difference} سجل جديد")
        
        print("   📋 التغييرات في التطبيقات:")
        for app_name in set(list(before_apps.keys()) + list(after_apps.keys())):
            before_count = before_apps.get(app_name, 0)
            after_count = after_apps.get(app_name, 0)
            if after_count != before_count:
                change = after_count - before_count
                print(f"      - {app_name}: {before_count} → {after_count} ({change:+d})")
        
        return True
    elif after_total == before_total:
        print("   ⚠️ لم تتم إضافة أي سجلات جديدة")
        print("   💡 قد يكون السبب:")
        print("      - البيانات موجودة مسبقاً")
        print("      - العملية لم تكتمل بعد")
        print("      - مشكلة في عملية الاستعادة")
        return False
    else:
        print("   ❌ عدد السجلات قل! هذا غير متوقع")
        return False

def main():
    """الدالة الرئيسية"""
    print("🔍 تشخيص مشكلة عدم استعادة البيانات")
    print("=" * 60)
    
    # اختبار الملفين
    backup_dir = "C:/Accounting_soft/finspilot/Backup_files"
    test_files = [
        (os.path.join(backup_dir, "backup_20250930_211406.json"), "JSON"),
        # (os.path.join(backup_dir, "backup_20250930_123432.xlsx"), "XLSX"),  # نختبر JSON أولاً
    ]
    
    results = []
    
    for filepath, file_type in test_files:
        if os.path.exists(filepath):
            success = test_restore_with_debugging(filepath, file_type)
            results.append({
                'file': os.path.basename(filepath),
                'type': file_type,
                'success': success
            })
        else:
            print(f"❌ الملف غير موجود: {filepath}")
    
    # النتائج النهائية
    print(f"\n{'='*60}")
    print("🎯 النتائج النهائية:")
    print("=" * 60)
    
    successful_restores = [r for r in results if r['success']]
    
    if successful_restores:
        print("✅ الملفات التي تمت استعادتها بنجاح:")
        for result in successful_restores:
            print(f"   - {result['file']} ({result['type']})")
    
    failed_restores = [r for r in results if not r['success']]
    if failed_restores:
        print("❌ الملفات التي فشلت في الاستعادة:")
        for result in failed_restores:
            print(f"   - {result['file']} ({result['type']})")
    
    if not successful_restores:
        print("\n💡 توصيات لحل المشكلة:")
        print("1. تحقق من logs النظام")
        print("2. تحقق من صلاحيات قاعدة البيانات")
        print("3. تحقق من إعدادات Django")
        print("4. تحقق من كود دالة الاستعادة")

if __name__ == "__main__":
    main()
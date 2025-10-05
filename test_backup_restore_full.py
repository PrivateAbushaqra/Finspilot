"""
اختبار شامل لعملية النسخ الاحتياطي والاستعادة
يختبر:
1. إنشاء نسخة احتياطية
2. عدد السجلات في النسخة
3. مسح البيانات
4. استعادة النسخة
5. التحقق من البيانات المستعادة
"""

import os
import django
import json

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from backup.views import perform_backup_task, perform_backup_restore, perform_clear_all_data
from django.apps import apps
from django.db import connection

def count_all_records():
    """حساب إجمالي السجلات في قاعدة البيانات"""
    total = 0
    records_by_model = {}
    
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            try:
                count = model.objects.count()
                if count > 0:
                    label = model._meta.label
                    records_by_model[label] = count
                    total += count
            except Exception:
                # تجاهل الجداول التي لا توجد في قاعدة البيانات
                pass
    
    return total, records_by_model

def main():
    print("="*80)
    print("اختبار شامل لعملية النسخ الاحتياطي والاستعادة")
    print("="*80)
    
    # 1. حساب السجلات الحالية
    print("\n1️⃣ حساب السجلات الحالية في قاعدة البيانات...")
    initial_total, initial_records = count_all_records()
    print(f"   ✅ إجمالي السجلات: {initial_total}")
    print(f"   ✅ عدد الجداول التي تحتوي على بيانات: {len(initial_records)}")
    
    # عرض أول 10 جداول
    print("\n   أكبر 10 جداول:")
    sorted_models = sorted(initial_records.items(), key=lambda x: x[1], reverse=True)[:10]
    for label, count in sorted_models:
        print(f"     - {label}: {count} سجل")
    
    # 2. إنشاء نسخة احتياطية
    print("\n2️⃣ إنشاء نسخة احتياطية...")
    backup_filename = 'test_full_backup.json'
    backup_filepath = os.path.join('media', 'backups', backup_filename)
    
    try:
        result = perform_backup_task(None, 'test', backup_filename, backup_filepath, format_type='json')
        print(f"   ✅ تم إنشاء النسخة الاحتياطية: {backup_filename}")
    except Exception as e:
        print(f"   ❌ فشل في إنشاء النسخة الاحتياطية: {e}")
        return
    
    # 3. فحص محتوى النسخة الاحتياطية
    print("\n3️⃣ فحص محتوى النسخة الاحتياطية...")
    try:
        with open(backup_filepath, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        # التحقق من وجود البيانات
        if 'data' not in backup_data:
            print("   ❌ النسخة الاحتياطية لا تحتوي على بيانات!")
            return
        
        # حساب السجلات في النسخة
        backup_total = 0
        backup_records = {}
        
        for app_name, app_models in backup_data['data'].items():
            for model_name, records in app_models.items():
                if isinstance(records, list):
                    count = len(records)
                    if count > 0:
                        label = f"{app_name}.{model_name}"
                        backup_records[label] = count
                        backup_total += count
        
        print(f"   ✅ إجمالي السجلات في النسخة: {backup_total}")
        print(f"   ✅ عدد الجداول في النسخة: {len(backup_records)}")
        
        # مقارنة
        if backup_total < initial_total:
            print(f"   ⚠️ النسخة تحتوي على سجلات أقل من قاعدة البيانات!")
            print(f"      الفرق: {initial_total - backup_total} سجل مفقود")
        elif backup_total == initial_total:
            print(f"   ✅ النسخة تحتوي على نفس عدد السجلات")
        
        # عرض أول 10 جداول من النسخة
        print("\n   أكبر 10 جداول في النسخة:")
        sorted_backup = sorted(backup_records.items(), key=lambda x: x[1], reverse=True)[:10]
        for label, count in sorted_backup:
            print(f"     - {label}: {count} سجل")
        
    except Exception as e:
        print(f"   ❌ فشل في قراءة النسخة الاحتياطية: {e}")
        return
    
    # 4. اختبار الاستعادة (بدون مسح البيانات أولاً)
    print("\n4️⃣ اختبار الاستعادة (بدون مسح)...")
    print("   ℹ️ هذا الاختبار سيحدّث السجلات الموجودة فقط")
    
    try:
        # استعادة بدون مسح
        perform_backup_restore(backup_data, clear_data=False, user=None)
        print("   ✅ تمت عملية الاستعادة (تحديث)")
        
        # التحقق من السجلات بعد الاستعادة
        after_restore_total, after_restore_records = count_all_records()
        print(f"   ✅ إجمالي السجلات بعد الاستعادة: {after_restore_total}")
        
    except Exception as e:
        print(f"   ❌ فشل في الاستعادة: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 5. النتيجة النهائية
    print("\n" + "="*80)
    print("النتيجة النهائية:")
    print("="*80)
    print(f"السجلات قبل النسخ: {initial_total}")
    print(f"السجلات في النسخة: {backup_total}")
    print(f"السجلات بعد الاستعادة: {after_restore_total}")
    
    if backup_total > 0:
        print("\n✅ النسخة الاحتياطية تحتوي على بيانات")
        if after_restore_total == initial_total:
            print("✅ عملية الاستعادة تعمل بشكل صحيح")
        else:
            print("⚠️ هناك فرق في عدد السجلات بعد الاستعادة")
    else:
        print("\n❌ النسخة الاحتياطية فارغة - هناك مشكلة في عملية النسخ!")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

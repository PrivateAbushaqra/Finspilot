#!/usr/bin/env python3
"""
سكريبت اختبار بسيط لمسح البيانات في عملية الاستعادة
"""
import os
import sys
import json
import time
import requests
from datetime import datetime

# إعداد Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')

import django
django.setup()

def count_database_records():
    """عد السجلات في قاعدة البيانات"""
    from django.apps import apps
    total = 0
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            if model._meta.managed:
                count = model.objects.count()
                total += count
    return total

def test_clear_data():
    """اختبار مسح البيانات"""
    print("🚀 بدء اختبار مسح البيانات")
    print("=" * 50)

    # قراءة النسخة الاحتياطية
    with open('test_small_backup.json', 'r', encoding='utf-8') as f:
        backup_data = json.load(f)

    print(f"تم قراءة النسخة الاحتياطية: {len(backup_data)} سجل")

    # عد السجلات قبل المسح
    records_before = count_database_records()
    print(f"السجلات قبل المسح: {records_before}")

    # استدعاء دالة مسح البيانات مباشرة
    from backup.views import perform_backup_restore

    print("بدء مسح البيانات...")
    start_time = time.time()

    try:
        result = perform_backup_restore(backup_data, clear_data=True, user=None)
        end_time = time.time()

        if result:
            print("✅ تم مسح البيانات بنجاح")
            print(".2f")
            # عد السجلات بعد المسح
            records_after = count_database_records()
            print(f"السجلات بعد المسح: {records_after}")
            print(f"تم مسح: {records_before - records_after} سجل")

            return True
        else:
            print("❌ فشل في مسح البيانات")
            return False

    except Exception as e:
        end_time = time.time()
        print(f"❌ خطأ في مسح البيانات: {str(e)}")
        print(".2f")
        return False

if __name__ == "__main__":
    success = test_clear_data()
    sys.exit(0 if success else 1)
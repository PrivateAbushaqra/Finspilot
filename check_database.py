#!/usr/bin/env python
"""
سكريبت للتحقق من نوع قاعدة البيانات المستخدمة في Finspilot
يمكن تشغيله محلياً أو على Render.com
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.db import connection

def check_database():
    """التحقق من معلومات قاعدة البيانات"""
    print("🔍 فحص قاعدة البيانات...")
    print("=" * 50)

    # معلومات قاعدة البيانات
    db_info = {
        'نوع قاعدة البيانات': connection.vendor,
        'اسم قاعدة البيانات': connection.settings_dict.get('NAME', 'غير محدد'),
        'المضيف': connection.settings_dict.get('HOST', 'غير محدد'),
        'المنفذ': connection.settings_dict.get('PORT', 'غير محدد'),
        'محرك قاعدة البيانات': connection.settings_dict.get('ENGINE', 'غير محدد'),
    }

    # طباعة المعلومات
    for key, value in db_info.items():
        print(f"{key}: {value}")

    print("=" * 50)

    # التحقق من النوع
    if connection.vendor.lower() == 'postgresql':
        print("✅ ممتاز! التطبيق يستخدم PostgreSQL")
        print("✅ هذا يعني أن النشر على Render.com سيكون مع PostgreSQL أيضاً")
        return True
    elif connection.vendor.lower() == 'sqlite':
        print("⚠️  تحذير: التطبيق يستخدم SQLite")
        print("⚠️  SQLite مناسب للتطوير فقط، ليس للإنتاج")
        return False
    else:
        print(f"❓ نوع قاعدة بيانات غير معروف: {connection.vendor}")
        return False

def test_connection():
    """اختبار الاتصال بقاعدة البيانات"""
    print("\n🔗 اختبار الاتصال...")
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        print("✅ الاتصال بقاعدة البيانات ناجح")
        return True
    except Exception as e:
        print(f"❌ فشل في الاتصال: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Finspilot - فحص قاعدة البيانات")
    print("=" * 50)

    # فحص قاعدة البيانات
    is_postgres = check_database()

    # اختبار الاتصال
    connection_ok = test_connection()

    print("\n" + "=" * 50)
    if is_postgres and connection_ok:
        print("🎉 كل شيء يعمل بشكل صحيح!")
        print("🎉 التطبيق جاهز للنشر على Render.com مع PostgreSQL")
        sys.exit(0)
    else:
        print("⚠️  يرجى التحقق من إعدادات قاعدة البيانات")
        sys.exit(1)
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.conf import settings

db_config = settings.DATABASES['default']
engine = db_config['ENGINE']
name = db_config['NAME']

print("="*60)
print("معلومات قاعدة البيانات الحالية")
print("="*60)
print(f"محرك قاعدة البيانات: {engine}")
print(f"اسم قاعدة البيانات: {name}")

if 'sqlite' in engine.lower():
    print("\n✅ النوع: SQLite")
    print("📁 الملف:", name)
    if os.path.exists(str(name)):
        size = os.path.getsize(str(name)) / (1024 * 1024)
        print(f"📊 الحجم: {size:.2f} MB")
    else:
        print("⚠️ الملف غير موجود!")
elif 'postgres' in engine.lower():
    print("\n✅ النوع: PostgreSQL")
    print(f"🔗 المضيف: {db_config.get('HOST', 'N/A')}")
    print(f"🔌 المنفذ: {db_config.get('PORT', 'N/A')}")
    print(f"👤 المستخدم: {db_config.get('USER', 'N/A')}")
else:
    print(f"\n❓ نوع غير معروف: {engine}")

print("="*60)

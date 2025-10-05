"""
سكريبت لحذف السيجنالات المكررة من sales/signals.py
"""

file_path = 'sales/signals.py'

print("=" * 70)
print("🔧 حذف السيجنالات المكررة من sales/signals.py")
print("=" * 70)

# قراءة الملف
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

total_lines = len(lines)
print(f"\n📊 عدد الأسطر الأصلي: {total_lines}")

# الاحتفاظ بأول 460 سطر فقط (السيجنالات الأصلية)
original_signals = lines[:460]

print(f"📊 عدد الأسطر بعد الحذف: {len(original_signals)}")
print(f"🗑️  عدد الأسطر المحذوفة: {total_lines - len(original_signals)}")

# إنشاء نسخة احتياطية
backup_path = file_path + '.backup_duplicates'
with open(backup_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print(f"\n💾 تم إنشاء نسخة احتياطية: {backup_path}")

# حفظ الملف المُعدّل
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(original_signals)

print("\n✅ تم حذف السيجنالات المكررة بنجاح!")
print("\n" + "=" * 70)
print("📋 الخطوة التالية:")
print("=" * 70)
print("اختبر إنشاء فاتورة مبيعات جديدة للتأكد من عدم وجود أخطاء")
print("=" * 70)

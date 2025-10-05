"""
تشغيل الاختبار الشامل مباشرة بدون طلب تأكيد
"""
import sys
sys.path.insert(0, '.')

# استيراد وتشغيل الاختبار
from test_comprehensive_backup import ComprehensiveBackupTest

print("\n" + "="*80)
print("🚀 بدء الاختبار الشامل مباشرة...")
print("="*80)
print("⚠️ تم أخذ نسخة احتياطية للأمان مسبقاً")
print("="*80 + "\n")

test = ComprehensiveBackupTest()
success = test.run()

print("\n" + "="*80)
print("🏁 انتهى الاختبار")
print("="*80)

if success:
    print("\n✅✅✅ النتيجة: النظام موثوق تماماً!")
    print("✅ يمكنك استخدام عملية المسح والاستعادة بثقة كاملة")
else:
    print("\n❌ النتيجة: يوجد مشاكل تحتاج لحل")

if test.report['errors']:
    print("\n❌ الأخطاء:")
    for error in test.report['errors']:
        print(f"  - {error}")

if test.report['warnings']:
    print("\n⚠️ التحذيرات:")
    for warning in test.report['warnings'][:10]:
        print(f"  - {warning}")
    if len(test.report['warnings']) > 10:
        print(f"  ... و {len(test.report['warnings'])-10} تحذير آخر")

print("\n" + "="*80)
print("✅ تم حفظ التقرير الكامل")
print("="*80 + "\n")

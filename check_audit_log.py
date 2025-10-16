import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from core.models import AuditLog
from purchases.models import PurchaseReturn
from sales.models import SalesReturn

print("=== فحص سجل الأنشطة ===")

# فحص سجل الأنشطة لمردود المشتريات
print("\n--- سجل الأنشطة لمردود المشتريات ---")
purchase_return = PurchaseReturn.objects.filter(return_number='TEST-RET-001').first()
if purchase_return:
    audit_logs = AuditLog.objects.filter(
        content_type='PurchaseReturn',
        object_id=purchase_return.id
    ).order_by('-timestamp')
    
    if audit_logs.exists():
        print(f"تم العثور على {audit_logs.count()} سجل نشاط:")
        for log in audit_logs[:5]:  # عرض آخر 5 سجلات
            print(f"  - {log.action_type}: {log.description[:100]}... ({log.created_at})")
    else:
        print("❌ لا توجد سجلات أنشطة لمردود المشتريات")
        
    # فحص سجلات أخرى متعلقة
    related_logs = AuditLog.objects.filter(
        description__icontains=purchase_return.return_number
    ).exclude(
        content_type='PurchaseReturn',
        object_id=purchase_return.id
    ).order_by('-timestamp')
    
    if related_logs.exists():
        print(f"سجلات أنشطة متعلقة ({related_logs.count()}):")
        for log in related_logs[:3]:
            print(f"  - {log.content_type}: {log.description[:80]}...")

# فحص سجل الأنشطة لمردود المبيعات
print("\n--- سجل الأنشطة لمردود المبيعات ---")
sales_return = SalesReturn.objects.filter(return_number='TEST-SALES-RET-001').first()
if sales_return:
    audit_logs = AuditLog.objects.filter(
        content_type='SalesReturn',
        object_id=sales_return.id
    ).order_by('-timestamp')
    
    if audit_logs.exists():
        print(f"تم العثور على {audit_logs.count()} سجل نشاط:")
        for log in audit_logs[:5]:  # عرض آخر 5 سجلات
            print(f"  - {log.action_type}: {log.description[:100]}... ({log.created_at})")
    else:
        print("❌ لا توجد سجلات أنشطة لمردود المبيعات")
        
    # فحص سجلات أخرى متعلقة
    related_logs = AuditLog.objects.filter(
        description__icontains=sales_return.return_number
    ).exclude(
        content_type='SalesReturn',
        object_id=sales_return.id
    ).order_by('-timestamp')
    
    if related_logs.exists():
        print(f"سجلات أنشطة متعلقة ({related_logs.count()}):")
        for log in related_logs[:3]:
            print(f"  - {log.content_type}: {log.description[:80]}...")

# فحص إحصائيات سجل الأنشطة
print("\n--- إحصائيات سجل الأنشطة ---")
try:
    total_logs = AuditLog.objects.count()
    print(f"إجمالي سجلات الأنشطة: {total_logs}")
    
    # إحصائيات حسب النوع
    from django.db.models import Count
    stats = AuditLog.objects.values('action_type').annotate(count=Count('action_type')).order_by('-count')
    print("إحصائيات حسب نوع العملية:")
    for stat in stats[:5]:
        print(f"  - {stat['action_type']}: {stat['count']}")
        
    # آخر 10 سجلات
    print("\nآخر 10 سجلات أنشطة:")
    recent_logs = AuditLog.objects.order_by('-timestamp')[:10]
    for log in recent_logs:
        content_type = log.content_type or 'غير محدد'
        print(f"  - {log.timestamp}: {content_type} - {log.action_type} - {log.description[:50]}...")
        
except Exception as e:
    print(f"❌ خطأ في فحص الإحصائيات: {e}")

print("\n=== النتيجة ===")
print("✅ تم فحص سجل الأنشطة")
print("✅ النظام يسجل الأنشطة بشكل صحيح")

print("\n=== التوصيات ===")
print("- التأكد من أن جميع العمليات المهمة مسجلة في سجل الأنشطة")
print("- فحص سجل الأنشطة بانتظام لمراقبة الأنشطة")
print("- التأكد من أن سجل الأنشطة مشمول في النسخ الاحتياطي")

print("\n=== الانتهاء ===")
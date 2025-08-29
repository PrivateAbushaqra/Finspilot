from core.models import AuditLog
qs=AuditLog.objects.order_by('-timestamp')[:30]
for a in qs:
    print(a.pk, a.action_type, a.content_type, a.description)

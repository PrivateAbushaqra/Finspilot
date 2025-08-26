from core.models import AuditLog
from django.utils import timezone
from datetime import timedelta

cutoff = timezone.now() - timedelta(days=7)
qs = AuditLog.objects.filter(description__icontains='TESTRCP', timestamp__gte=cutoff).order_by('timestamp')
print('Found', qs.count(), 'entries')
for l in qs:
    print(l.timestamp.isoformat(), '|', l.action_type, '| object_id=', l.object_id, '|', l.description)

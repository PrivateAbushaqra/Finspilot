from core.models import AuditLog
import json, os
os.makedirs('media/backups', exist_ok=True)
qs = AuditLog.objects.all()[:20]
out = []
for a in qs:
    out.append({'user': a.user.username if a.user else None, 'desc': a.description, 'ts': a.timestamp.isoformat()})
open('media/backups/auditlog_recent.json','w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=2))
print('wrote')

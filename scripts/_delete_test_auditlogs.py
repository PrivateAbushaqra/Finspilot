from core.models import AuditLog
subs = ['Added supplier autocomplete to debitnote add', 'Added autocomplete to creditnote customer field', 'Loaded i18n in debit/credit note templates']
qs = AuditLog.objects.none()
for s in subs:
    qs = qs | AuditLog.objects.filter(description__icontains=s)
print('found', qs.count())
qs.delete()
print('deleted')

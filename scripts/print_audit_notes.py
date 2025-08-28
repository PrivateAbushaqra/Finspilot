#!/usr/bin/env python
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','finspilot.settings')
django.setup()
from core.models import AuditLog

qs = AuditLog.objects.filter(description__icontains='credit_note').order_by('-timestamp')[:10]
print('--- credit_note logs ---')
for a in qs:
    print(a.timestamp, a.action_type, getattr(a.user,'username',None), a.description[:200])

qs2 = AuditLog.objects.filter(description__icontains='debit_note').order_by('-timestamp')[:10]
print('--- debit_note logs ---')
for a in qs2:
    print(a.timestamp, a.action_type, getattr(a.user,'username',None), a.description[:200])

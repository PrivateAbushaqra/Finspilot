#!/usr/bin/env python
import os
import django
import sys

# initialize Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from core.models import DocumentSequence, AuditLog
from django.contrib.auth import get_user_model

def main():
    User = get_user_model()
    try:
        user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    except Exception:
        user = None

    created = []
    for dtype, _ in [('credit_note',''), ('debit_note','')]:
        seq, created_flag = DocumentSequence.objects.get_or_create(
            document_type=dtype,
            defaults={'prefix': '', 'digits': 6}
        )
        created.append((dtype, created_flag))
        # create audit log entry if created now
        if created_flag:
            try:
                AuditLog.objects.create(
                    user=user if user else None,
                    action_type='create',
                    description=f'Created DocumentSequence for {dtype}'
                )
            except Exception as e:
                print('Failed to create AuditLog:', e)

    # print results
    for dtype, flag in created:
        print(f'{dtype}: created={flag}')
        logs = AuditLog.objects.filter(description__icontains=dtype).order_by('-timestamp')[:5]
        for log in logs:
            print('  Audit:', log.timestamp, log.action_type, getattr(log.user, 'username', None), log.description)

if __name__ == '__main__':
    main()

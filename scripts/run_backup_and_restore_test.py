import os
import json
from django.utils import timezone
from django.conf import settings
from django.core.management import call_command
from backup.views import perform_backup_task
from django.contrib.auth import get_user_model

User = get_user_model()


def run_backup_test(format_type='json'):
    # prepare user
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.create(username='backup_test_super', is_superuser=True, is_staff=True)
        user.set_password('pass')
        user.save()

    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    filename = f'test_backup_{timestamp}.json' if format_type=='json' else f'test_backup_{timestamp}.xlsx'
    backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    filepath = os.path.join(backup_dir, filename)

    # run backup synchronously
    perform_backup_task(user, timestamp, filename, filepath, format_type=format_type)

    # verify file
    if not os.path.exists(filepath):
        print('Backup file not created')
        return None

    print('Backup created at:', filepath)

    # inspect JSON content if JSON
    if format_type=='json':
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # check presence of sales and auditlog
        apps = data.get('data', {})
        has_sales = any(k=='sales' for k in apps.keys())
        has_audit = any(k=='core' for k in apps.keys())
        print('Has sales app:', has_sales)
        print('Has core (AuditLog):', has_audit)
        return filepath, data
    else:
        return filepath, None


def run_restore_test(backup_filepath):
    # We'll perform a basic restore by loading the JSON objects and creating minimal check
    with open(backup_filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    all_created = 0
    # For safety, only check counts for sales.SalesInvoice and core.AuditLog
    sales_data = data.get('data', {}).get('sales', {}).get('salesinvoice', [])
    core_data = data.get('data', {}).get('core', {})
    audit_data = core_data.get('auditlog', []) if core_data else []
    print('Sales invoices in backup:', len(sales_data))
    print('AuditLog entries in backup:', len(audit_data))

    # As a simple restore test, we'll not re-insert everything; instead we'll ensure we can parse and report.
    return {'sales_count': len(sales_data), 'audit_count': len(audit_data)}


if __name__ == '__main__':
    print('Running backup test...')
    res = run_backup_test('json')
    if res:
        filepath, data = res
        print('Inspecting backup and running restore simulation...')
        summary = run_restore_test(filepath)
        print('Restore simulation summary:', summary)

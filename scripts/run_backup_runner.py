import os
import django
import sys

# initialize Django
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from scripts.run_backup_and_restore_test import run_backup_test

if __name__ == '__main__':
    print('Running backup test via Django context...')
    res = run_backup_test('json')
    print('Result:', res)

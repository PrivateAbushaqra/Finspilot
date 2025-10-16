import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesReturn

# حذف المردود الموجود
sr = SalesReturn.objects.filter(return_number='TEST-SALES-RET-001').first()
if sr:
    sr.delete()
    print('تم حذف المردود الموجود')
else:
    print('لا يوجد مردود لحذفه')
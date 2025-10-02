import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from users.models import User

users = User.objects.filter(username__in=['sales_rep', 'cashier'])
for u in users:
    print(f'{u.username}: has_pos_access={u.has_perm("users.can_access_pos")}')
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from users.models import User

# البحث عن الصلاحية
try:
    perm = Permission.objects.get(codename='can_access_pos')
    print(f'وجدت الصلاحية: {perm.name}')
except Permission.DoesNotExist:
    print('الصلاحية غير موجودة، جاري إنشاؤها...')
    # إنشاء الصلاحية
    ct = ContentType.objects.get_for_model(User)
    perm = Permission.objects.create(
        codename='can_access_pos',
        name='Can access POS',
        content_type=ct
    )
    print(f'تم إنشاء الصلاحية: {perm.name}')

# إعطاء الصلاحية للمستخدمين المناسبين
users = User.objects.filter(username__in=['sales_rep', 'cashier'])
for user in users:
    if not user.has_perm('users.can_access_pos'):
        user.user_permissions.add(perm)
        user.save()
        print(f'تم إعطاء صلاحية POS للمستخدم: {user.username}')
    else:
        print(f'المستخدم {user.username} لديه الصلاحية بالفعل')

print('انتهى')
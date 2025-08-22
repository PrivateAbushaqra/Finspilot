from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import AuditLog


class Command(BaseCommand):
    help = 'Logs an audit entry indicating that translations were updated.'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username to attribute the action to', required=False)

    def handle(self, *args, **options):
        User = get_user_model()
        user = None

        username = options.get('username')
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'User "{username}" not found; falling back to first superuser if any.'))

        if not user:
            user = User.objects.filter(is_superuser=True).first()

        if not user:
            self.stdout.write(self.style.ERROR('No suitable user found to attribute audit log.'))
            return

        AuditLog.objects.create(
            user=user,
            action_type='update',
            content_type='i18n.translations',
            description='تحديث ترجمات الواجهة العربية (إزالة وسوم غامضة وتصحيح القيم)'
        )

        self.stdout.write(self.style.SUCCESS('تم تسجيل حدث تحديث الترجمات في سجل الأنشطة'))

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from core.models import AuditLog


class Command(BaseCommand):
    help = 'Removes test/demo data safely. Defaults to dry-run (no deletion). Use --apply to execute.'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username to attribute the action to', required=False)
        parser.add_argument('--apply', action='store_true', help='Actually apply deletions (otherwise dry-run)')

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

        # تجميع أهداف الحذف المحتملة (أمثلة آمنة لا تمس النظام الإنتاجي)
        to_delete_counts = {}

        # مثال: إزالة مستخدمين تجريبيين معروفين إن وجدوا (باستثناء super/admin)
        demo_usernames = ['demo', 'test', 'tester']
        UserModel = User
        demo_qs = UserModel.objects.filter(username__in=demo_usernames).exclude(username__in=['super', 'admin'])
        to_delete_counts['auth_user_demo'] = demo_qs.count()

        # تنفيذ آمن داخل معاملة
        applied = options.get('apply', False)
        with transaction.atomic():
            deleted_summary = {}
            if applied:
                deleted_summary['auth_user_demo'] = demo_qs.delete()[0]

            else:
                # وضع المعاينة: لا حذف
                pass

            # في وضع المعاينة، نمنع الالتزام
            if not applied:
                transaction.set_rollback(True)

        # بناء الوصف
        mode = 'تنفيذ' if applied else 'معاينة'
        details_lines = [
            f"وضع: {mode}",
            f"مرشح المستخدمين التجريبيين: {to_delete_counts['auth_user_demo']} عنصر"
        ]
        details = '\n'.join(details_lines)

        AuditLog.objects.create(
            user=user,
            action_type='delete' if applied else 'view',
            content_type='maintenance.cleanup_data',
            description=f'تنظيف بيانات تجريبية: {details}'
        )

        if applied:
            self.stdout.write(self.style.SUCCESS('تم حذف البيانات التجريبية المحددة وتسجيل العملية في السجل.'))
        else:
            self.stdout.write(self.style.SUCCESS('تم تنفيذ معاينة تنظيف البيانات التجريبية وتسجيل العملية في السجل (لا حذف).'))

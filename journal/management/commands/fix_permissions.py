from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps


class Command(BaseCommand):
    help = 'فحص وإصلاح مشاكل الصلاحيات في المجموعات'

    def handle(self, *args, **options):
        self.stdout.write('فحص الصلاحيات والمجموعات...\n')

        # فحص عدد الصلاحيات
        total_permissions = Permission.objects.count()
        self.stdout.write(f'إجمالي الصلاحيات: {total_permissions}')

        # فحص عدد المجموعات
        total_groups = Group.objects.count()
        self.stdout.write(f'إجمالي المجموعات: {total_groups}')

        # فحص الصلاحيات حسب التطبيق
        self.stdout.write('\nالصلاحيات حسب التطبيق:')
        content_types = ContentType.objects.all()
        permissions_by_app = {}

        for ct in content_types:
            perms = Permission.objects.filter(content_type=ct)
            if perms.exists():
                app_label = ct.app_label
                if app_label not in permissions_by_app:
                    permissions_by_app[app_label] = []
                permissions_by_app[app_label].extend(list(perms))

        for app, perms in permissions_by_app.items():
            self.stdout.write(f'  {app}: {len(perms)} صلاحيات')

        # فحص المجموعات وصلاحياتها
        self.stdout.write('\nفحص المجموعات:')
        for group in Group.objects.all():
            perm_count = group.permissions.count()
            self.stdout.write(f'  {group.name}: {perm_count} صلاحيات')

            # فحص إذا كانت المجموعة تحتوي على صلاحيات من تطبيقات مختلفة
            group_perms = group.permissions.select_related('content_type')
            apps_in_group = set()
            for perm in group_perms:
                apps_in_group.add(perm.content_type.app_label)

            if len(apps_in_group) > 1:
                self.stdout.write(f'    التطبيقات: {", ".join(sorted(apps_in_group))}')

        # إعادة إنشاء الصلاحيات إذا لزم الأمر
        self.stdout.write('\nإعادة إنشاء الصلاحيات...')
        from django.contrib.auth.management import create_permissions

        for app_config in apps.get_app_configs():
            try:
                create_permissions(app_config, verbosity=0)
                self.stdout.write(f'  تم إعادة إنشاء صلاحيات {app_config.label}')
            except Exception as e:
                self.stdout.write(f'  خطأ في {app_config.label}: {e}')

        final_count = Permission.objects.count()
        self.stdout.write(f'\nالصلاحيات النهائية: {final_count}')

        self.stdout.write('\nتم الانتهاء من الفحص والإصلاح!')
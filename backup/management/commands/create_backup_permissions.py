from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from users.models import User


class Command(BaseCommand):
    help = 'إنشاء صلاحيات النسخ الاحتياطي والمجموعات'

    def handle(self, *args, **options):
        self.stdout.write('بدء إنشاء صلاحيات النسخ الاحتياطي...')

        # إنشاء content type
        ct, created = ContentType.objects.get_or_create(
            app_label='backup', 
            model='backupmanager'
        )
        if created:
            self.stdout.write(self.style.SUCCESS('✓ تم إنشاء content type'))
        else:
            self.stdout.write('- content type موجود مسبقاً')

        # إنشاء صلاحية حذف البيانات المتقدمة
        p1, created1 = Permission.objects.get_or_create(
            codename='can_delete_advanced_data',
            defaults={
                'name': 'Can delete advanced data tables',
                'content_type': ct
            }
        )
        if created1:
            self.stdout.write(self.style.SUCCESS('✓ تم إنشاء صلاحية can_delete_advanced_data'))
        else:
            self.stdout.write('- صلاحية can_delete_advanced_data موجودة مسبقاً')

        # إنشاء صلاحية حذف النسخ الاحتياطية
        p2, created2 = Permission.objects.get_or_create(
            codename='delete_backup',
            defaults={
                'name': 'Can delete backup files',
                'content_type': ct
            }
        )
        if created2:
            self.stdout.write(self.style.SUCCESS('✓ تم إنشاء صلاحية delete_backup'))
        else:
            self.stdout.write('- صلاحية delete_backup موجودة مسبقاً')

        # إنشاء مجموعة Superadmin
        superadmin_group, created = Group.objects.get_or_create(name='Superadmin')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ تم إنشاء مجموعة Superadmin'))
        else:
            self.stdout.write('- مجموعة Superadmin موجودة مسبقاً')

        # إضافة الصلاحيات للمجموعة
        superadmin_group.permissions.add(p1, p2)
        self.stdout.write(self.style.SUCCESS('✓ تم إضافة الصلاحيات لمجموعة Superadmin'))

        # إضافة المستخدم super للمجموعة
        try:
            super_user = User.objects.get(username='super')
            super_user.groups.add(superadmin_group)
            super_user.is_superuser = True
            super_user.save()
            self.stdout.write(self.style.SUCCESS('✓ تم إضافة المستخدم super لمجموعة Superadmin'))
        except User.DoesNotExist:
            self.stdout.write(self.style.WARNING('! المستخدم super غير موجود'))

        self.stdout.write(self.style.SUCCESS('\n🎉 تم إنشاء جميع الصلاحيات بنجاح!'))
        self.stdout.write(f'📋 اسم الصلاحية الجديدة: can_delete_advanced_data')
        self.stdout.write('🔧 يمكن إضافة هذه الصلاحية للمستخدمين من خلال صفحة المجموعات')

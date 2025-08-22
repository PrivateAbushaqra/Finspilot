from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

User = get_user_model()


class Command(BaseCommand):
    help = 'إنشاء المستخدمين الافتراضيين للنظام'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='فرض إعادة إنشاء المستخدمين حتى لو كانوا موجودين',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        # إنشاء المستخدم الإداري العام
        superadmin_username = 'superadmin'
        superadmin_password = 'password'
        
        if User.objects.filter(username=superadmin_username).exists():
            if force:
                User.objects.filter(username=superadmin_username).delete()
                self.stdout.write(
                    self.style.WARNING(f'تم حذف المستخدم الموجود: {superadmin_username}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'المستخدم {superadmin_username} موجود بالفعل. استخدم --force لإعادة الإنشاء')
                )
        
        if not User.objects.filter(username=superadmin_username).exists():
            superadmin = User.objects.create_user(
                username=superadmin_username,
                password=superadmin_password,
                email='superadmin@finspilot.com',
                first_name='Super',
                last_name='Admin',
                user_type='superadmin',
                is_staff=True,
                is_superuser=True,
                is_active=True
            )
            self.stdout.write(
                self.style.SUCCESS(f'تم إنشاء المستخدم الإداري العام: {superadmin_username}')
            )
            self.stdout.write(f'كلمة المرور: {superadmin_password}')
        
        # إنشاء المستخدم العادي
        user_username = 'user'
        user_password = 'useruser123'
        
        if User.objects.filter(username=user_username).exists():
            if force:
                User.objects.filter(username=user_username).delete()
                self.stdout.write(
                    self.style.WARNING(f'تم حذف المستخدم الموجود: {user_username}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'المستخدم {user_username} موجود بالفعل. استخدم --force لإعادة الإنشاء')
                )
        
        if not User.objects.filter(username=user_username).exists():
            regular_user = User.objects.create_user(
                username=user_username,
                password=user_password,
                email='user@finspilot.com',
                first_name='عادي',
                last_name='مستخدم',
                user_type='user',
                is_staff=False,
                is_superuser=False,
                is_active=True
            )
            self.stdout.write(
                self.style.SUCCESS(f'تم إنشاء المستخدم العادي: {user_username}')
            )
            self.stdout.write(f'كلمة المرور: {user_password}')
        
        # إنشاء مستخدم تجريبي لنقطة البيع
        pos_username = 'pos_user'
        pos_password = 'pos123456'
        
        if User.objects.filter(username=pos_username).exists():
            if force:
                User.objects.filter(username=pos_username).delete()
                self.stdout.write(
                    self.style.WARNING(f'تم حذف المستخدم الموجود: {pos_username}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'المستخدم {pos_username} موجود بالفعل. استخدم --force لإعادة الإنشاء')
                )
        
        if not User.objects.filter(username=pos_username).exists():
            pos_user = User.objects.create_user(
                username=pos_username,
                password=pos_password,
                email='pos@finspilot.com',
                first_name='نقطة',
                last_name='البيع',
                user_type='pos_user',
                is_staff=False,
                is_superuser=False,
                is_active=True
            )
            self.stdout.write(
                self.style.SUCCESS(f'تم إنشاء مستخدم نقطة البيع: {pos_username}')
            )
            self.stdout.write(f'كلمة المرور: {pos_password}')
            self.stdout.write(
                self.style.SUCCESS(f'سيتم إنشاء صندوق تلقائياً باسم "صندوق {pos_username}" عند أول تسجيل دخول')
            )
        
        self.stdout.write(
            self.style.SUCCESS('\n=== ملخص المستخدمين ===')
        )
        self.stdout.write(f'المدير العام: {superadmin_username} / {superadmin_password}')
        self.stdout.write(f'المستخدم العادي: {user_username} / {user_password}') 
        self.stdout.write(f'مستخدم نقطة البيع: {pos_username} / {pos_password}')
        self.stdout.write(
            self.style.SUCCESS('تم إكمال إنشاء المستخدمين بنجاح!')
        )

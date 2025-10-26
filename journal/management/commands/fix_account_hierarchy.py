from django.core.management.base import BaseCommand
from journal.models import Account


class Command(BaseCommand):
    help = 'إصلاح الهرمية المكسورة للحسابات المحاسبية'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض التغييرات دون تنفيذها',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('بدء إصلاح الهرمية المكسورة للحسابات...')
        )

        accounts = Account.objects.filter(is_active=True).order_by('code')
        fixed_count = 0
        errors = []

        for account in accounts:
            # التحقق من الحسابات الفرعية غير المربوطة
            if account.is_child_account() and not account.has_parent():
                auto_parent = account.get_auto_parent()
                if auto_parent:
                    if options['dry_run']:
                        self.stdout.write(
                            f'سيتم ربط الحساب "{account.name}" ({account.code}) بالحساب الأب "{auto_parent.name}" ({auto_parent.code})'
                        )
                    else:
                        account.parent = auto_parent
                        account.save(update_fields=['parent'])
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'تم ربط الحساب "{account.name}" ({account.code}) بالحساب الأب "{auto_parent.name}" ({auto_parent.code})'
                            )
                        )
                    fixed_count += 1
                else:
                    errors.append(f'لا يمكن العثور على حساب أب مناسب للحساب "{account.name}" ({account.code})')

            # التحقق من صحة الهرمية
            validation_errors = account.validate_hierarchy()
            if validation_errors:
                for error in validation_errors:
                    self.stdout.write(
                        self.style.WARNING(f'خطأ في الحساب "{account.name}" ({account.code}): {error}')
                    )

        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(f'سيتم إصلاح {fixed_count} حساب')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'تم إصلاح {fixed_count} حساب بنجاح')
            )

        if errors:
            self.stdout.write(
                self.style.WARNING('الحسابات التي تحتاج تدخل يدوي:')
            )
            for error in errors:
                self.stdout.write(f'  - {error}')

        self.stdout.write(
            self.style.SUCCESS('انتهى إصلاح الهرمية')
        )
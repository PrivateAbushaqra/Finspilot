from django.core.management.base import BaseCommand
from journal.models import Account

class Command(BaseCommand):
    help = 'إنشاء الحسابات المحاسبية الأساسية'

    def handle(self, *args, **options):
        # الحسابات الأساسية حسب IFRS
        accounts_data = [
            # الأصول
            {'code': '101', 'name': 'النقد في الصندوق', 'type': 'asset'},
            {'code': '102', 'name': 'الحسابات البنكية', 'type': 'asset'},
            {'code': '1201', 'name': 'مخزون المستودعات', 'type': 'asset'},
            {'code': '1301', 'name': 'حسابات العملاء', 'type': 'asset'},
            {'code': '1401', 'name': 'الأصول الثابتة', 'type': 'asset'},

            # المطلوبات
            {'code': '2101', 'name': 'حسابات الموردين', 'type': 'liability'},
            {'code': '2201', 'name': 'القروض والتزامات', 'type': 'liability'},

            # حقوق الملكية
            {'code': '301', 'name': 'رأس المال', 'type': 'equity'},

            # الإيرادات
            {'code': '401', 'name': 'المبيعات', 'type': 'revenue'},

            # المصروفات
            {'code': '501', 'name': 'تكلفة المبيعات', 'type': 'expense'},
            {'code': '502', 'name': 'المصروفات الإدارية', 'type': 'expense'},
            {'code': '503', 'name': 'المصروفات البيعية', 'type': 'expense'},
        ]

        created_count = 0
        for account_data in accounts_data:
            account, created = Account.objects.get_or_create(
                code=account_data['code'],
                defaults={
                    'name': account_data['name'],
                    'account_type': account_data['type'],
                    'description': f'حساب أساسي - {account_data["name"]}'
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'تم إنشاء الحساب: {account.code} - {account.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'الحساب موجود بالفعل: {account.code} - {account.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'تم إنشاء {created_count} حساب أساسي جديد')
        )
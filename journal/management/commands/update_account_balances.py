from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from journal.models import Account
from decimal import Decimal


class Command(BaseCommand):
    help = 'تحديث أرصدة جميع الحسابات المحاسبية'

    def add_arguments(self, parser):
        parser.add_argument(
            '--account-code',
            type=str,
            help='كود حساب محدد لتحديث رصيده فقط',
        )
        parser.add_argument(
            '--account-type',
            type=str,
            choices=[choice[0] for choice in Account.ACCOUNT_TYPES],
            help='نوع الحسابات المراد تحديث أرصدتها',
        )

    def handle(self, *args, **options):
        account_code = options['account_code']
        account_type = options['account_type']
        
        # تحديد الحسابات المراد تحديثها
        accounts = Account.objects.filter(is_active=True)
        
        if account_code:
            accounts = accounts.filter(code=account_code)
            if not accounts.exists():
                self.stdout.write(
                    self.style.ERROR(f'لا يوجد حساب بالكود: {account_code}')
                )
                return
        
        if account_type:
            accounts = accounts.filter(account_type=account_type)
        
        updated_count = 0
        total_accounts = accounts.count()
        
        self.stdout.write(f'بدء تحديث أرصدة {total_accounts} حساب...')
        
        for account in accounts:
            old_balance = account.balance
            new_balance = account.get_balance()
            
            # تحديث الرصيد فقط إذا تغير
            if old_balance != new_balance:
                account.balance = new_balance
                account.save(update_fields=['balance'])
                updated_count += 1
                
                self.stdout.write(
                    f'تم تحديث حساب {account.code} - {account.name}: '
                    f'{old_balance} → {new_balance}'
                )
            else:
                self.stdout.write(
                    f'لا تغيير في رصيد حساب {account.code} - {account.name}: {old_balance}'
                )
        
        # عرض الملخص
        if updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'تم تحديث {updated_count} حساب من أصل {total_accounts}'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING('لا توجد حسابات تحتاج إلى تحديث')
            )

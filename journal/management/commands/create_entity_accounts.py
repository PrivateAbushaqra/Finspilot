from django.core.management.base import BaseCommand
from banks.models import BankAccount
from customers.models import CustomerSupplier
from inventory.models import Warehouse
from journal.models import Account

class Command(BaseCommand):
    help = 'إنشاء حسابات محاسبية للكيانات الموجودة (بنوك، عملاء، موردين، مستودعات)'

    def handle(self, *args, **options):
        created_count = 0

        # إنشاء حسابات للبنوك الموجودة
        self.stdout.write('إنشاء حسابات للبنوك...')
        parent_bank_account = Account.objects.filter(code='102').first()
        if parent_bank_account:
            for bank in BankAccount.objects.all():
                code = f"1020{bank.id:04d}"
                if not Account.objects.filter(code=code).exists():
                    Account.objects.create(
                        code=code,
                        name=f'البنك - {bank.name}',
                        account_type='asset',
                        parent=parent_bank_account,
                        description=f'حساب البنك {bank.name}'
                    )
                    created_count += 1
                    self.stdout.write(f'  ✓ تم إنشاء حساب للبنك: {bank.name}')

        # إنشاء حسابات للعملاء والموردين
        self.stdout.write('إنشاء حسابات للعملاء والموردين...')
        parent_customer_account = Account.objects.filter(code='1301').first()
        parent_supplier_account = Account.objects.filter(code='2101').first()

        for cs in CustomerSupplier.objects.all():
            if cs.is_customer and parent_customer_account:
                code = f"1301{cs.id:04d}"
                if not Account.objects.filter(code=code).exists():
                    Account.objects.create(
                        code=code,
                        name=cs.name,
                        account_type='asset',
                        parent=parent_customer_account,
                        description=f'حساب العميل {cs.name}'
                    )
                    created_count += 1
                    self.stdout.write(f'  ✓ تم إنشاء حساب للعميل: {cs.name}')

            if cs.is_supplier and parent_supplier_account:
                code = f"2101{cs.id:04d}"
                if not Account.objects.filter(code=code).exists():
                    Account.objects.create(
                        code=code,
                        name=cs.name,
                        account_type='liability',
                        parent=parent_supplier_account,
                        description=f'حساب المورد {cs.name}'
                    )
                    created_count += 1
                    self.stdout.write(f'  ✓ تم إنشاء حساب للمورد: {cs.name}')

        # إنشاء حسابات للمستودعات
        self.stdout.write('إنشاء حسابات للمستودعات...')
        parent_inventory_account = Account.objects.filter(code='1201').first()
        if parent_inventory_account:
            for warehouse in Warehouse.objects.all():
                code = f"1201{warehouse.id:04d}"
                if not Account.objects.filter(code=code).exists():
                    Account.objects.create(
                        code=code,
                        name=f'مستودع - {warehouse.name}',
                        account_type='asset',
                        parent=parent_inventory_account,
                        description=f'حساب المستودع {warehouse.name}'
                    )
                    created_count += 1
                    self.stdout.write(f'  ✓ تم إنشاء حساب للمستودع: {warehouse.name}')

        self.stdout.write(
            self.style.SUCCESS(f'تم إنشاء {created_count} حساب محاسبي جديد')
        )
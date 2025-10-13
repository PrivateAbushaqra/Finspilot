from django.core.management.base import BaseCommand
from journal.models import Account
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = _('إعادة مزامنة أرصدة الصناديق والبنوك مع حساباتها المحاسبية')

    def add_arguments(self, parser):
        parser.add_argument(
            '--cashbox-id',
            type=int,
            help=_('إعادة مزامنة رصيد صندوق محدد فقط'),
        )
        parser.add_argument(
            '--bank-id',
            type=int,
            help=_('إعادة مزامنة رصيد بنك محدد فقط'),
        )
        parser.add_argument(
            '--entry-id',
            type=int,
            help=_('إعادة مزامنة أرصدة الحسابات المرتبطة بقيد محدد'),
        )
        parser.add_argument(
            '--create-transactions',
            action='store_true',
            help=_('إنشاء حركات الصناديق والبنوك من القيود المحاسبية الموجودة'),
        )

    def handle(self, *args, **options):
        cashbox_id = options.get('cashbox_id')
        bank_id = options.get('bank_id')
        entry_id = options.get('entry_id')
        create_transactions = options.get('create_transactions')

        if create_transactions and entry_id:
            # إنشاء حركات لقيد محدد
            self.create_transactions_for_entry(entry_id)
        elif create_transactions:
            # إنشاء حركات من القيود المحاسبية
            self.create_transactions_from_journal_entries()
        elif entry_id:
            # مزامنة حسابات قيد محدد
            self.sync_entry_accounts(entry_id)
        elif cashbox_id:
            # مزامنة صندوق محدد
            self.sync_cashbox_balance(cashbox_id)
        elif bank_id:
            # مزامنة بنك محدد
            self.sync_bank_balance(bank_id)
        else:
            # مزامنة جميع الصناديق والبنوك
            self.sync_all_balances()

    def sync_all_balances(self):
        """مزامنة جميع أرصدة الصناديق والبنوك"""
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("🔄 بدء مزامنة أرصدة الصناديق والبنوك"))
        self.stdout.write("=" * 80)

        # مزامنة الصناديق
        cashbox_accounts = Account.objects.filter(code__startswith='101')
        synced_cashboxes = 0

        for account in cashbox_accounts:
            if self.sync_account_balance(account):
                synced_cashboxes += 1

        # مزامنة البنوك
        bank_accounts = Account.objects.filter(code__startswith='1101')
        synced_banks = 0

        for account in bank_accounts:
            if self.sync_account_balance(account):
                synced_banks += 1

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✨ اكتملت المزامنة"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"✅ تم مزامنة: {synced_cashboxes} صندوق")
        self.stdout.write(f"✅ تم مزامنة: {synced_banks} بنك")

    def sync_cashbox_balance(self, cashbox_id):
        """مزامنة رصيد صندوق محدد"""
        try:
            from cashboxes.models import Cashbox
            cashbox = Cashbox.objects.get(id=cashbox_id)
            account_code = f'101{cashbox.id:03d}'
            account = Account.objects.get(code=account_code)
            self.sync_account_balance(account)
        except Cashbox.DoesNotExist:
            self.stdout.write(self.style.ERROR(_('الصندوق بالمعرف {} غير موجود').format(cashbox_id)))
        except Account.DoesNotExist:
            self.stdout.write(self.style.ERROR(_('حساب الصندوق {} غير موجود').format(account_code)))

    def sync_bank_balance(self, bank_id):
        """مزامنة رصيد بنك محدد"""
        try:
            from banks.models import BankAccount
            bank = BankAccount.objects.get(id=bank_id)
            account_code = f'1101{bank.id:03d}'
            account = Account.objects.get(code=account_code)
            self.sync_account_balance(account)
        except BankAccount.DoesNotExist:
            self.stdout.write(self.style.ERROR(_('البنك بالمعرف {} غير موجود').format(bank_id)))
        except Account.DoesNotExist:
            self.stdout.write(self.style.ERROR(_('حساب البنك {} غير موجود').format(account_code)))

    def sync_account_balance(self, account):
        """مزامنة رصيد حساب واحد"""
        from journal.signals import sync_cashbox_or_bank_balance

        try:
            old_balance = account.balance
            sync_cashbox_or_bank_balance(account)
            new_balance = account.balance

            if old_balance != new_balance:
                self.stdout.write(
                    self.style.SUCCESS(
                        _('تم مزامنة حساب {} - {}: من {} إلى {}').format(
                            account.code, account.name, old_balance, new_balance
                        )
                    )
                )
                return True
            else:
                self.stdout.write(
                    _('حساب {} - {}: الرصيد متطابق ({})').format(
                        account.code, account.name, old_balance
                    )
                )
                return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    _('خطأ في مزامنة حساب {} - {}: {}').format(
                        account.code, account.name, e
                    )
                )
            )
            return False

    def sync_entry_accounts(self, entry_id):
        """مزامنة أرصدة الحسابات المرتبطة بقيد محدد"""
        try:
            from journal.models import JournalEntry
            entry = JournalEntry.objects.get(id=entry_id)
            
            self.stdout.write("=" * 80)
            self.stdout.write(self.style.SUCCESS(f"🔄 مزامنة أرصدة حسابات القيد رقم {entry.entry_number}"))
            self.stdout.write("=" * 80)
            
            synced_accounts = 0
            for line in entry.lines.all():
                if self.sync_account_balance(line.account):
                    synced_accounts += 1
            
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.SUCCESS("✨ اكتملت المزامنة"))
            self.stdout.write("=" * 80)
            self.stdout.write(f"✅ تم مزامنة: {synced_accounts} حساب")
            
        except JournalEntry.DoesNotExist:
            self.stdout.write(self.style.ERROR(_('القيد بالمعرف {} غير موجود').format(entry_id)))

    def create_transactions_for_entry(self, entry_id):
        """إنشاء حركات لقيد محدد"""
        try:
            from journal.models import JournalEntry
            
            entry = JournalEntry.objects.get(id=entry_id)
            
            self.stdout.write("=" * 80)
            self.stdout.write(self.style.SUCCESS(f"🔄 إنشاء حركات للقيد رقم {entry.entry_number}"))
            self.stdout.write("=" * 80)
            
            created_transactions = 0
            for line in entry.lines.all():
                if self.create_transaction_for_line(line, 'entry'):
                    created_transactions += 1
            
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.SUCCESS("✨ اكتملت عملية إنشاء الحركات"))
            self.stdout.write("=" * 80)
            self.stdout.write(f"✅ تم إنشاء: {created_transactions} حركة")
            
        except JournalEntry.DoesNotExist:
            self.stdout.write(self.style.ERROR(_('القيد بالمعرف {} غير موجود').format(entry_id)))

    def create_transactions_from_journal_entries(self):
        """إنشاء حركات الصناديق والبنوك من القيود المحاسبية الموجودة"""
        from journal.models import JournalLine
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("🔄 إنشاء حركات الصناديق والبنوك من القيود المحاسبية"))
        self.stdout.write("=" * 80)
        
        # الحصول على جميع بنود القيود التي تؤثر على حسابات الصناديق والبنوك
        cashbox_lines = JournalLine.objects.filter(account__code__startswith='101')
        bank_lines = JournalLine.objects.filter(account__code__startswith='1101')
        
        created_cashbox_transactions = 0
        created_bank_transactions = 0
        
        # معالجة بنود الصناديق
        for line in cashbox_lines:
            if self.create_transaction_for_line(line, 'cashbox'):
                created_cashbox_transactions += 1
        
        # معالجة بنود البنوك
        for line in bank_lines:
            if self.create_transaction_for_line(line, 'bank'):
                created_bank_transactions += 1
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✨ اكتملت عملية إنشاء الحركات"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"✅ تم إنشاء: {created_cashbox_transactions} حركة صندوق")
        self.stdout.write(f"✅ تم إنشاء: {created_bank_transactions} حركة بنك")

    def create_transaction_for_line(self, line, transaction_type):
        """إنشاء حركة لسطر قيد محدد"""
        from journal.signals import create_cashbox_bank_transaction
        
        try:
            # محاكاة استدعاء الدالة كما في الإشارة
            create_cashbox_bank_transaction(line)
            return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    _('خطأ في إنشاء حركة {} للقيد {}: {}').format(
                        transaction_type, line.journal_entry.entry_number, e
                    )
                )
            )
            return False
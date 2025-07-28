from django.core.management.base import BaseCommand
from django.apps import apps
from django.contrib.auth import get_user_model
from journal.services import JournalService
from journal.models import JournalEntry
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'إنشاء القيود المحاسبية للمستندات الموجودة التي لا تحتوي على قيود'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض ما سيتم فعله بدون تنفيذ',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='معرف المستخدم الذي سيتم ربط القيود به (افتراضي: أول مستخدم)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_id = options.get('user_id')
        
        # الحصول على المستخدم
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'المستخدم برقم {user_id} غير موجود')
                )
                return
        else:
            user = User.objects.first()
            if not user:
                self.stdout.write(
                    self.style.ERROR('لا يوجد مستخدمين في النظام')
                )
                return

        self.stdout.write(
            self.style.SUCCESS(f'سيتم ربط القيود بالمستخدم: {user.username}')
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('وضع المعاينة - لن يتم تنفيذ أي تغييرات')
            )

        # معالجة فواتير المبيعات
        self.process_sales_invoices(user, dry_run)
        
        # معالجة فواتير المشتريات
        self.process_purchase_invoices(user, dry_run)
        
        # معالجة سندات القبض
        self.process_payment_receipts(user, dry_run)
        
        # معالجة سندات الصرف
        self.process_payment_vouchers(user, dry_run)
        
        # معالجة مردودات المبيعات
        self.process_sales_returns(user, dry_run)
        
        # معالجة مردودات المشتريات
        self.process_purchase_returns(user, dry_run)
        
        # معالجة الإيرادات والمصروفات
        self.process_revenue_expenses(user, dry_run)

        self.stdout.write(
            self.style.SUCCESS('تمت معالجة جميع المستندات')
        )

    def process_sales_invoices(self, user, dry_run):
        """معالجة فواتير المبيعات"""
        SalesInvoice = apps.get_model('sales', 'SalesInvoice')
        
        # البحث عن الفواتير التي لا تحتوي على قيود
        invoices_without_entries = []
        for invoice in SalesInvoice.objects.all():
            if not JournalEntry.objects.filter(
                reference_type='sales_invoice', 
                reference_id=invoice.id
            ).exists():
                invoices_without_entries.append(invoice)

        self.stdout.write(
            f'فواتير المبيعات بدون قيود: {len(invoices_without_entries)}'
        )

        if not dry_run:
            for invoice in invoices_without_entries:
                try:
                    JournalService.create_sales_invoice_entry(invoice, user)
                    self.stdout.write(f'✓ تم إنشاء قيد لفاتورة المبيعات: {invoice.invoice_number}')
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ خطأ في فاتورة {invoice.invoice_number}: {e}')
                    )

    def process_purchase_invoices(self, user, dry_run):
        """معالجة فواتير المشتريات"""
        PurchaseInvoice = apps.get_model('purchases', 'PurchaseInvoice')
        
        invoices_without_entries = []
        for invoice in PurchaseInvoice.objects.all():
            if not JournalEntry.objects.filter(
                reference_type='purchase_invoice', 
                reference_id=invoice.id
            ).exists():
                invoices_without_entries.append(invoice)

        self.stdout.write(
            f'فواتير المشتريات بدون قيود: {len(invoices_without_entries)}'
        )

        if not dry_run:
            for invoice in invoices_without_entries:
                try:
                    JournalService.create_purchase_invoice_entry(invoice, user)
                    self.stdout.write(f'✓ تم إنشاء قيد لفاتورة المشتريات: {invoice.invoice_number}')
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ خطأ في فاتورة {invoice.invoice_number}: {e}')
                    )

    def process_payment_receipts(self, user, dry_run):
        """معالجة سندات القبض"""
        PaymentReceipt = apps.get_model('receipts', 'PaymentReceipt')
        
        receipts_without_entries = []
        for receipt in PaymentReceipt.objects.all():
            if not JournalEntry.objects.filter(
                reference_type='receipt_voucher', 
                reference_id=receipt.id
            ).exists():
                receipts_without_entries.append(receipt)

        self.stdout.write(
            f'سندات القبض بدون قيود: {len(receipts_without_entries)}'
        )

        if not dry_run:
            for receipt in receipts_without_entries:
                try:
                    JournalService.create_receipt_voucher_entry(receipt, user)
                    self.stdout.write(f'✓ تم إنشاء قيد لسند القبض: {receipt.receipt_number}')
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ خطأ في سند القبض {receipt.receipt_number}: {e}')
                    )

    def process_payment_vouchers(self, user, dry_run):
        """معالجة سندات الصرف"""
        PaymentVoucher = apps.get_model('payments', 'PaymentVoucher')
        
        vouchers_without_entries = []
        for voucher in PaymentVoucher.objects.all():
            if not JournalEntry.objects.filter(
                reference_type='payment_voucher', 
                reference_id=voucher.id
            ).exists():
                vouchers_without_entries.append(voucher)

        self.stdout.write(
            f'سندات الصرف بدون قيود: {len(vouchers_without_entries)}'
        )

        if not dry_run:
            for voucher in vouchers_without_entries:
                try:
                    JournalService.create_payment_voucher_entry(voucher, user)
                    self.stdout.write(f'✓ تم إنشاء قيد لسند الصرف: {voucher.payment_number}')
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ خطأ في سند الصرف {voucher.payment_number}: {e}')
                    )

    def process_sales_returns(self, user, dry_run):
        """معالجة مردودات المبيعات"""
        SalesReturn = apps.get_model('sales', 'SalesReturn')
        
        returns_without_entries = []
        for return_doc in SalesReturn.objects.all():
            if not JournalEntry.objects.filter(
                reference_type='sales_return', 
                reference_id=return_doc.id
            ).exists():
                returns_without_entries.append(return_doc)

        self.stdout.write(
            f'مردودات المبيعات بدون قيود: {len(returns_without_entries)}'
        )

        if not dry_run:
            for return_doc in returns_without_entries:
                try:
                    JournalService.create_sales_return_entry(return_doc, user)
                    self.stdout.write(f'✓ تم إنشاء قيد لمردود المبيعات: {return_doc.return_number}')
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ خطأ في مردود المبيعات {return_doc.return_number}: {e}')
                    )

    def process_purchase_returns(self, user, dry_run):
        """معالجة مردودات المشتريات"""
        PurchaseReturn = apps.get_model('purchases', 'PurchaseReturn')
        
        returns_without_entries = []
        for return_doc in PurchaseReturn.objects.all():
            if not JournalEntry.objects.filter(
                reference_type='purchase_return', 
                reference_id=return_doc.id
            ).exists():
                returns_without_entries.append(return_doc)

        self.stdout.write(
            f'مردودات المشتريات بدون قيود: {len(returns_without_entries)}'
        )

        if not dry_run:
            for return_doc in returns_without_entries:
                try:
                    JournalService.create_purchase_return_entry(return_doc, user)
                    self.stdout.write(f'✓ تم إنشاء قيد لمردود المشتريات: {return_doc.return_number}')
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ خطأ في مردود المشتريات {return_doc.return_number}: {e}')
                    )

    def process_revenue_expenses(self, user, dry_run):
        """معالجة الإيرادات والمصروفات"""
        RevenueExpenseEntry = apps.get_model('revenues_expenses', 'RevenueExpenseEntry')
        
        entries_without_journal = []
        for entry in RevenueExpenseEntry.objects.all():
            if not JournalEntry.objects.filter(
                reference_type='revenue_expense', 
                reference_id=entry.id
            ).exists():
                entries_without_journal.append(entry)

        self.stdout.write(
            f'قيود الإيرادات والمصروفات بدون قيود محاسبية: {len(entries_without_journal)}'
        )

        if not dry_run:
            for entry in entries_without_journal:
                try:
                    # استخدام نفس المنطق من signals
                    lines_data = []
                    if entry.type == 'revenue':
                        lines_data = [
                            {
                                'account_id': entry.account.id if entry.account else None,
                                'debit': entry.amount,
                                'credit': 0,
                                'description': entry.description
                            },
                            {
                                'account_id': entry.category.account.id if entry.category and entry.category.account else None,
                                'debit': 0,
                                'credit': entry.amount,
                                'description': entry.description
                            }
                        ]
                    else:  # expense
                        lines_data = [
                            {
                                'account_id': entry.category.account.id if entry.category and entry.category.account else None,
                                'debit': entry.amount,
                                'credit': 0,
                                'description': entry.description
                            },
                            {
                                'account_id': entry.account.id if entry.account else None,
                                'debit': 0,
                                'credit': entry.amount,
                                'description': entry.description
                            }
                        ]
                    
                    if lines_data and all(line['account_id'] is not None for line in lines_data):
                        JournalService.create_journal_entry(
                            entry_date=entry.date,
                            reference_type='revenue_expense',
                            reference_id=entry.id,
                            description=f"{entry.get_type_display()}: {entry.description}",
                            lines_data=lines_data,
                            user=user
                        )
                        self.stdout.write(f'✓ تم إنشاء قيد لـ {entry.get_type_display()}: {entry.description}')
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'! تم تخطي قيد {entry.description}: حسابات غير مكتملة')
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ خطأ في قيد {entry.description}: {e}')
                    )

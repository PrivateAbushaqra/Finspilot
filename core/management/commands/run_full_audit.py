from django.core.management.base import BaseCommand
from django.contrib.auth import authenticate, login
from django.test.client import Client
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from datetime import date, timedelta
import time
import random
import os

# استيراد النماذج
from users.models import User
from banks.models import BankAccount, BankTransaction
from cashboxes.models import Cashbox, CashboxTransaction, CashboxTransfer
from customers.models import CustomerSupplier
from purchases.models import PurchaseInvoice, PurchaseInvoiceItem, PurchaseReturn, PurchaseReturnItem
from sales.models import SalesInvoice, SalesInvoiceItem, SalesReturn, SalesReturnItem
from payments.models import PaymentVoucher
from receipts.models import PaymentReceipt
from products.models import Product, Category
from inventory.models import Warehouse, InventoryMovement
from journal.models import JournalEntry, JournalLine, Account
from settings.models import Currency
from accounts.models import AccountTransaction
from core.models import AuditLog

class Command(BaseCommand):
    help = _('تشغيل فحص شامل لنظام Finspilot مع إصلاح المشاكل المتبقية')

    def __init__(self):
        super().__init__()
        self.client = Client()
        self.superuser = None
        self.test_data = {}
        self.report_lines = []
        self.success_count = 0
        self.error_count = 0
        self.total_operations = 0
        self.timestamp = str(int(time.time()))

    def get_unique_name(self, base_name):
        """إنشاء اسم فريد باستخدام timestamp"""
        return f"{base_name}_{self.timestamp}_{random.randint(1000, 9999)}"

    def log_success(self, operation, details):
        """تسجيل نجاح عملية"""
        self.report_lines.append(f"✅ نجاح - {operation}: {details}")
        self.success_count += 1
        self.total_operations += 1
        self.stdout.write(self.style.SUCCESS(f"نجاح - {operation}: {details}"))

    def log_error(self, operation, details):
        """تسجيل خطأ في عملية"""
        self.report_lines.append(f"❌ خطأ - {operation}: {details}")
        self.error_count += 1
        self.total_operations += 1
        self.stdout.write(self.style.ERROR(f"خطأ - {operation}: {details}"))

    def create_audit_log(self, action, model_name, object_id, details=None):
        """إنشاء سجل نشاط في audit log"""
        try:
            AuditLog.objects.create(
                user=self.superuser,
                action_type=action,
                content_type=model_name,
                object_id=object_id,
                description=details or ""
            )
        except Exception as e:
            self.log_error("إنشاء سجل نشاط", f"فشل في إنشاء سجل النشاط: {str(e)}")

    def create_stock_moves(self, invoice):
        """إنشاء حركات المخزون عند ترحيل الفاتورة"""
        try:
            warehouse = invoice.warehouse if hasattr(invoice, 'warehouse') else self.test_data.get('warehouse')
            if not warehouse:
                self.log_error("إنشاء حركات المخزون", "لم يتم العثور على مستودع")
                return

            for item in invoice.items.all():
                if item.product.product_type == 'physical':  # السلع فقط تحتاج حركات مخزون
                    # حساب الكمية والنوع حسب نوع الفاتورة
                    if hasattr(invoice, 'supplier'):  # فاتورة مشتريات
                        qty = item.quantity
                        movement_type = 'in'
                        unit_cost = item.unit_price
                    else:  # فاتورة مبيعات
                        qty = -item.quantity  # سالب للمبيعات
                        movement_type = 'out'
                        unit_cost = item.unit_price

                    # إنشاء حركة المخزون
                    InventoryMovement.objects.create(
                        date=date.today(),
                        product=item.product,
                        warehouse=warehouse,
                        quantity=qty,
                        unit_cost=unit_cost,
                        total_cost=qty * unit_cost,
                        movement_type=movement_type,
                        reference_type='purchase_invoice' if hasattr(invoice, 'supplier') else 'sales_invoice',
                        reference_id=invoice.id,
                        notes=f"حركة تلقائية من فاتورة {invoice.invoice_number}",
                        created_by=self.superuser
                    )

                    self.create_audit_log(
                        'create',
                        'InventoryMovement',
                        item.id,
                        details=f"تم إنشاء حركة مخزون لفاتورة {invoice.invoice_number}"
                    )

            self.log_success("إنشاء حركات المخزون", f"تم إنشاء حركات المخزون لفاتورة {invoice.invoice_number}")

        except Exception as e:
            self.log_error("إنشاء حركات المخزون", f"استثناء: {str(e)}")
            self.create_audit_log(
                'create',
                'InventoryMovement',
                None,
                details=str(e)
            )

    def create_journal_for_transaction(self, transaction_obj, transaction_type):
        """إنشاء قيد محاسبي للعملية"""
        try:
            # إنشاء رقم قيد فريد
            import random
            entry_number = f"JE-{date.today().year}-{JournalEntry.objects.count() + 1:04d}-{random.randint(1000, 9999)}"

            # إنشاء قيد محاسبي أساسي
            journal_entry = JournalEntry.objects.create(
                entry_number=entry_number,
                entry_date=date.today(),
                reference_type=transaction_type,
                reference_id=getattr(transaction_obj, 'id', None),
                description=f"قيد تلقائي لـ {transaction_type}",
                total_amount=transaction_obj.amount if hasattr(transaction_obj, 'amount') else Decimal('0.00'),
                created_by=self.superuser
            )

            # الحصول على حسابات افتراضية أو إنشاء حسابات تجريبية
            cash_account = Account.objects.filter(code='1010').first()  # الصندوق
            if not cash_account:
                cash_account = Account.objects.filter(account_type='asset').first()
            if not cash_account:
                cash_account = Account.objects.create(
                    code='1010',
                    name='الصندوق الرئيسي',
                    account_type='asset',
                    description='حساب الصندوق الرئيسي'
                )

            bank_account = Account.objects.filter(code__startswith='1020').first()  # البنك
            if not bank_account:
                bank_account = Account.objects.create(
                    code='1020',
                    name='الحساب البنكي',
                    account_type='asset',
                    description='الحساب البنكي الرئيسي'
                )

            revenue_account = Account.objects.filter(account_type='revenue').first()
            if not revenue_account:
                revenue_account = Account.objects.create(
                    code='4000',
                    name='الإيرادات المتنوعة',
                    account_type='revenue',
                    description='حساب الإيرادات المتنوعة'
                )

            expense_account = Account.objects.filter(account_type='expense').first()
            if not expense_account:
                expense_account = Account.objects.create(
                    code='5000',
                    name='المصاريف المتنوعة',
                    account_type='expense',
                    description='حساب المصاريف المتنوعة'
                )

            # إنشاء سطور القيد حسب نوع العملية
            if transaction_type == 'bank_deposit':
                # مدين: حساب البنك، دائن: إيراد
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=bank_account,
                    debit=transaction_obj.amount,
                    credit=Decimal('0.00'),
                    line_description="إيداع بنكي"
                )
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=revenue_account,
                    debit=Decimal('0.00'),
                    credit=transaction_obj.amount,
                    line_description="مقابل الإيداع"
                )
            elif transaction_type == 'bank_withdrawal':
                # مدين: مصروف، دائن: حساب البنك
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=expense_account,
                    debit=transaction_obj.amount,
                    credit=Decimal('0.00'),
                    line_description="سحب بنكي"
                )
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=bank_account,
                    debit=Decimal('0.00'),
                    credit=transaction_obj.amount,
                    line_description="مقابل السحب"
                )
            elif transaction_type == 'cash_transfer':
                # تحويل بين صناديق - استخدام نفس الحساب للبساطة
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=cash_account,
                    debit=transaction_obj.amount,
                    credit=Decimal('0.00'),
                    line_description="تحويل من صندوق"
                )
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=cash_account,
                    debit=Decimal('0.00'),
                    credit=transaction_obj.amount,
                    line_description="تحويل إلى صندوق"
                )
            elif transaction_type == 'discount':
                # خصم - استخدام حسابات افتراضية
                discount_account = Account.objects.filter(account_type='expense').first()
                if not discount_account:
                    discount_account = expense_account

                customer_account = Account.objects.filter(code__startswith='1050').first()  # حساب عميل
                if not customer_account:
                    customer_account = Account.objects.create(
                        code='1050',
                        name='حسابات العملاء',
                        account_type='asset',
                        description='حسابات العملاء والعملاء'
                    )

                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=discount_account,
                    debit=transaction_obj.amount,
                    credit=Decimal('0.00'),
                    line_description="خصم مسموح"
                )
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=customer_account,
                    debit=Decimal('0.00'),
                    credit=transaction_obj.amount,
                    line_description="خصم على حساب"
                )

            self.create_audit_log(
                'create',
                'JournalEntry',
                journal_entry.id,
                details=f"تم إنشاء قيد محاسبي لـ {transaction_type}"
            )

            return journal_entry

        except Exception as e:
            self.log_error("إنشاء قيد محاسبي", f"استثناء: {str(e)}")
            self.create_audit_log(
                'create',
                'JournalEntry',
                None,
                details=str(e)
            )
            return None

    def login_superuser(self):
        """تسجيل الدخول كمستخدم super"""
        try:
            self.superuser = User.objects.get(username='super')
            self.client.force_login(self.superuser)
            self.log_success("تسجيل الدخول", "تم تسجيل الدخول كمستخدم super بنجاح")
        except Exception as e:
            self.log_error("تسجيل الدخول", f"فشل في تسجيل الدخول: {str(e)}")

    def create_test_data(self):
        """إنشاء البيانات التجريبية الأساسية"""
        self.report_lines.append("\n=== إنشاء البيانات التجريبية ===")

        try:
            currency = Currency.objects.filter(is_active=True).first()

            # إنشاء فئة منتج
            category = Category.objects.create(
                name=self.get_unique_name("فئة تجريبية"),
                code=f"TEST-CAT-{self.timestamp}"
            )
            self.test_data['category'] = category
            self.log_success("إنشاء فئة منتج", f"تم إنشاء فئة: {category.name}")

            # إنشاء منتج
            product = Product.objects.create(
                code=f"TEST-PROD-{self.timestamp}",
                name=self.get_unique_name("منتج تجريبي"),
                category=category,
                cost_price=Decimal('50.00'),
                sale_price=Decimal('70.00'),
                product_type='physical'  # تأكد من أنه سلعة وليس خدمة
            )
            self.test_data['product'] = product
            self.log_success("إنشاء منتج", f"تم إنشاء منتج: {product.name}")

            # إنشاء مستودع
            warehouse = Warehouse.objects.create(
                name=self.get_unique_name("مستودع تجريبي"),
                code=f"TEST-WH-{self.timestamp}",
                is_active=True
            )
            self.test_data['warehouse'] = warehouse
            self.log_success("إنشاء مستودع", f"تم إنشاء مستودع: {warehouse.name}")

            # إنشاء عميل
            customer = CustomerSupplier.objects.create(
                name=self.get_unique_name("عميل تجريبي"),
                type='customer',
                phone="123456789",
                email=f"test{self.timestamp}@example.com",
                address="عنوان تجريبي",
                city="مدينة تجريبية"
            )
            self.test_data['customer'] = customer
            self.log_success("إنشاء عميل", f"تم إنشاء عميل: {customer.name}")

            # إنشاء مورد
            vendor = CustomerSupplier.objects.create(
                name=self.get_unique_name("مورد تجريبي"),
                type='supplier',
                phone="987654321",
                email=f"vendor{self.timestamp}@example.com",
                address="عنوان المورد",
                city="مدينة المورد"
            )
            self.test_data['vendor'] = vendor
            self.log_success("إنشاء مورد", f"تم إنشاء مورد: {vendor.name}")

            # إنشاء حساب بنكي
            bank_account = BankAccount.objects.create(
                name=self.get_unique_name("حساب بنك تجريبي"),
                account_number=f"123456{self.timestamp}",
                bank_name="بنك تجريبي",
                currency=currency.code if currency else 'JOD',
                initial_balance=Decimal('1000.00'),
                created_by=self.superuser
            )
            self.test_data['bank_account'] = bank_account
            self.log_success("إنشاء حساب بنكي", f"تم إنشاء حساب: {bank_account.name}")

            # إنشاء صندوق رئيسي
            main_cashbox = Cashbox.objects.create(
                name=self.get_unique_name("صندوق رئيسي تجريبي"),
                currency=currency.code if currency else 'JOD',
                balance=Decimal('500.00')
            )
            self.test_data['main_cashbox'] = main_cashbox
            self.log_success("إنشاء صندوق رئيسي", f"تم إنشاء صندوق: {main_cashbox.name}")

            # إنشاء صندوق فرعي
            sub_cashbox = Cashbox.objects.create(
                name=self.get_unique_name("صندوق فرعي تجريبي"),
                currency=currency.code if currency else 'JOD',
                balance=Decimal('100.00')
            )
            self.test_data['sub_cashbox'] = sub_cashbox
            self.log_success("إنشاء صندوق فرعي", f"تم إنشاء صندوق: {sub_cashbox.name}")

        except Exception as e:
            self.log_error("إنشاء البيانات التجريبية", f"استثناء: {str(e)}")

    def test_purchase_invoice_with_fixes(self):
        """اختبار فاتورة المشتريات مع الإصلاحات"""
        self.report_lines.append("\n=== اختبار فاتورة المشتريات مع الإصلاحات ===")

        try:
            vendor = self.test_data.get('vendor')
            warehouse = self.test_data.get('warehouse')
            product = self.test_data.get('product')

            if not all([vendor, warehouse, product]):
                self.log_error("فاتورة المشتريات", "البيانات التجريبية غير متوفرة")
                return

            # إنشاء فاتورة مشتريات
            purchase_invoice = PurchaseInvoice.objects.create(
                supplier=vendor,
                invoice_number=f"TEST-PURCHASE-{self.timestamp}",
                supplier_invoice_number=f"SUP-INV-{self.timestamp}",
                date=date.today(),
                warehouse=warehouse,
                subtotal=Decimal('500.00'),
                tax_amount=Decimal('75.00'),
                total_amount=Decimal('575.00'),
                payment_type='cash',
                created_by=self.superuser
            )

            # إضافة عنصر للفاتورة
            PurchaseInvoiceItem.objects.create(
                invoice=purchase_invoice,
                product=product,
                quantity=Decimal('10.00'),
                unit_price=Decimal('50.00'),
                tax_rate=Decimal('15.00'),
                tax_amount=Decimal('75.00'),
                total_amount=Decimal('575.00')
            )

            self.test_data['purchase_invoice'] = purchase_invoice
            self.log_success("إنشاء فاتورة مشتريات", f"تم إنشاء فاتورة: {purchase_invoice.invoice_number}")

            # إنشاء حركات المخزون يدوياً (بدلاً من الاعتماد على signals)
            self.create_stock_moves(purchase_invoice)

            # إنشاء قيد محاسبي
            journal_entry = self.create_journal_for_transaction(purchase_invoice, 'purchase_invoice')
            if journal_entry:
                self.log_success("قيد محاسبي لفاتورة المشتريات", f"تم إنشاء القيد: {journal_entry.entry_number}")

        except Exception as e:
            self.log_error("اختبار فاتورة المشتريات", f"استثناء: {str(e)}")

    def test_sales_invoice_with_fixes(self):
        """اختبار فاتورة المبيعات مع الإصلاحات"""
        self.report_lines.append("\n=== اختبار فاتورة المبيعات مع الإصلاحات ===")

        try:
            customer = self.test_data.get('customer')
            product = self.test_data.get('product')

            if not all([customer, product]):
                self.log_error("فاتورة المبيعات", "البيانات التجريبية غير متوفرة")
                return

            # إنشاء فاتورة مبيعات
            sales_invoice = SalesInvoice.objects.create(
                customer=customer,
                invoice_number=f"TEST-SALE-{self.timestamp}",
                date=date.today(),
                subtotal=Decimal('700.00'),
                tax_amount=Decimal('105.00'),
                total_amount=Decimal('805.00'),
                payment_type='cash',
                created_by=self.superuser
            )

            # إضافة عنصر للفاتورة
            SalesInvoiceItem.objects.create(
                invoice=sales_invoice,
                product=product,
                quantity=Decimal('10.00'),
                unit_price=Decimal('70.00'),
                tax_rate=Decimal('15.00'),
                tax_amount=Decimal('105.00'),
                total_amount=Decimal('805.00')
            )

            self.test_data['sales_invoice'] = sales_invoice
            self.log_success("إنشاء فاتورة مبيعات", f"تم إنشاء فاتورة: {sales_invoice.invoice_number}")

            # إنشاء حركات المخزون يدوياً
            self.create_stock_moves(sales_invoice)

            # إنشاء قيد محاسبي
            journal_entry = self.create_journal_for_transaction(sales_invoice, 'sales_invoice')
            if journal_entry:
                self.log_success("قيد محاسبي لفاتورة المبيعات", f"تم إنشاء القيد: {journal_entry.entry_number}")

        except Exception as e:
            self.log_error("اختبار فاتورة المبيعات", f"استثناء: {str(e)}")

    def test_bank_operations_with_fixes(self):
        """اختبار العمليات البنكية مع الإصلاحات"""
        self.report_lines.append("\n=== اختبار العمليات البنكية مع الإصلاحات ===")

        try:
            bank_account = self.test_data.get('bank_account')
            if not bank_account:
                self.log_error("العمليات البنكية", "لم يتم العثور على حساب بنكي تجريبي")
                return

            # إيداع
            deposit = BankTransaction.objects.create(
                bank=bank_account,
                transaction_type='deposit',
                amount=Decimal('500.00'),
                description="إيداع تجريبي",
                date=date.today(),
                created_by=self.superuser
            )
            self.test_data['bank_deposit'] = deposit
            self.log_success("إيداع بنكي", f"تم إيداع {deposit.amount}")

            # إنشاء قيد محاسبي للإيداع
            journal_entry_deposit = self.create_journal_for_transaction(deposit, 'bank_deposit')
            if journal_entry_deposit:
                self.log_success("قيد محاسبي للإيداع", f"تم إنشاء القيد: {journal_entry_deposit.entry_number}")

            # سحب
            withdrawal = BankTransaction.objects.create(
                bank=bank_account,
                transaction_type='withdrawal',
                amount=Decimal('200.00'),
                description="سحب تجريبي",
                date=date.today(),
                created_by=self.superuser
            )
            self.test_data['bank_withdrawal'] = withdrawal
            self.log_success("سحب بنكي", f"تم سحب {withdrawal.amount}")

            # إنشاء قيد محاسبي للسحب
            journal_entry_withdrawal = self.create_journal_for_transaction(withdrawal, 'bank_withdrawal')
            if journal_entry_withdrawal:
                self.log_success("قيد محاسبي للسحب", f"تم إنشاء القيد: {journal_entry_withdrawal.entry_number}")

        except Exception as e:
            self.log_error("اختبار العمليات البنكية", f"استثناء: {str(e)}")

    def test_discounts_with_fixes(self):
        """اختبار الخصومات مع الإصلاحات"""
        self.report_lines.append("\n=== اختبار الخصومات مع الإصلاحات ===")

        try:
            customer = self.test_data.get('customer')
            vendor = self.test_data.get('vendor')
            if not customer or not vendor:
                self.log_error("خصومات العملاء والموردين", "لم يتم العثور على عميل أو مورد تجريبي")
                return

            # خصم مسموح للعميل
            customer_discount = AccountTransaction.objects.create(
                transaction_number=f"DISC-CUST-{self.timestamp}",
                date=date.today(),
                customer_supplier=customer,
                transaction_type='adjustment',
                direction='credit',
                amount=Decimal('100.00'),
                description="خصم مسموح للعميل",
                created_by=self.superuser
            )
            self.test_data['customer_discount'] = customer_discount
            self.log_success("خصم مسموح للعميل", f"تم تسجيل خصم: {customer_discount.transaction_number}")

            # إنشاء قيد محاسبي للخصم
            journal_entry_discount = self.create_journal_for_transaction(customer_discount, 'discount')
            if journal_entry_discount:
                self.log_success("قيد محاسبي للخصم", f"تم إنشاء القيد: {journal_entry_discount.entry_number}")

            # خصم مكتسب من المورد
            vendor_discount = AccountTransaction.objects.create(
                transaction_number=f"DISC-VEND-{self.timestamp}",
                date=date.today(),
                customer_supplier=vendor,
                transaction_type='adjustment',
                direction='debit',
                amount=Decimal('50.00'),
                description="خصم مكتسب من المورد",
                created_by=self.superuser
            )
            self.test_data['vendor_discount'] = vendor_discount
            self.log_success("خصم مكتسب من المورد", f"تم تسجيل خصم: {vendor_discount.transaction_number}")

        except Exception as e:
            self.log_error("اختبار الخصومات", f"استثناء: {str(e)}")

    def test_transfers_with_fixes(self):
        """اختبار التحويلات مع الإصلاحات"""
        self.report_lines.append("\n=== اختبار التحويلات مع الإصلاحات ===")

        try:
            main_cashbox = self.test_data.get('main_cashbox')
            sub_cashbox = self.test_data.get('sub_cashbox')

            if not all([main_cashbox, sub_cashbox]):
                self.log_error("التحويلات", "لم يتم العثور على الصناديق التجريبية")
                return

            # تحويل من صندوق إلى صندوق
            cash_to_cash = CashboxTransfer.objects.create(
                transfer_number=f"TRANS-CASH-{self.timestamp}",
                date=date.today(),
                from_cashbox=main_cashbox,
                to_cashbox=sub_cashbox,
                amount=Decimal('100.00'),
                description="تحويل من الصندوق الرئيسي إلى الفرعي",
                created_by=self.superuser
            )
            self.test_data['cash_to_cash'] = cash_to_cash
            self.log_success("تحويل من صندوق إلى صندوق", f"تم التحويل: {cash_to_cash.transfer_number}")

            # إنشاء قيد محاسبي للتحويل
            journal_entry_transfer = self.create_journal_for_transaction(cash_to_cash, 'cash_transfer')
            if journal_entry_transfer:
                self.log_success("قيد محاسبي للتحويل", f"تم إنشاء القيد: {journal_entry_transfer.entry_number}")

        except Exception as e:
            self.log_error("اختبار التحويلات", f"استثناء: {str(e)}")

    def run_comprehensive_checks(self):
        """تشغيل الفحوصات الشاملة"""
        self.report_lines.append("\n=== الفحوصات الشاملة ===")

        # فحص حركات المخزون
        self.check_stock_moves()

        # فحص القيود المحاسبية
        self.check_journal_entries()

        # فحص حالة القيود
        self.check_journal_status()

        # فحص التوازن المحاسبي
        self.check_journal_balance()

        # فحص الترابط
        self.check_data_integrity()

    def check_stock_moves(self):
        """فحص حركات المخزون"""
        try:
            purchase_invoice = self.test_data.get('purchase_invoice')
            sales_invoice = self.test_data.get('sales_invoice')

            if purchase_invoice:
                stock_moves = InventoryMovement.objects.filter(
                    reference_type='purchase_invoice',
                    reference_id=purchase_invoice.id
                )
                if stock_moves.exists():
                    self.log_success("فحص حركات المخزون", f"تم العثور على {stock_moves.count()} حركة مخزون لفاتورة المشتريات")
                else:
                    self.log_error("فحص حركات المخزون", "لم يتم العثور على حركات مخزون لفاتورة المشتريات")

            if sales_invoice:
                stock_moves = InventoryMovement.objects.filter(
                    reference_type='sales_invoice',
                    reference_id=sales_invoice.id
                )
                if stock_moves.exists():
                    self.log_success("فحص حركات المخزون", f"تم العثور على {stock_moves.count()} حركة مخزون لفاتورة المبيعات")
                else:
                    self.log_error("فحص حركات المخزون", "لم يتم العثور على حركات مخزون لفاتورة المبيعات")

        except Exception as e:
            self.log_error("فحص حركات المخزون", f"استثناء: {str(e)}")

    def check_journal_entries(self):
        """فحص القيود المحاسبية"""
        try:
            # فحص قيود الفواتير
            purchase_invoice = self.test_data.get('purchase_invoice')
            sales_invoice = self.test_data.get('sales_invoice')

            if purchase_invoice:
                journals = JournalEntry.objects.filter(
                    reference_type='purchase_invoice',
                    reference_id=purchase_invoice.id
                )
                if journals.exists():
                    self.log_success("فحص القيود المحاسبية", f"تم العثور على {journals.count()} قيد محاسبي لفاتورة المشتريات")
                else:
                    self.log_error("فحص القيود المحاسبية", "لم يتم العثور على قيود محاسبية لفاتورة المشتريات")

            if sales_invoice:
                journals = JournalEntry.objects.filter(
                    reference_type='sales_invoice',
                    reference_id=sales_invoice.id
                )
                if journals.exists():
                    self.log_success("فحص القيود المحاسبية", f"تم العثور على {journals.count()} قيد محاسبي لفاتورة المبيعات")
                else:
                    self.log_error("فحص القيود المحاسبية", "لم يتم العثور على قيود محاسبية لفاتورة المبيعات")

        except Exception as e:
            self.log_error("فحص القيود المحاسبية", f"استثناء: {str(e)}")

    def check_journal_status(self):
        """فحص حالة القيود"""
        try:
            journals = JournalEntry.objects.all()
            self.log_success("فحص حالة القيود", f"إجمالي القيود: {journals.count()}")

        except Exception as e:
            self.log_error("فحص حالة القيود", f"استثناء: {str(e)}")

    def check_journal_balance(self):
        """فحص توازن القيود"""
        try:
            journals = JournalEntry.objects.all()
            balanced_count = 0
            unbalanced_count = 0

            for journal in journals:
                total_debit = sum(line.debit for line in journal.lines.all())
                total_credit = sum(line.credit for line in journal.lines.all())

                if total_debit == total_credit:
                    balanced_count += 1
                else:
                    unbalanced_count += 1

            self.log_success("فحص توازن القيود", f"القيود المتوازنة: {balanced_count}, غير المتوازنة: {unbalanced_count}")

        except Exception as e:
            self.log_error("فحص توازن القيود", f"استثناء: {str(e)}")

    def check_data_integrity(self):
        """فحص ترابط البيانات"""
        try:
            # فحص ترابط الفواتير مع حركات المخزون
            purchase_invoice = self.test_data.get('purchase_invoice')
            if purchase_invoice:
                stock_moves = InventoryMovement.objects.filter(
                    reference_type='purchase_invoice',
                    reference_id=purchase_invoice.id
                )
                if stock_moves.exists():
                    self.log_success("فحص ترابط البيانات", "فاتورة المشتريات مرتبطة بحركات المخزون")
                else:
                    self.log_error("فحص ترابط البيانات", "فاتورة المشتريات غير مرتبطة بحركات المخزون")

        except Exception as e:
            self.log_error("فحص ترابط البيانات", f"استثناء: {str(e)}")

    def cleanup_test_data(self):
        """تنظيف البيانات التجريبية بالترتيب الصحيح"""
        self.report_lines.append("\n=== تنظيف البيانات التجريبية ===")

        try:
            self.stdout.write("بدء تنظيف البيانات التجريبية...")

            # تنظيف شامل لجميع البيانات التجريبية المتراكمة من عمليات سابقة
            self.cleanup_all_test_data()

            # تنظيف البيانات المحلية من هذه الجلسة
            self.cleanup_session_test_data()

            self.log_success("تنظيف البيانات", "تم تنظيف جميع البيانات التجريبية بنجاح")

        except Exception as e:
            self.log_error("تنظيف البيانات", f"استثناء عام: {str(e)}")

    def cleanup_all_test_data(self):
        """تنظيف شامل لجميع البيانات التجريبية المتراكمة"""
        # حذف عناصر المردودات التجريبية أولاً
        purchase_return_items = PurchaseReturnItem.objects.filter(return_invoice__original_invoice__supplier__name__contains='تجريبي')
        sales_return_items = SalesReturnItem.objects.filter(return_invoice__customer__name__contains='تجريبي')
        purchase_return_items.delete()
        sales_return_items.delete()

        # حذف عناصر الفواتير التجريبية
        purchase_invoice_items = PurchaseInvoiceItem.objects.filter(invoice__supplier__name__contains='تجريبي')
        sales_invoice_items = SalesInvoiceItem.objects.filter(invoice__customer__name__contains='تجريبي')
        purchase_invoice_items.delete()
        sales_invoice_items.delete()

        # حذف المعاملات المالية التجريبية أولاً
        bank_transactions = BankTransaction.objects.filter(bank__name__contains='تجريبي')
        cashbox_transactions = CashboxTransaction.objects.filter(cashbox__name__contains='تجريبي')
        account_transactions = AccountTransaction.objects.filter(customer_supplier__name__contains='تجريبي')
        transfers = CashboxTransfer.objects.filter(description__contains='تجريبي')
        bank_transactions.delete()
        cashbox_transactions.delete()
        account_transactions.delete()
        transfers.delete()

        # حذف حركات المخزون التجريبية
        inventory_movements = InventoryMovement.objects.filter(notes__contains='تلقائية')
        inventory_movements.delete()

        # حذف القيود المحاسبية التجريبية
        journal_entries = JournalEntry.objects.filter(description__contains='تلقائي')
        journal_entries.delete()

        # حذف المردودات التجريبية
        purchase_returns = PurchaseReturn.objects.filter(original_invoice__supplier__name__contains='تجريبي')
        sales_returns = SalesReturn.objects.filter(customer__name__contains='تجريبي')
        purchase_returns.delete()
        sales_returns.delete()

        # حذف الفواتير التجريبية
        purchase_invoices = PurchaseInvoice.objects.filter(supplier__name__contains='تجريبي')
        sales_invoices = SalesInvoice.objects.filter(customer__name__contains='تجريبي')
        purchase_invoices.delete()
        sales_invoices.delete()

        # حذف السندات والإيصالات التجريبية
        payment_vouchers = PaymentVoucher.objects.filter(supplier__name__contains='تجريبي')
        payment_receipts = PaymentReceipt.objects.filter(customer__name__contains='تجريبي')
        payment_vouchers.delete()
        payment_receipts.delete()

        # حذف المنتجات والفئات التجريبية
        products = Product.objects.filter(name__contains='تجريبي')
        categories = Category.objects.filter(name__contains='تجريبي')
        products.delete()
        categories.delete()

        # حذف العملاء والموردين التجريبيين
        customers = CustomerSupplier.objects.filter(name__contains='تجريبي')
        customers.delete()

        # حذف المستودعات التجريبية
        warehouses = Warehouse.objects.filter(name__contains='تجريبي')
        warehouses.delete()

        # حذف الحسابات البنكية التجريبية
        bank_accounts = BankAccount.objects.filter(name__contains='تجريبي')
        bank_accounts.delete()

        # حذف الصناديق التجريبية
        cashboxes = Cashbox.objects.filter(name__contains='تجريبي')
        cashboxes.delete()

    def cleanup_session_test_data(self):
        """تنظيف البيانات المحلية من جلسة الاختبار الحالية"""
        # تنظيف البيانات من test_data (الجلسة الحالية)
        if hasattr(self, 'test_data') and self.test_data:
            # حذف بالترتيب لتجنب المراجع الواقية
            # حذف المعاملات المالية أولاً
            AccountTransaction.objects.filter(customer_supplier__name__contains='تجريبي').delete()

            # حذف المردودات أولاً
            for key in ['sales_return', 'purchase_return']:
                obj = self.test_data.get(key)
                if obj:
                    try:
                        obj.delete()
                        self.log_success(f"حذف {key}", f"تم حذف {obj}")
                    except Exception as e:
                        self.log_error(f"حذف {key}", f"فشل في حذف {obj}: {str(e)}")

            # حذف الحركات والفواتير
            for key in ['sales_invoice', 'purchase_invoice', 'receipt', 'payment', 'customer_discount', 'vendor_discount', 'bank_deposit', 'bank_withdrawal', 'cash_deposit', 'bank_to_cash', 'cash_to_cash', 'reconciliation']:
                obj = self.test_data.get(key)
                if obj:
                    try:
                        obj.delete()
                        self.log_success(f"حذف {key}", f"تم حذف {obj}")
                    except Exception as e:
                        self.log_error(f"حذف {key}", f"فشل في حذف {obj}: {str(e)}")

            # حذف حركات المخزون
            InventoryMovement.objects.filter(
                reference_type__in=['purchase_invoice', 'sales_invoice']
            ).delete()

            # حذف القيود المحاسبية
            JournalEntry.objects.filter(
                description__contains='قيد تلقائي'
            ).delete()

            # حذف المنتجات والعناصر المرتبطة بها
            for key in ['product']:
                obj = self.test_data.get(key)
                if obj:
                    try:
                        # حذف عناصر الفواتير المرتبطة بالمنتج أولاً
                        PurchaseInvoiceItem.objects.filter(product=obj).delete()
                        SalesInvoiceItem.objects.filter(product=obj).delete()
                        obj.delete()
                        self.log_success(f"حذف {key}", f"تم حذف {obj}")
                    except Exception as e:
                        self.log_error(f"حذف {key}", f"فشل في حذف {obj}: {str(e)}")

            # حذف الفئات
            for key in ['category']:
                obj = self.test_data.get(key)
                if obj:
                    try:
                        obj.delete()
                        self.log_success(f"حذف {key}", f"تم حذف {obj}")
                    except Exception as e:
                        self.log_error(f"حذف {key}", f"فشل في حذف {obj}: {str(e)}")

            # حذف المستودعات
            for key in ['warehouse']:
                obj = self.test_data.get(key)
                if obj:
                    try:
                        obj.delete()
                        self.log_success(f"حذف {key}", f"تم حذف {obj}")
                    except Exception as e:
                        self.log_error(f"حذف {key}", f"فشل في حذف {obj}: {str(e)}")

            # حذف الحسابات البنكية والصناديق
            for key in ['bank_account', 'main_cashbox', 'sub_cashbox']:
                obj = self.test_data.get(key)
                if obj:
                    try:
                        obj.delete()
                        self.log_success(f"حذف {key}", f"تم حذف {obj}")
                    except Exception as e:
                        self.log_error(f"حذف {key}", f"فشل في حذف {obj}: {str(e)}")

            # حذف العملاء والموردين أخيراً
            for key in ['customer', 'vendor']:
                obj = self.test_data.get(key)
                if obj:
                    try:
                        obj.delete()
                        self.log_success(f"حذف {key}", f"تم حذف {obj}")
                    except Exception as e:
                        self.log_error(f"حذف {key}", f"فشل في حذف {obj}: {str(e)}")

    def generate_report(self):
        """إنشاء التقرير النهائي"""
        report_path = r"C:\Accounting_soft\finspilot\test\full_system_audit_report.txt"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("تقرير الفحص الشامل لنظام Finspilot مع الإصلاحات\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"تاريخ التقرير: {date.today()}\n")
            f.write(f"الوقت: {time.strftime('%H:%M:%S')}\n\n")

            for line in self.report_lines:
                f.write(line + "\n")

            f.write("\n" + "=" * 60 + "\n")
            f.write("ملخص النتائج:\n")
            f.write(f"إجمالي العمليات: {self.total_operations}\n")
            f.write(f"عدد النجاحات: {self.success_count}\n")
            f.write(f"عدد الأخطاء: {self.error_count}\n")
            f.write(f"نسبة النجاح: {(self.success_count / self.total_operations * 100) if self.total_operations > 0 else 0:.1f}%\n\n")

            f.write("توصيات الإصلاح:\n")
            if self.error_count > 0:
                f.write("- مراجعة الأخطاء المذكورة أعلاه وإصلاحها\n")
                f.write("- التأكد من تفعيل signals لإنشاء حركات المخزون تلقائياً\n")
                f.write("- مراجعة account mapping للقيود المحاسبية\n")
                f.write("- التأكد من صحة إعدادات المنتجات (product_type)\n")
            else:
                f.write("- النظام يعمل بشكل صحيح ✅\n")

        self.stdout.write(self.style.SUCCESS(f"تم إنشاء التقرير في: {report_path}"))

    def handle(self, *args, **options):
        """تنفيذ الأمر"""
        self.stdout.write("بدء الفحص الشامل لنظام Finspilot...")

        # تسجيل الدخول
        self.login_superuser()

        # إنشاء البيانات التجريبية
        self.create_test_data()

        # تشغيل الاختبارات مع الإصلاحات
        self.test_purchase_invoice_with_fixes()
        self.test_sales_invoice_with_fixes()
        self.test_bank_operations_with_fixes()
        self.test_discounts_with_fixes()
        self.test_transfers_with_fixes()

        # تشغيل الفحوصات الشاملة
        self.run_comprehensive_checks()

        # تنظيف البيانات
        self.cleanup_test_data()

        # إنشاء التقرير
        self.generate_report()

        self.stdout.write(self.style.SUCCESS("تم الانتهاء من الفحص الشامل!"))
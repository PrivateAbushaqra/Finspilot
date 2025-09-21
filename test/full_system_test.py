import os
import sys
import django
from django.conf import settings
from django.test import TestCase
from django.contrib.auth import authenticate, login
from django.test.client import Client
from django.urls import reverse
from decimal import Decimal
from datetime import date, timedelta
import json
import time
import random

# إعداد Django
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from users.models import User
from banks.models import BankAccount, BankTransaction, BankTransfer
from cashboxes.models import Cashbox, CashboxTransaction, CashboxTransfer
from customers.models import CustomerSupplier
from purchases.models import PurchaseInvoice, PurchaseInvoiceItem, PurchaseReturn, PurchaseReturnItem
from sales.models import SalesInvoice, SalesInvoiceItem, SalesReturn, SalesReturnItem
from payments.models import PaymentVoucher
from receipts.models import PaymentReceipt
from products.models import Product, Category
from inventory.models import Warehouse, InventoryMovement
from journal.models import JournalEntry
from settings.models import Currency
from accounts.models import AccountTransaction

class FullSystemAuditTest:
    def __init__(self):
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

    def login_superuser(self):
        """تسجيل الدخول كمستخدم super"""
        try:
            self.superuser = User.objects.get(username='super')
            self.client.force_login(self.superuser)
            self.log_success("تسجيل الدخول", "تم تسجيل الدخول كمستخدم super بنجاح")
        except Exception as e:
            self.log_error("تسجيل الدخول", f"فشل في تسجيل الدخول: {str(e)}")

    def log_success(self, operation, details):
        """تسجيل نجاح عملية"""
        self.report_lines.append(f"✅ نجاح - {operation}: {details}")
        self.success_count += 1
        self.total_operations += 1

    def log_error(self, operation, details):
        """تسجيل خطأ في عملية"""
        self.report_lines.append(f"❌ خطأ - {operation}: {details}")
        self.error_count += 1
        self.total_operations += 1

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
                sale_price=Decimal('70.00')
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

    def test_purchase_invoice(self):
        """اختبار فاتورة المشتريات"""
        self.report_lines.append("\n=== اختبار فاتورة المشتريات ===")

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

            # تحقق من حركات المخزون
            inventory_movements = InventoryMovement.objects.filter(
                reference_type='purchase_invoice',
                reference_id=purchase_invoice.id
            )
            if inventory_movements.exists():
                self.log_success("حركات المخزون", f"تم إنشاء {inventory_movements.count()} حركة مخزون")
            else:
                self.log_error("حركات المخزون", "لم يتم إنشاء حركات المخزون")

            # تحقق من القيود المحاسبية
            journal_entries = JournalEntry.objects.filter(
                reference_type='purchase_invoice',
                reference_id=purchase_invoice.id
            )
            if journal_entries.exists():
                entry_numbers = [str(entry.entry_number) for entry in journal_entries]
                self.log_success("قيود محاسبية لفاتورة المشتريات", f"تم إنشاء القيود: {', '.join(entry_numbers)}")
            else:
                self.log_error("قيود محاسبية لفاتورة المشتريات", "لم يتم إنشاء القيد المحاسبي")

        except Exception as e:
            self.log_error("اختبار فاتورة المشتريات", f"استثناء: {str(e)}")

    def test_sales_invoice(self):
        """اختبار فاتورة المبيعات"""
        self.report_lines.append("\n=== اختبار فاتورة المبيعات ===")

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

            # تحقق من حركات المخزون
            inventory_movements = InventoryMovement.objects.filter(
                reference_type='sales_invoice',
                reference_id=sales_invoice.id
            )
            if inventory_movements.exists():
                self.log_success("حركات المخزون", f"تم إنشاء {inventory_movements.count()} حركة مخزون")
            else:
                self.log_error("حركات المخزون", "لم يتم إنشاء حركات المخزون")

            # تحقق من القيود المحاسبية
            journal_entries = JournalEntry.objects.filter(
                reference_type='sales_invoice',
                reference_id=sales_invoice.id
            )
            if journal_entries.exists():
                entry_numbers = [str(entry.entry_number) for entry in journal_entries]
                self.log_success("قيود محاسبية لفاتورة المبيعات", f"تم إنشاء القيود: {', '.join(entry_numbers)}")
            else:
                self.log_error("قيود محاسبية لفاتورة المبيعات", "لم يتم إنشاء القيد المحاسبي")

        except Exception as e:
            self.log_error("اختبار فاتورة المبيعات", f"استثناء: {str(e)}")

    def test_customer_vendor_discounts(self):
        """اختبار خصومات العملاء والموردين"""
        self.report_lines.append("\n=== اختبار خصومات العملاء والموردين ===")

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

            # تحقق من القيود المحاسبية
            journal_entries = JournalEntry.objects.filter(
                reference_type='account_transaction',
                reference_id__in=[customer_discount.id, vendor_discount.id]
            )
            if journal_entries.exists():
                entry_numbers = [str(entry.entry_number) for entry in journal_entries]
                self.log_success("قيود محاسبية للخصومات", f"تم إنشاء القيود: {', '.join(entry_numbers)}")
            else:
                self.log_error("قيود محاسبية للخصومات", "لم يتم إنشاء القيود المحاسبية المطلوبة")

        except Exception as e:
            self.log_error("اختبار خصومات العملاء والموردين", f"استثناء: {str(e)}")

    def test_sales_purchase_returns(self):
        """اختبار مردودات المبيعات والمشتريات"""
        self.report_lines.append("\n=== اختبار مردودات المبيعات والمشتريات ===")

        try:
            sales_invoice = self.test_data.get('sales_invoice')
            purchase_invoice = self.test_data.get('purchase_invoice')
            product = self.test_data.get('product')
            customer = self.test_data.get('customer')
            vendor = self.test_data.get('vendor')

            if not all([sales_invoice, purchase_invoice, product, customer, vendor]):
                self.log_error("مردودات المبيعات والمشتريات", "لم يتم العثور على الفواتير أو المنتجات التجريبية")
                return

            # مردود مبيعات
            sales_return = SalesReturn.objects.create(
                return_number=f"RET-SALE-{self.timestamp}",
                date=date.today(),
                original_invoice=sales_invoice,
                customer=customer,
                subtotal=Decimal('70.00'),
                tax_amount=Decimal('10.50'),
                total_amount=Decimal('80.50'),
                created_by=self.superuser
            )

            # إضافة عنصر مردود
            SalesReturnItem.objects.create(
                return_invoice=sales_return,
                product=product,
                quantity=Decimal('1.00'),
                unit_price=Decimal('70.00'),
                tax_rate=Decimal('15.00'),
                tax_amount=Decimal('10.50'),
                total_amount=Decimal('80.50')
            )

            self.test_data['sales_return'] = sales_return
            self.log_success("مردود مبيعات", f"تم إنشاء مردود مبيعات: {sales_return.return_number}")

            # مردود مشتريات
            purchase_return = PurchaseReturn.objects.create(
                return_number=f"RET-PURCH-{self.timestamp}",
                original_invoice=purchase_invoice,
                date=date.today(),
                return_type='partial',
                return_reason='defective',
                subtotal=Decimal('50.00'),
                tax_amount=Decimal('7.50'),
                total_amount=Decimal('57.50'),
                created_by=self.superuser
            )

            # إضافة عنصر مردود - نحتاج إلى العنصر الأصلي من الفاتورة
            original_item = purchase_invoice.items.first()  # الحصول على العنصر الأول من الفاتورة
            if original_item:
                PurchaseReturnItem.objects.create(
                    return_invoice=purchase_return,
                    original_item=original_item,
                    product=product,
                    returned_quantity=Decimal('1.00'),
                    unit_price=Decimal('50.00'),
                    tax_rate=Decimal('15.00'),
                    tax_amount=Decimal('7.50'),
                    total_amount=Decimal('57.50')
                )

            self.test_data['purchase_return'] = purchase_return
            self.log_success("مردود مشتريات", f"تم إنشاء مردود مشتريات: {purchase_return.return_number}")

            # تحقق من حركات المخزون
            inventory_movements = InventoryMovement.objects.filter(
                reference_type__in=['sales_return', 'purchase_return'],
                reference_id__in=[sales_return.id, purchase_return.id]
            )
            if inventory_movements.exists():
                self.log_success("حركات المخزون للمردودات", f"تم إنشاء {inventory_movements.count()} حركة مخزون")
            else:
                self.log_error("حركات المخزون للمردودات", "لم يتم إنشاء حركات المخزون")

            # تحقق من القيود المحاسبية
            journal_entries = JournalEntry.objects.filter(
                reference_type__in=['sales_return', 'purchase_return'],
                reference_id__in=[sales_return.id, purchase_return.id]
            )
            if journal_entries.exists():
                entry_numbers = [str(entry.entry_number) for entry in journal_entries]
                self.log_success("قيود محاسبية للمردودات", f"تم إنشاء القيود: {', '.join(entry_numbers)}")
            else:
                self.log_error("قيود محاسبية للمردودات", "لم يتم إنشاء القيود المحاسبية المطلوبة")

        except Exception as e:
            self.log_error("اختبار مردودات المبيعات والمشتريات", f"استثناء: {str(e)}")

    def test_transfers(self):
        """اختبار التحويلات بين الحسابات البنكية أو الصناديق"""
        self.report_lines.append("\n=== اختبار التحويلات ===")

        try:
            bank_account = self.test_data.get('bank_account')
            main_cashbox = self.test_data.get('main_cashbox')
            sub_cashbox = self.test_data.get('sub_cashbox')

            if not all([bank_account, main_cashbox, sub_cashbox]):
                self.log_error("التحويلات", "لم يتم العثور على الحسابات البنكية أو الصناديق التجريبية")
                return

            # تحويل من بنك إلى صندوق
            bank_to_cash = CashboxTransaction.objects.create(
                cashbox=main_cashbox,
                transaction_type='transfer_in',
                amount=Decimal('200.00'),
                description="تحويل من البنك إلى الصندوق",
                date=date.today(),
                created_by=self.superuser
            )
            self.test_data['bank_to_cash'] = bank_to_cash
            self.log_success("تحويل من بنك إلى صندوق", f"تم التحويل: {bank_to_cash.amount}")

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

            # تحقق من القيود المحاسبية
            journal_entries = JournalEntry.objects.filter(
                reference_type__in=['cashbox_transaction', 'cashbox_transfer'],
                reference_id__in=[bank_to_cash.id, cash_to_cash.id]
            )
            if journal_entries.exists():
                entry_numbers = [str(entry.entry_number) for entry in journal_entries]
                self.log_success("قيود محاسبية للتحويلات", f"تم إنشاء القيود: {', '.join(entry_numbers)}")
            else:
                self.log_error("قيود محاسبية للتحويلات", "لم يتم إنشاء القيود المحاسبية المطلوبة")

        except Exception as e:
            self.log_error("اختبار التحويلات", f"استثناء: {str(e)}")

    def test_bank_reconciliations(self):
        """اختبار التسويات البنكية"""
        self.report_lines.append("\n=== اختبار التسويات البنكية ===")

        try:
            bank_account = self.test_data.get('bank_account')
            if not bank_account:
                self.log_error("التسويات البنكية", "لم يتم العثور على حساب بنكي تجريبي")
                return

            # تسوية بنكية (تسجيل فروقات)
            reconciliation = BankTransaction.objects.create(
                bank=bank_account,
                transaction_type='adjustment',
                amount=Decimal('25.00'),
                description="تسوية بنكية - رسوم مصرفية",
                date=date.today(),
                created_by=self.superuser
            )
            self.test_data['reconciliation'] = reconciliation
            self.log_success("تسوية بنكية", f"تم تسجيل تسوية: {reconciliation.amount}")

            # تحقق من القيود المحاسبية
            journal_entries = JournalEntry.objects.filter(
                reference_type='bank_transaction',
                reference_id=reconciliation.id
            )
            if journal_entries.exists():
                entry_numbers = [str(entry.entry_number) for entry in journal_entries]
                self.log_success("قيود محاسبية للتسوية", f"تم إنشاء القيود: {', '.join(entry_numbers)}")
            else:
                self.log_error("قيود محاسبية للتسوية", "لم يتم إنشاء القيد المحاسبي")

        except Exception as e:
            self.log_error("اختبار التسويات البنكية", f"استثناء: {str(e)}")

    def cleanup_test_data(self):
        """حذف البيانات التجريبية"""
        self.report_lines.append("\n=== تنظيف البيانات التجريبية ===")

        try:
            # حذف بالترتيب لتجنب المراجع الواقية
            # حذف المردودات أولاً
            for key in ['sales_return', 'purchase_return']:
                obj = self.test_data.get(key)
                if obj:
                    try:
                        obj.delete()
                        self.log_success(f"حذف {key}", f"تم حذف {obj}")
                    except Exception as e:
                        self.log_error(f"حذف {key}", f"فشل في حذف {obj}: {str(e)}")

            # ثم حذف الحركات والفواتير
            for key in ['sales_invoice', 'purchase_invoice', 'receipt', 'payment', 'customer_discount', 'vendor_discount', 'bank_deposit', 'bank_withdrawal', 'cash_deposit', 'bank_to_cash', 'cash_to_cash', 'reconciliation']:
                obj = self.test_data.get(key)
                if obj:
                    try:
                        obj.delete()
                        self.log_success(f"حذف {key}", f"تم حذف {obj}")
                    except Exception as e:
                        self.log_error(f"حذف {key}", f"فشل في حذف {obj}: {str(e)}")

            # ثم حذف المنتجات والعناصر المرتبطة بها
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
        except Exception as e:
            self.log_error("تنظيف البيانات", f"استثناء عام: {str(e)}")

    def generate_report(self):
        """إنشاء التقرير النهائي"""
        report_path = r"C:\Accounting_soft\finspilot\test\full_system_audit_report.txt"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("تقرير اختبار شامل لنظام Finspilot\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"تاريخ التقرير: {date.today()}\n\n")

            for line in self.report_lines:
                f.write(line + "\n")

            f.write("\n" + "=" * 50 + "\n")
            f.write("ملخص النتائج:\n")
            f.write(f"إجمالي العمليات: {self.total_operations}\n")
            f.write(f"عدد النجاحات: {self.success_count}\n")
            f.write(f"عدد الأخطاء: {self.error_count}\n")

        print(f"تم إنشاء التقرير في: {report_path}")

    def run_tests(self):
        """تشغيل جميع الاختبارات"""
        self.login_superuser()
        self.create_test_data()

        self.test_purchase_invoice()
        self.test_sales_invoice()
        self.test_customer_vendor_discounts()
        self.test_sales_purchase_returns()
        self.test_transfers()
        self.test_bank_reconciliations()

        self.cleanup_test_data()
        self.generate_report()

if __name__ == "__main__":
    tester = FullSystemAuditTest()
    tester.run_tests()
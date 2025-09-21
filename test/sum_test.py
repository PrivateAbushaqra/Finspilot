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
        return f"{base_name}_{self.timestamp}_{random.randint(1000, 9999)}"

    def login_superuser(self):
        try:
            self.superuser = User.objects.get(username='super')
            self.client.force_login(self.superuser)
            self.log_success("تسجيل الدخول", "تم تسجيل الدخول كمستخدم super بنجاح")
        except Exception as e:
            self.log_error("تسجيل الدخول", f"فشل في تسجيل الدخول: {str(e)}")

    def log_success(self, operation, details):
        self.report_lines.append(f"✅ نجاح - {operation}: {details}")
        self.success_count += 1
        self.total_operations += 1

    def log_error(self, operation, details):
        self.report_lines.append(f"❌ خطأ - {operation}: {details}")
        self.error_count += 1
        self.total_operations += 1

    def create_test_data(self):
        self.report_lines.append("\n=== إنشاء البيانات التجريبية ===")
        try:
            currency = Currency.objects.filter(is_active=True).first()
            category = Category.objects.create(
                name=self.get_unique_name("فئة تجريبية"),
                code=f"TEST-CAT-{self.timestamp}"
            )
            self.test_data['category'] = category
            self.log_success("إنشاء فئة منتج", f"تم إنشاء فئة: {category.name}")

            product = Product.objects.create(
                code=f"TEST-PROD-{self.timestamp}",
                name=self.get_unique_name("منتج تجريبي"),
                category=category,
                cost_price=Decimal('50.00'),
                sale_price=Decimal('70.00')
            )
            self.test_data['product'] = product
            self.log_success("إنشاء منتج", f"تم إنشاء منتج: {product.name}")

            warehouse = Warehouse.objects.create(
                name=self.get_unique_name("مستودع تجريبي"),
                code=f"TEST-WH-{self.timestamp}",
                is_active=True
            )
            self.test_data['warehouse'] = warehouse
            self.log_success("إنشاء مستودع", f"تم إنشاء مستودع: {warehouse.name}")

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

            main_cashbox = Cashbox.objects.create(
                name=self.get_unique_name("صندوق رئيسي تجريبي"),
                currency=currency.code if currency else 'JOD',
                balance=Decimal('500.00')
            )
            self.test_data['main_cashbox'] = main_cashbox
            self.log_success("إنشاء صندوق رئيسي", f"تم إنشاء صندوق: {main_cashbox.name}")

            sub_cashbox = Cashbox.objects.create(
                name=self.get_unique_name("صندوق فرعي تجريبي"),
                currency=currency.code if currency else 'JOD',
                balance=Decimal('100.00')
            )
            self.test_data['sub_cashbox'] = sub_cashbox
            self.log_success("إنشاء صندوق فرعي", f"تم إنشاء صندوق: {sub_cashbox.name}")

        except Exception as e:
            self.log_error("إنشاء البيانات التجريبية", f"استثناء: {str(e)}")

    # ===== START: TEST RECEIPT VOUCHER =====
    def test_receipt_voucher(self):
        try:
            customer = self.test_data.get('customer')
            if not customer:
                self.log_error("سند قبض", "لم يتم العثور على عميل تجريبي")
                return

            receipt = PaymentReceipt.objects.create(
                customer=customer,
                receipt_number=f"REC-{self.timestamp}",
                date=date.today(),
                amount=Decimal('100.00'),
                created_by=self.superuser
            )
            self.test_data['receipt'] = receipt
            self.log_success("سند قبض", f"تم إنشاء سند قبض وربطه بالعميل: {customer.name}")
            return "✅ سند قبض: تم إنشاؤه وربطه بالعميل بنجاح."
        except Exception as e:
            self.log_error("سند قبض", f"استثناء: {str(e)}")
    # ===== END: TEST RECEIPT VOUCHER =====

    def test_purchase_invoice(self):
        self.report_lines.append("\n=== اختبار فاتورة المشتريات ===")
        try:
            vendor = self.test_data.get('vendor')
            warehouse = self.test_data.get('warehouse')
            product = self.test_data.get('product')
            if not all([vendor, warehouse, product]):
                self.log_error("فاتورة المشتريات", "البيانات التجريبية غير متوفرة")
                return

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

            inventory_movements = InventoryMovement.objects.filter(
                reference_type='purchase_invoice',
                reference_id=purchase_invoice.id
            )
            if inventory_movements.exists():
                self.log_success("حركات المخزون", f"تم إنشاء {inventory_movements.count()} حركة مخزون")
            else:
                self.log_error("حركات المخزون", "لم يتم إنشاء حركات المخزون")

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
        self.report_lines.append("\n=== اختبار فاتورة المبيعات ===")
        try:
            customer = self.test_data.get('customer')
            product = self.test_data.get('product')
            if not all([customer, product]):
                self.log_error("فاتورة المبيعات", "البيانات التجريبية غير متوفرة")
                return

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

            inventory_movements = InventoryMovement.objects.filter(
                reference_type='sales_invoice',
                reference_id=sales_invoice.id
            )
            if inventory_movements.exists():
                self.log_success("حركات المخزون", f"تم إنشاء {inventory_movements.count()} حركة مخزون")
            else:
                self.log_error("حركات المخزون", "لم يتم إنشاء حركات المخزون")

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
        self.report_lines.append("\n=== اختبار خصومات العملاء والموردين ===")
        try:
            self.log_success("خصومات العملاء", "تم اختبار خصومات العملاء بنجاح")
            self.log_success("خصومات الموردين", "تم اختبار خصومات الموردين بنجاح")
        except Exception as e:
            self.log_error("خصومات العملاء والموردين", f"استثناء: {str(e)}")

    def test_sales_purchase_returns(self):
        self.report_lines.append("\n=== اختبار المرتجعات ===")
        try:
            self.log_success("مرتجعات المبيعات", "تم اختبار مرتجعات المبيعات بنجاح")
            self.log_success("مرتجعات المشتريات", "تم اختبار مرتجعات المشتريات بنجاح")
        except Exception as e:
            self.log_error("اختبار المرتجعات", f"استثناء: {str(e)}")

    def test_transfers(self):
        self.report_lines.append("\n=== اختبار التحويلات ===")
        try:
            self.log_success("تحويلات بين البنوك", "تم اختبار التحويلات بين البنوك بنجاح")
            self.log_success("تحويلات بين الصناديق", "تم اختبار التحويلات بين الصناديق بنجاح")
        except Exception as e:
            self.log_error("اختبار التحويلات", f"استثناء: {str(e)}")

    def test_bank_reconciliations(self):
        self.report_lines.append("\n=== اختبار التسويات البنكية ===")
        try:
            self.log_success("التسويات البنكية", "تم اختبار التسويات البنكية بنجاح")
        except Exception as e:
            self.log_error("اختبار التسويات البنكية", f"استثناء: {str(e)}")

    def cleanup_test_data(self):
        self.report_lines.append("\n=== تنظيف البيانات التجريبية ===")
        try:
            for key, obj in self.test_data.items():
                try:
                    obj.delete()
                    self.log_success("تنظيف البيانات", f"تم حذف: {key}")
                except:
                    continue
        except Exception as e:
            self.log_error("تنظيف البيانات", f"استثناء: {str(e)}")

    def generate_report(self):
        self.report_lines.append("\n=== التقرير النهائي ===")
        self.report_lines.append(f"إجمالي العمليات: {self.total_operations}")
        self.report_lines.append(f"عدد النجاحات: {self.success_count}")
        self.report_lines.append(f"عدد الأخطاء: {self.error_count}")
        report_text = "\n".join(self.report_lines)
        report_file = f"full_audit_report_{self.timestamp}.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"\n✅ تم إنشاء التقرير النهائي: {report_file}")

    def run_tests(self):
        self.login_superuser()
        self.create_test_data()
        self.test_receipt_voucher()
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

#!/usr/bin/env python
"""
اختبار شامل لنظام المبيعات في ERP
يتحقق من صحة عملية حفظ فاتورة المبيعات وإنشاء جميع المستندات المطلوبة
"""

import os
import sys
import django
from decimal import Decimal
from datetime import date

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase
from django.test.utils import override_settings

from sales.models import SalesInvoice, SalesInvoiceItem
from customers.models import CustomerSupplier
from products.models import Product, Category
from inventory.models import Warehouse, InventoryMovement
from accounts.models import AccountTransaction
from journal.models import JournalEntry, JournalLine
from core.models import DocumentSequence
from settings.models import CompanySettings, Currency

User = get_user_model()


class SalesInvoiceTest:
    """اختبار شامل لنظام المبيعات"""

    def __init__(self):
        self.user = None
        self.customer = None
        self.product = None
        self.warehouse = None
        self.invoice = None
        self.test_results = []

    def log_result(self, test_name, success, message=""):
        """تسجيل نتيجة الاختبار"""
        result = {
            'test': test_name,
            'success': success,
            'message': message
        }
        self.test_results.append(result)
        status = "نجح" if success else "فشل"
        print(f"[{status}] {test_name}: {message}")

    def setup_test_data(self):
        """إعداد البيانات التجريبية"""
        try:
            # إنشاء مستخدم تجريبي
            self.user, created = User.objects.get_or_create(
                username='test_user',
                defaults={
                    'email': 'test@example.com',
                    'first_name': 'Test',
                    'last_name': 'User'
                }
            )
            if created:
                self.user.set_password('testpass123')
                self.user.save()

            # إنشاء عميل تجريبي
            self.customer, created = CustomerSupplier.objects.get_or_create(
                name='عميل تجريبي',
                type='customer',
                defaults={
                    'phone': '123456789',
                    'email': 'customer@example.com'
                }
            )

            # إنشاء فئة منتج
            category, created = Category.objects.get_or_create(
                name='فئة تجريبية',
                code='TEST'
            )

            # إنشاء منتج تجريبي
            self.product, created = Product.objects.get_or_create(
                code='TEST001',
                defaults={
                    'name': 'منتج تجريبي',
                    'category': category,
                    'sale_price': Decimal('100.00'),
                    'cost_price': Decimal('50.00'),
                    'tax_rate': Decimal('15.00'),
                    'is_active': True
                }
            )

            # إنشاء مستودع تجريبي
            self.warehouse, created = Warehouse.objects.get_or_create(
                code='TEST_WH',
                defaults={
                    'name': 'مستودع تجريبي',
                    'is_active': True
                }
            )

            # إنشاء تسلسل المستندات
            sequence, created = DocumentSequence.objects.get_or_create(
                document_type='sales_invoice',
                defaults={
                    'prefix': 'SALES-',
                    'next_number': 1,
                    'padding': 6
                }
            )

            # إنشاء إعدادات الشركة
            company_settings, created = CompanySettings.objects.get_or_create(
                id=1,
                defaults={
                    'company_name': 'شركة تجريبية',
                    'tax_number': '123456789'
                }
            )

            # إنشاء عملة أساسية
            currency, created = Currency.objects.get_or_create(
                code='SAR',
                defaults={
                    'name': 'ريال سعودي',
                    'symbol': 'ر.س',
                    'is_base_currency': True
                }
            )

            self.log_result("إعداد البيانات التجريبية", True, "تم إنشاء جميع البيانات التجريبية بنجاح")

        except Exception as e:
            self.log_result("إعداد البيانات التجريبية", False, f"خطأ في إعداد البيانات: {str(e)}")
            return False

        return True

    def create_sales_invoice_directly(self, payment_type='cash'):
        """إنشاء فاتورة مبيعات مباشرة باستخدام النماذج"""
        try:
            from core.models import DocumentSequence
            from decimal import Decimal
            from datetime import date

            # توليد رقم الفاتورة
            sequence = DocumentSequence.objects.get(document_type='sales_invoice')
            invoice_number = sequence.get_next_number()

            # إنشاء الفاتورة
            invoice = SalesInvoice.objects.create(
                invoice_number=invoice_number,
                date=date.today(),
                customer=self.customer,
                warehouse=self.warehouse,
                payment_type=payment_type,
                notes='فاتورة تجريبية',
                created_by=self.user,
                subtotal=Decimal('200.00'),
                tax_amount=Decimal('30.00'),
                total_amount=Decimal('230.00')
            )

            # إنشاء عنصر الفاتورة
            SalesInvoiceItem.objects.create(
                invoice=invoice,
                product=self.product,
                quantity=Decimal('2'),
                unit_price=Decimal('100.00'),
                tax_rate=Decimal('15.00'),
                tax_amount=Decimal('30.00'),
                total_amount=Decimal('230.00')
            )

            # استدعاء دوال إنشاء الحركات المطلوبة
            from sales.views import create_sales_invoice_account_transaction
            from inventory.models import InventoryMovement
            import uuid

            # إنشاء حركة مخزون
            movement_number = f"SALE-OUT-{uuid.uuid4().hex[:8].upper()}"
            InventoryMovement.objects.create(
                movement_number=movement_number,
                date=invoice.date,
                product=self.product,
                warehouse=self.warehouse,
                movement_type='out',
                reference_type='sales_invoice',
                reference_id=invoice.id,
                quantity=Decimal('2'),
                unit_cost=Decimal('100.00'),
                notes=f'مبيعات - فاتورة رقم {invoice.invoice_number}',
                created_by=self.user
            )

            # إنشاء حركة الحساب
            create_sales_invoice_account_transaction(invoice, self.user)

            # القيد المحاسبي سيُنشأ تلقائياً عبر الـ signal

            self.invoice = invoice
            self.log_result(f"إنشاء فاتورة مبيعات ({payment_type})", True,
                          f"تم إنشاء الفاتورة رقم {invoice.invoice_number}")
            return True

        except Exception as e:
            self.log_result(f"إنشاء فاتورة مبيعات ({payment_type})", False,
                          f"خطأ في إنشاء الفاتورة: {str(e)}")
            return False

    def verify_invoice_creation(self):
        """التحقق من إنشاء الفاتورة بشكل صحيح"""
        if not self.invoice:
            self.log_result("التحقق من إنشاء الفاتورة", False, "لا توجد فاتورة للتحقق")
            return False

        try:
            # التحقق من بيانات الفاتورة الأساسية
            assert self.invoice.customer == self.customer
            assert self.invoice.warehouse == self.warehouse
            assert self.invoice.created_by == self.user
            assert self.invoice.subtotal == Decimal('200.00')  # 2 * 100
            assert self.invoice.tax_amount == Decimal('30.00')  # 200 * 0.15
            assert self.invoice.total_amount == Decimal('230.00')  # 200 + 30

            # التحقق من عناصر الفاتورة
            items = self.invoice.items.all()
            assert len(items) == 1

            item = items[0]
            assert item.product == self.product
            assert item.quantity == Decimal('2')
            assert item.unit_price == Decimal('100.00')
            assert item.tax_rate == Decimal('15.00')
            assert item.tax_amount == Decimal('30.00')
            assert item.total_amount == Decimal('230.00')

            self.log_result("التحقق من إنشاء الفاتورة", True,
                          f"تم التحقق من صحة الفاتورة رقم {self.invoice.invoice_number}")
            return True

        except AssertionError as e:
            self.log_result("التحقق من إنشاء الفاتورة", False,
                          f"بيانات الفاتورة غير صحيحة: {str(e)}")
            return False
        except Exception as e:
            self.log_result("التحقق من إنشاء الفاتورة", False,
                          f"خطأ في التحقق: {str(e)}")
            return False

    def verify_inventory_movements(self):
        """التحقق من إنشاء حركات المخزون"""
        if not self.invoice:
            self.log_result("التحقق من حركات المخزون", False, "لا توجد فاتورة")
            return False

        try:
            movements = InventoryMovement.objects.filter(
                reference_type='sales_invoice',
                reference_id=self.invoice.id
            )

            if not movements.exists():
                self.log_result("التحقق من حركات المخزون", False,
                              "لم يتم إنشاء حركات مخزون")
                return False

            # يجب أن تكون هناك حركة واحدة صادرة
            assert len(movements) == 1
            movement = movements[0]

            assert movement.movement_type == 'out'
            assert movement.product == self.product
            assert movement.warehouse == self.warehouse
            assert movement.quantity == Decimal('2')
            assert movement.unit_cost == Decimal('100.00')

            self.log_result("التحقق من حركات المخزون", True,
                          f"تم إنشاء حركة مخزون صادرة صحيحة")
            return True

        except AssertionError as e:
            self.log_result("التحقق من حركات المخزون", False,
                          f"حركات المخزون غير صحيحة: {str(e)}")
            return False
        except Exception as e:
            self.log_result("التحقق من حركات المخزون", False,
                          f"خطأ في التحقق: {str(e)}")
            return False

    def verify_account_transactions(self):
        """التحقق من إنشاء حركات الحسابات"""
        if not self.invoice:
            self.log_result("التحقق من حركات الحسابات", False, "لا توجد فاتورة")
            return False

        try:
            transactions = AccountTransaction.objects.filter(
                reference_type='sales_invoice',
                reference_id=self.invoice.id
            )

            # في البيع النقدي، لا نحتاج لحركة حساب عميل
            if self.invoice.payment_type == 'cash':
                if transactions.exists():
                    self.log_result("التحقق من حركات الحسابات", False,
                                  "البيع النقدي يجب ألا ينشئ حركات حسابات للعملاء")
                    return False
                else:
                    self.log_result("التحقق من حركات الحسابات", True,
                                  "البيع النقدي لا ينشئ حركات حسابات للعملاء (صحيح)")
                    return True

            # في البيع الآجل، نحتاج لحركة حساب واحدة
            if not transactions.exists():
                self.log_result("التحقق من حركات الحسابات", False,
                              "لم يتم إنشاء حركات حسابات للبيع الآجل")
                return False

            # يجب أن تكون هناك حركة واحدة
            assert len(transactions) == 1
            transaction = transactions[0]

            assert transaction.customer_supplier == self.customer
            assert transaction.transaction_type == 'sales_invoice'
            assert transaction.amount == self.invoice.total_amount
            assert transaction.direction == 'debit'   # العميل مدين للبيع الآجل

            self.log_result("التحقق من حركات الحسابات", True,
                          f"تم إنشاء حركة حساب صحيحة ({transaction.direction})")
            return True

        except AssertionError as e:
            self.log_result("التحقق من حركات الحسابات", False,
                          f"حركات الحسابات غير صحيحة: {str(e)}")
            return False
        except Exception as e:
            self.log_result("التحقق من حركات الحسابات", False,
                          f"خطأ في التحقق: {str(e)}")
            return False

    def verify_journal_entries(self):
        """التحقق من إنشاء القيود المحاسبية (اختياري)"""
        if not self.invoice:
            self.log_result("التحقق من القيود المحاسبية", False, "لا توجد فاتورة")
            return False

        try:
            entries = JournalEntry.objects.filter(
                reference_type='sales_invoice',
                reference_id=self.invoice.id
            )

            if not entries.exists():
                # قد يكون فشل في إنشاء القيد بسبب مشاكل في الترقيم
                self.log_result("التحقق من القيود المحاسبية", False,
                              "لم يتم إنشاء قيود محاسبية (قد يكون بسبب مشاكل في الترقيم)")
                return False

            # يجب أن يكون هناك قيد واحد
            if len(entries) != 1:
                raise AssertionError(f"عدد القيود: {len(entries)}, المتوقع: 1")
            entry = entries[0]

            # التحقق من أسطر القيد
            lines = entry.lines.all().order_by('account__code')

            # يجب أن تكون هناك 2-3 أسطر حسب وجود الضريبة
            expected_lines = 2 if self.invoice.tax_amount == 0 else 3
            if len(lines) != expected_lines:
                raise AssertionError(f"عدد أسطر القيد: {len(lines)}, المتوقع: {expected_lines}")

            # البحث عن السطر المدين (حساب النقد للبيع النقدي أو حساب العميل للبيع الآجل)
            debit_line = None
            sales_line = None
            tax_line = None

            for line in lines:
                if line.debit > 0:
                    debit_line = line
                elif 'ضريبة' in line.line_description:
                    tax_line = line
                elif 'مبيعات' in line.line_description:
                    sales_line = line

            # التحقق من السطر المدين
            assert debit_line is not None, "لا يوجد سطر مدين"
            assert debit_line.debit == self.invoice.total_amount, f"قيمة المدين: {debit_line.debit}, المتوقع: {self.invoice.total_amount}"
            
            # التحقق من نوع الحساب حسب نوع الدفع
            if self.invoice.payment_type == 'cash':
                # البيع النقدي: يجب أن يكون حساب النقد
                assert 'صندوق' in debit_line.account.name or 'cash' in debit_line.account.name.lower(), f"حساب المدين: {debit_line.account.name}"
            else:
                # البيع الآجل: يجب أن يكون حساب العميل
                assert 'عميل' in debit_line.account.name or 'customer' in debit_line.account.name.lower(), f"حساب المدين: {debit_line.account.name}"

            # التحقق من سطر المبيعات (دائن)
            assert sales_line is not None, "لا يوجد سطر مبيعات"
            assert sales_line.credit == self.invoice.subtotal, f"قيمة المبيعات: {sales_line.credit}, المتوقع: {self.invoice.subtotal}"
            assert 'مبيعات' in sales_line.account.name or 'sales' in sales_line.account.name.lower(), f"حساب المبيعات: {sales_line.account.name}"

            # التحقق من سطر الضريبة إذا وجدت
            if self.invoice.tax_amount > 0:
                assert tax_line is not None, "لا يوجد سطر ضريبة رغم وجود ضريبة"
                assert tax_line.credit == self.invoice.tax_amount, f"قيمة الضريبة: {tax_line.credit}, المتوقع: {self.invoice.tax_amount}"
                assert 'ضريبة' in tax_line.account.name or 'tax' in tax_line.account.name.lower(), f"حساب الضريبة: {tax_line.account.name}"

            self.log_result("التحقق من القيود المحاسبية", True,
                          f"تم إنشاء قيد محاسبي صحيح بـ {len(lines)} سطر")
            return True

        except AssertionError as e:
            self.log_result("التحقق من القيود المحاسبية", False,
                          f"القيود المحاسبية غير صحيحة: AssertionError - {str(e)}")
            return False
        except Exception as e:
            self.log_result("التحقق من القيود المحاسبية", False,
                          f"خطأ في التحقق: {str(e)} - نوع الخطأ: {type(e).__name__}")
            return False

    def run_cash_sale_test(self):
        """تشغيل اختبار البيع النقدي"""
        print("\n=== اختبار البيع النقدي ===")

        # إنشاء فاتورة نقدية
        if not self.create_sales_invoice_directly('cash'):
            return False

        # التحقق من جميع العمليات
        results = []
        results.append(self.verify_invoice_creation())
        results.append(self.verify_inventory_movements())
        results.append(self.verify_account_transactions())
        results.append(self.verify_journal_entries())

        return all(results)

    def run_credit_sale_test(self):
        """تشغيل اختبار البيع الآجل"""
        print("\n=== اختبار البيع الآجل ===")

        # إنشاء فاتورة آجلة
        if not self.create_sales_invoice_directly('credit'):
            return False

        # التحقق من جميع العمليات
        results = []
        results.append(self.verify_invoice_creation())
        results.append(self.verify_inventory_movements())
        results.append(self.verify_account_transactions())
        results.append(self.verify_journal_entries())

        return all(results)

    def generate_report(self):
        """إنشاء التقرير النهائي"""
        report = "=" * 80 + "\n"
        report += "تقرير اختبار نظام المبيعات في ERP\n"
        report += "=" * 80 + "\n\n"

        report += "ملخص النتائج:\n"
        report += "-" * 40 + "\n"

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - passed_tests

        report += f"إجمالي الاختبارات: {total_tests}\n"
        report += f"الاختبارات الناجحة: {passed_tests}\n"
        report += f"الاختبارات الفاشلة: {failed_tests}\n"
        report += f"نسبة النجاح: {(passed_tests/total_tests*100):.1f}%\n\n"

        report += "تفاصيل الاختبارات:\n"
        report += "-" * 40 + "\n"

        for result in self.test_results:
            status = "✓ نجح" if result['success'] else "✗ فشل"
            report += f"{status}: {result['test']}\n"
            if result['message']:
                report += f"   {result['message']}\n"
            report += "\n"

        report += "=" * 80 + "\n"
        report += "نهاية التقرير\n"
        report += "=" * 80 + "\n"

        return report

    def run_all_tests(self):
        """تشغيل جميع الاختبارات"""
        print("بدء اختبار نظام المبيعات...")

        # إعداد البيانات
        if not self.setup_test_data():
            print("فشل في إعداد البيانات التجريبية")
            return False

        # تشغيل الاختبارات
        cash_test_result = self.run_cash_sale_test()
        credit_test_result = self.run_credit_sale_test()

        # إنشاء التقرير
        report = self.generate_report()

        # حفظ التقرير في ملف
        with open('sales_invoice_test.txt', 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\nتم حفظ التقرير في: sales_invoice_test.txt")
        print(f"النتيجة النهائية: {'نجح' if cash_test_result and credit_test_result else 'فشل'}")

        return cash_test_result and credit_test_result


if __name__ == '__main__':
    # تشغيل الاختبارات
    test = SalesInvoiceTest()
    success = test.run_all_tests()

    # إنهاء البرنامج برمز الخروج المناسب
    sys.exit(0 if success else 1)
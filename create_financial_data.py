#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
إنشاء بيانات معاملات مالية شاملة للفترة من 1/1/2025 إلى 30/9/2025
"""

import os
import sys
import django
import random
from decimal import Decimal
from datetime import date, datetime, timedelta
import uuid

# إعداد Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.db import transaction
from sales.models import SalesInvoice, SalesInvoiceItem
from purchases.models import PurchaseInvoice, PurchaseInvoiceItem
from receipts.models import PaymentReceipt
from payments.models import PaymentVoucher
from customers.models import CustomerSupplier
from products.models import Product, Category
from users.models import User
from cashboxes.models import Cashbox
from banks.models import BankAccount
from inventory.models import Warehouse
from journal.models import JournalEntry, JournalLine
from core.models import DocumentSequence

def create_products():
    """إنشاء منتجات للتجربة"""
    print("إنشاء المنتجات...")

    # إنشاء فئات
    categories_data = [
        {'name': 'لابتوبات', 'name_en': 'Laptops'},
        {'name': 'مكونات حاسوب', 'name_en': 'Computer Components'},
        {'name': 'إكسسوارات', 'name_en': 'Accessories'},
        {'name': 'خدمات صيانة', 'name_en': 'Maintenance Services'},
    ]

    categories = []
    for cat_data in categories_data:
        cat, created = Category.objects.get_or_create(
            name=cat_data['name'],
            defaults={'name_en': cat_data['name_en']}
        )
        categories.append(cat)

    # منتجات اللابتوبات
    laptops = [
        {'code': 'LT001', 'name': 'لابتوب Dell Inspiron 15', 'cost': 2500, 'sale': 3200},
        {'code': 'LT002', 'name': 'لابتوب HP Pavilion 14', 'cost': 2800, 'sale': 3600},
        {'code': 'LT003', 'name': 'لابتوب Lenovo ThinkPad', 'cost': 3500, 'sale': 4500},
        {'code': 'LT004', 'name': 'لابتوب Asus VivoBook', 'cost': 2200, 'sale': 2800},
        {'code': 'LT005', 'name': 'لابتوب Acer Aspire 5', 'cost': 2000, 'sale': 2600},
    ]

    # مكونات الحاسوب
    components = [
        {'code': 'CPU001', 'name': 'معالج Intel Core i5', 'cost': 800, 'sale': 1000},
        {'code': 'CPU002', 'name': 'معالج Intel Core i7', 'cost': 1200, 'sale': 1500},
        {'code': 'RAM001', 'name': 'ذاكرة RAM 8GB DDR4', 'cost': 200, 'sale': 280},
        {'code': 'RAM002', 'name': 'ذاكرة RAM 16GB DDR4', 'cost': 350, 'sale': 450},
        {'code': 'SSD001', 'name': 'قرص SSD 256GB', 'cost': 180, 'sale': 250},
        {'code': 'SSD002', 'name': 'قرص SSD 512GB', 'cost': 300, 'sale': 400},
        {'code': 'MB001', 'name': 'لوحة أم ASUS Prime', 'cost': 250, 'sale': 350},
    ]

    # الإكسسوارات
    accessories = [
        {'code': 'ACC001', 'name': 'ماوس لاسلكي Logitech', 'cost': 25, 'sale': 45},
        {'code': 'ACC002', 'name': 'لوحة مفاتيح ميكانيكية', 'cost': 80, 'sale': 120},
        {'code': 'ACC003', 'name': 'شاشة عرض 24 بوصة', 'cost': 180, 'sale': 250},
        {'code': 'ACC004', 'name': 'سماعات gaming', 'cost': 60, 'sale': 90},
        {'code': 'ACC005', 'name': 'حقيبة لابتوب', 'cost': 30, 'sale': 50},
    ]

    # خدمات الصيانة
    services = [
        {'code': 'SVC001', 'name': 'صيانة شاملة للابتوب', 'cost': 50, 'sale': 100},
        {'code': 'SVC002', 'name': 'تنظيف وصيانة داخلية', 'cost': 30, 'sale': 60},
        {'code': 'SVC003', 'name': 'إصلاح شاشة لابتوب', 'cost': 80, 'sale': 150},
        {'code': 'SVC004', 'name': 'تركيب ذاكرة RAM', 'cost': 20, 'sale': 40},
        {'code': 'SVC005', 'name': 'استبدال قرص صلب', 'cost': 60, 'sale': 120},
    ]

    products_data = [
        (laptops, categories[0]),  # لابتوبات
        (components, categories[1]),  # مكونات
        (accessories, categories[2]),  # إكسسوارات
        (services, categories[3]),  # خدمات
    ]

    created_products = []
    for products_list, category in products_data:
        for product_data in products_list:
            product, created = Product.objects.get_or_create(
                code=product_data['code'],
                defaults={
                    'name': product_data['name'],
                    'category': category,
                    'cost_price': Decimal(str(product_data['cost'])),
                    'sale_price': Decimal(str(product_data['sale'])),
                    'tax_rate': Decimal('16.00'),  # ضريبة 16%
                    'product_type': 'service' if 'SVC' in product_data['code'] else 'physical',
                    'is_active': True,
                }
            )
            created_products.append(product)

    print(f"✅ تم إنشاء {len(created_products)} منتج")
    return created_products

def get_random_date(start_date, end_date):
    """إنشاء تاريخ عشوائي بين تاريخين"""
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)

def create_purchase_invoices(products, suppliers, users):
    """إنشاء فواتير المشتريات"""
    print("إنشاء فواتير المشتريات...")

    warehouse = Warehouse.objects.filter(is_active=True).first()
    if not warehouse:
        warehouse = Warehouse.objects.create(
            name='المستودع الرئيسي',
            code='MAIN',
            is_active=True
        )

    created_invoices = []
    start_date = date(2025, 1, 1)
    end_date = date(2025, 9, 30)

    for i in range(50):
        # اختيار مورد عشوائي
        supplier = random.choice(suppliers)

        # اختيار مستخدم عشوائي
        user = random.choice(users)

        # تاريخ عشوائي
        invoice_date = get_random_date(start_date, end_date)

        # إنشاء رقم الفاتورة
        try:
            sequence = DocumentSequence.objects.get(document_type='purchase_invoice')
            invoice_number = sequence.get_next_number()
        except:
            invoice_number = f"PI{1000 + i:06d}"

        # اختيار منتجات عشوائية (3-8 أصناف)
        num_items = random.randint(3, 8)
        selected_products = random.sample(products, min(num_items, len(products)))

        # إنشاء الفاتورة
        invoice = PurchaseInvoice.objects.create(
            invoice_number=invoice_number,
            date=invoice_date,
            supplier=supplier,
            warehouse=warehouse,
            payment_type=random.choice(['cash', 'credit']),
            notes=f'فاتورة مشتريات رقم {invoice_number}',
            created_by=user,
            is_tax_inclusive=True,
        )

        subtotal = Decimal('0')
        total_tax = Decimal('0')

        # إضافة الأصناف
        for product in selected_products:
            quantity = random.randint(1, 10)
            unit_price = product.cost_price
            tax_rate = product.tax_rate

            line_subtotal = quantity * unit_price
            line_tax = line_subtotal * (tax_rate / 100)

            PurchaseInvoiceItem.objects.create(
                invoice=invoice,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                tax_rate=tax_rate,
                tax_amount=line_tax,
                total_amount=line_subtotal + line_tax
            )

            subtotal += line_subtotal
            total_tax += line_tax

        # تحديث إجماليات الفاتورة
        invoice.subtotal = subtotal
        invoice.tax_amount = total_tax
        invoice.total_amount = subtotal + total_tax
        invoice.save()

        created_invoices.append(invoice)

    print(f"✅ تم إنشاء {len(created_invoices)} فاتورة مشتريات")
    return created_invoices

def create_sales_invoices(products, customers, users, cashboxes):
    """إنشاء فواتير المبيعات"""
    print("إنشاء فواتير المبيعات...")

    warehouse = Warehouse.objects.filter(is_active=True).first()
    created_invoices = []
    start_date = date(2025, 1, 1)
    end_date = date(2025, 9, 30)

    for i in range(200):
        # اختيار عميل عشوائي
        customer = random.choice(customers)

        # اختيار مستخدم عشوائي (يفضل موظفي المبيعات)
        sales_users = [u for u in users if 'sales' in u.username or 'admin' in u.username]
        if sales_users:
            user = random.choice(sales_users)
        else:
            user = random.choice(users)

        # تاريخ عشوائي
        invoice_date = get_random_date(start_date, end_date)

        # إنشاء رقم الفاتورة
        try:
            sequence = DocumentSequence.objects.get(document_type='sales_invoice')
            invoice_number = sequence.get_next_number()
        except:
            invoice_number = f"SI{1000 + i:06d}"

        # اختيار منتجات عشوائية (2-6 أصناف)
        num_items = random.randint(2, 6)
        selected_products = random.sample(products, min(num_items, len(products)))

        # تحديد نوع الدفع
        payment_type = random.choice(['cash', 'credit'])

        # تحديد الصندوق إذا كان الدفع نقدي
        cashbox = None
        if payment_type == 'cash':
            if user.has_perm('users.can_access_pos'):
                # إنشاء صندوق خاص بالمستخدم إذا لم يكن موجوداً
                cashbox, created = Cashbox.objects.get_or_create(
                    responsible_user=user,
                    defaults={
                        'name': f'صندوق {user.username}',
                        'balance': Decimal('0'),
                        'currency_id': 1,
                        'is_active': True
                    }
                )
            else:
                cashbox = random.choice(cashboxes) if cashboxes else None

        # تحديد ما إذا كانت شاملة الضريبة
        inclusive_tax = random.choice([True, False])

        # إنشاء الفاتورة
        invoice = SalesInvoice.objects.create(
            invoice_number=invoice_number,
            date=invoice_date,
            customer=customer,
            warehouse=warehouse,
            payment_type=payment_type,
            cashbox=cashbox,
            notes=f'فاتورة مبيعات رقم {invoice_number}',
            created_by=user,
            inclusive_tax=inclusive_tax,
        )

        subtotal = Decimal('0')
        total_tax = Decimal('0')

        # إضافة الأصناف
        for product in selected_products:
            quantity = random.randint(1, 5)
            unit_price = product.sale_price
            tax_rate = product.tax_rate

            line_subtotal = quantity * unit_price
            line_tax = line_subtotal * (tax_rate / 100)

            SalesInvoiceItem.objects.create(
                invoice=invoice,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                tax_rate=tax_rate,
                tax_amount=line_tax,
                total_amount=line_subtotal + line_tax
            )

            subtotal += line_subtotal
            total_tax += line_tax

        # تحديث إجماليات الفاتورة
        invoice.subtotal = subtotal
        if inclusive_tax:
            invoice.tax_amount = total_tax
            invoice.total_amount = subtotal + total_tax
        else:
            invoice.tax_amount = Decimal('0')
            invoice.total_amount = subtotal
        invoice.save()

        created_invoices.append(invoice)

    print(f"✅ تم إنشاء {len(created_invoices)} فاتورة مبيعات")
    return created_invoices

def create_receipts(sales_invoices, cashboxes, bank_accounts, users):
    """إنشاء سندات القبض"""
    print("إنشاء سندات القبض...")

    created_receipts = []
    # اختيار فواتير عشوائية للقبض (حوالي 60% من الفواتير)
    num_receipts = 60
    selected_invoices = random.sample(sales_invoices, min(num_receipts, len(sales_invoices)))

    for i, invoice in enumerate(selected_invoices):
        # تاريخ القبض (بعد تاريخ الفاتورة بأيام قليلة)
        receipt_date = invoice.date + timedelta(days=random.randint(1, 30))

        # إنشاء رقم السند
        try:
            sequence = DocumentSequence.objects.get(document_type='payment_receipt')
            receipt_number = sequence.get_next_number()
        except:
            receipt_number = f"PR{1000 + i:06d}"

        # تحديد طريقة القبض
        payment_type = random.choice(['cash', 'check'])

        # تحديد الصندوق أو الحساب البنكي
        cashbox = None
        bank_account = None
        check_number = None
        check_date = None

        if payment_type == 'cash':
            cashbox = random.choice(cashboxes) if cashboxes else None
        else:
            bank_account = random.choice(bank_accounts) if bank_accounts else None
            check_number = f"CHK{random.randint(10000, 99999)}"
            check_date = receipt_date

        # اختيار مستخدم
        user = random.choice(users)

        # إنشاء سند القبض
        receipt = PaymentReceipt.objects.create(
            receipt_number=receipt_number,
            date=receipt_date,
            customer=invoice.customer,
            payment_type=payment_type,
            amount=invoice.total_amount,
            cashbox=cashbox,
            check_number=check_number,
            check_date=check_date,
            bank_name=bank_account.name if bank_account else None,
            check_cashbox=bank_account,  # استخدام الحساب البنكي كـ check_cashbox
            created_by=user
        )

        created_receipts.append(receipt)

    print(f"✅ تم إنشاء {len(created_receipts)} سند قبض")
    return created_receipts

def create_payments(purchase_invoices, cashboxes, bank_accounts, users):
    """إنشاء سندات الصرف"""
    print("إنشاء سندات الصرف...")

    created_vouchers = []

    # دفع المشتريات (حوالي 70% من فواتير المشتريات)
    purchase_payments = 28  # 70% من 40
    selected_purchases = random.sample(purchase_invoices, min(purchase_payments, len(purchase_invoices)))

    # مصاريف تشغيلية (الباقي)
    operational_expenses = 40 - purchase_payments

    # دفع المشتريات
    for i, invoice in enumerate(selected_purchases):
        # تاريخ الصرف (بعد تاريخ الفاتورة بأيام قليلة)
        payment_date = invoice.date + timedelta(days=random.randint(1, 30))

        # إنشاء رقم السند
        try:
            sequence = DocumentSequence.objects.get(document_type='payment_voucher')
            voucher_number = sequence.get_next_number()
        except:
            voucher_number = f"PV{1000 + i:06d}"

        # تحديد طريقة الصرف
        payment_type = random.choice(['cash', 'bank_transfer'])

        # تحديد الصندوق أو الحساب البنكي
        cashbox = None
        bank_account = None

        if payment_type == 'cash':
            cashbox = random.choice(cashboxes) if cashboxes else None
        else:
            bank_account = random.choice(bank_accounts) if bank_accounts else None

        # اختيار مستخدم
        user = random.choice(users)

        # إنشاء سند الصرف
        voucher = PaymentVoucher.objects.create(
            voucher_number=voucher_number,
            date=payment_date,
            supplier=invoice.supplier,
            payment_type=payment_type,
            amount=invoice.total_amount,
            cashbox=cashbox,
            bank_account=bank_account,
            description=f'دفع فاتورة مشتريات رقم {invoice.invoice_number}',
            created_by=user
        )

        created_vouchers.append(voucher)

    # مصاريف تشغيلية
    expense_types = [
        'إيجار المكتب',
        'فاتورة كهرباء',
        'فاتورة إنترنت',
        'رواتب الموظفين',
        'مصاريف نقل',
        'مصاريف مكتبية',
    ]

    for i in range(operational_expenses):
        payment_date = get_random_date(date(2025, 1, 1), date(2025, 9, 30))

        try:
            sequence = DocumentSequence.objects.get(document_type='payment_voucher')
            voucher_number = sequence.get_next_number()
        except:
            voucher_number = f"PV{2000 + i:06d}"

        payment_type = random.choice(['cash', 'bank_transfer'])
        cashbox = None
        bank_account = None

        if payment_type == 'cash':
            cashbox = random.choice(cashboxes) if cashboxes else None
        else:
            bank_account = random.choice(bank_accounts) if bank_accounts else None

        user = random.choice(users)
        expense_type = random.choice(expense_types)
        amount = Decimal(str(random.randint(500, 5000)))

        voucher = PaymentVoucher.objects.create(
            voucher_number=voucher_number,
            date=payment_date,
            payment_type=payment_type,
            amount=amount,
            cashbox=cashbox,
            bank_account=bank_account,
            description=f'{expense_type} - شهر {payment_date.strftime("%B %Y")}',
            created_by=user
        )

        created_vouchers.append(voucher)

    print(f"✅ تم إنشاء {len(created_vouchers)} سند صرف")
    return created_vouchers

def create_additional_journal_entries(users):
    """إنشاء قيود محاسبية إضافية"""
    print("إنشاء قيود محاسبية إضافية...")

    created_entries = []

    # قيود شهرية للمصاريف
    monthly_expenses = [
        {'description': 'رواتب الموظفين', 'amount': 15000},
        {'description': 'إيجار المكتب', 'amount': 3000},
        {'description': 'فاتورة كهرباء', 'amount': 800},
        {'description': 'فاتورة إنترنت', 'amount': 400},
        {'description': 'مصاريف نقل', 'amount': 1200},
        {'description': 'مصاريف مكتبية', 'amount': 600},
    ]

    for month in range(1, 10):  # 9 أشهر
        for expense in monthly_expenses:
            entry_date = date(2025, month, 28)  # نهاية كل شهر

            try:
                sequence = DocumentSequence.objects.get(document_type='journal_entry')
                entry_number = sequence.get_next_number()
            except:
                entry_number = f"JE{1000 + len(created_entries):06d}"

            user = random.choice(users)

            # إنشاء القيد
            journal_entry = JournalEntry.objects.create(
                entry_number=entry_number,
                date=entry_date,
                description=f'{expense["description"]} - شهر {month}/2025',
                created_by=user
            )

            # خط إدخال (مدين) - حساب المصروف
            JournalLine.objects.create(
                journal_entry=journal_entry,
                account_id=5001,  # افتراضي - حساب مصاريف إدارية
                description=f'{expense["description"]}',
                debit=Decimal(str(expense['amount'])),
                credit=Decimal('0')
            )

            # خط إخراج (دائن) - حساب الصندوق أو البنك
            JournalLine.objects.create(
                journal_entry=journal_entry,
                account_id=1001,  # افتراضي - حساب نقدي
                description=f'دفع {expense["description"]}',
                debit=Decimal('0'),
                credit=Decimal(str(expense['amount']))
            )

            created_entries.append(journal_entry)

    # قيود إهلاك (إذا وجدت أصول)
    depreciation_entries = 5
    for i in range(depreciation_entries):
        entry_date = get_random_date(date(2025, 1, 1), date(2025, 9, 30))

        try:
            sequence = DocumentSequence.objects.get(document_type='journal_entry')
            entry_number = sequence.get_next_number()
        except:
            entry_number = f"JE{2000 + i:06d}"

        user = random.choice(users)
        depreciation_amount = Decimal(str(random.randint(500, 2000)))

        journal_entry = JournalEntry.objects.create(
            entry_number=entry_number,
            date=entry_date,
            description=f'قيد إهلاك شهري - أصول ثابتة',
            created_by=user
        )

        # إهلاك مكاسب (مدين)
        JournalLine.objects.create(
            journal_entry=journal_entry,
            account_id=6001,  # حساب إهلاك
            description='إهلاك الأصول الثابتة',
            debit=depreciation_amount,
            credit=Decimal('0')
        )

        # إهلاك مكاسب (دائن)
        JournalLine.objects.create(
            journal_entry=journal_entry,
            account_id=1501,  # حساب تراكمي إهلاك
            description='تراكمي إهلاك الأصول',
            debit=Decimal('0'),
            credit=depreciation_amount
        )

        created_entries.append(journal_entry)

    print(f"✅ تم إنشاء {len(created_entries)} قيد محاسبي إضافي")
    return created_entries

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء إنشاء بيانات المعاملات المالية...")

    try:
        with transaction.atomic():
            # إنشاء المنتجات
            products = create_products()

            # الحصول على البيانات المطلوبة
            customers = list(CustomerSupplier.objects.filter(type__in=['customer', 'both']))
            suppliers = list(CustomerSupplier.objects.filter(type__in=['supplier', 'both']))
            users = list(User.objects.all())
            cashboxes = list(Cashbox.objects.filter(is_active=True))
            bank_accounts = list(BankAccount.objects.filter(is_active=True))

            print(f"العملاء المتاحون: {len(customers)}")
            print(f"الموردون المتاحون: {len(suppliers)}")
            print(f"المستخدمون المتاحون: {len(users)}")
            print(f"الصناديق المتاحة: {len(cashboxes)}")
            print(f"الحسابات البنكية المتاحة: {len(bank_accounts)}")

            # إنشاء فواتير المشتريات
            purchase_invoices = create_purchase_invoices(products, suppliers, users)

            # إنشاء فواتير المبيعات
            sales_invoices = create_sales_invoices(products, customers, users, cashboxes)

            # إنشاء سندات القبض
            receipts = create_receipts(sales_invoices, cashboxes, bank_accounts, users)

            # إنشاء سندات الصرف
            payments = create_payments(purchase_invoices, cashboxes, bank_accounts, users)

            # إنشاء قيود إضافية
            additional_entries = create_additional_journal_entries(users)

            print("\n🎉 تم إنشاء جميع البيانات بنجاح!")
            print(f"📊 ملخص البيانات المُنشأة:")
            print(f"   • فواتير المشتريات: {len(purchase_invoices)}")
            print(f"   • فواتير المبيعات: {len(sales_invoices)}")
            print(f"   • سندات القبض: {len(receipts)}")
            print(f"   • سندات الصرف: {len(payments)}")
            print(f"   • قيود محاسبية إضافية: {len(additional_entries)}")

    except Exception as e:
        print(f"❌ خطأ في إنشاء البيانات: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
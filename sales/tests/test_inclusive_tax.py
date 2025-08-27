from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone

from products.models import Category, Product
from customers.models import CustomerSupplier
from sales.models import SalesInvoice

User = get_user_model()


class TestInclusiveTax(TestCase):
    def setUp(self):
        # create category and product
        self.cat = Category.objects.create(name='TEST-CAT', sequence_number=99999)
        self.prod = Product.objects.create(code='TST-1', name='T1', product_type='physical', category=self.cat, sale_price=Decimal('100.000'), tax_rate=Decimal('5.00'))
        # create customer
        self.cust = CustomerSupplier.objects.create(name='TEST-CUST', type='customer')

        # users
        self.normal = User.objects.create_user(username='normal', password='pass')
        self.super = User.objects.create_user(username='super', password='pass', is_superuser=True, is_staff=True)

        self.client = Client()
        # prevent writing real AuditLog entries during tests which may reference users across dbs
        try:
            from unittest.mock import patch
            patcher = patch('core.signals.log_user_activity')
            self.addCleanup(patcher.stop)
            self.mock_log = patcher.start()
        except Exception:
            self.mock_log = None

    def test_normal_user_invoice_inclusive_by_default(self):
        self.client.login(username='normal', password='pass')
        post_data = {
            'customer': str(self.cust.id),
            'payment_type': 'cash',
            'products[]': [str(self.prod.id)],
            'quantities[]': ['1'],
            'prices[]': [str(self.prod.sale_price)],
            'tax_rates[]': [str(self.prod.tax_rate)],
            'discount': '0',
            'notes': 'test_normal_inclusive',
        }
        resp = self.client.post('/ar/sales/invoices/add/', post_data, follow=True)
        self.assertIn(resp.status_code, (200, 302))

        inv = SalesInvoice.objects.filter(notes='test_normal_inclusive').first()
        self.assertIsNotNone(inv, 'Invoice should be created')
        # normal users cannot toggle => inclusive_tax True
        self.assertTrue(inv.inclusive_tax)
        # tax should be applied
        expected_tax = (self.prod.sale_price * (self.prod.tax_rate / Decimal('100'))).quantize(Decimal('0.001'))
        self.assertEqual(inv.tax_amount.quantize(Decimal('0.001')), expected_tax)

    def test_superuser_can_unset_inclusive_tax(self):
        self.client.login(username='super', password='pass')
        # For superuser, omitting the 'inclusive_tax' key will set it to False in current logic
        post_data = {
            'customer': str(self.cust.id),
            'payment_type': 'cash',
            'products[]': [str(self.prod.id)],
            'quantities[]': ['1'],
            'prices[]': [str(self.prod.sale_price)],
            'tax_rates[]': [str(self.prod.tax_rate)],
            'discount': '0',
            'notes': 'test_super_exclusive',
        }
        resp = self.client.post('/ar/sales/invoices/add/', post_data, follow=True)
        self.assertIn(resp.status_code, (200, 302))

        inv = SalesInvoice.objects.filter(notes='test_super_exclusive').first()
        self.assertIsNotNone(inv, 'Invoice should be created')
        # superuser omitted key => inclusive_tax False
        self.assertFalse(inv.inclusive_tax)
        # tax should be zero
        self.assertEqual(inv.tax_amount.quantize(Decimal('0.001')), Decimal('0').quantize(Decimal('0.001')))
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
from customers.models import CustomerSupplier
from products.models import Product, Category
from core.models import DocumentSequence
from sales.models import SalesInvoice
from unittest.mock import patch

User = get_user_model()


class InclusiveTaxTests(TestCase):
    def setUp(self):
        # patch audit logging to avoid creating AuditLog rows in tests
        self.patcher_log_activity = patch('core.signals.log_activity')
        self.patcher_log_user_activity = patch('core.signals.log_user_activity')
        self.mock_log_activity = self.patcher_log_activity.start()
        self.mock_log_user_activity = self.patcher_log_user_activity.start()

        # create users
        self.superuser = User.objects.create_superuser(username='super', email='s@example.com', password='pass')
        self.user = User.objects.create_user(username='normal', email='n@example.com', password='pass')

        # create customer
        self.customer = CustomerSupplier.objects.create(name='Cust1', type='customer', city='Amman')

        # create category and product
        self.category = Category.objects.create(name='Cat1', sequence_number=10000)
        self.product = Product.objects.create(code='P001', name='Product1', category=self.category, sale_price=Decimal('100'), tax_rate=Decimal('5'))

        # ensure document sequence exists
        DocumentSequence.objects.get_or_create(document_type='sales_invoice', defaults={'prefix':'SALES-','digits':6})

        self.client = Client()

    def tearDown(self):
        self.patcher_log_activity.stop()
        self.patcher_log_user_activity.stop()

    def _post_invoice(self, user, inclusive_tax_checkbox_present=True):
        self.client.force_login(user)
        url = reverse('sales:invoice_add')
        data = {
            'customer': str(self.customer.id),
            'payment_type': 'cash',
            'date': '2025-01-01',
            'products[]': [str(self.product.id)],
            'quantities[]': ['1'],
            'prices[]': ['100'],
            'tax_rates[]': ['5'],
            'discount': '0',
            'notes': 'test',
        }
        if inclusive_tax_checkbox_present:
            data['inclusive_tax'] = 'on'

        response = self.client.post(url, data, HTTP_HOST='127.0.0.1')
        return response

    def test_superuser_can_unset_inclusive_tax(self):
        # superuser POST without inclusive_tax -> should default to False when permitted
        resp = self._post_invoice(self.superuser, inclusive_tax_checkbox_present=False)
        # should redirect to detail
        self.assertEqual(resp.status_code, 302)
        inv = SalesInvoice.objects.order_by('-id').first()
        self.assertIsNotNone(inv)
        # superuser is allowed to toggle; since checkbox absent, inclusive_tax should be False
        self.assertFalse(inv.inclusive_tax)

        # log_user_activity should have been called for create and for inclusive_tax change
        calls = [c.args for c in self.mock_log_user_activity.call_args_list]
        self.assertTrue(any(len(c) >= 2 and c[1] == 'create' for c in calls))
        self.assertTrue(any(len(c) >= 2 and c[1] == 'update' for c in calls))

    def test_normal_user_cannot_unset_inclusive_tax(self):
        # normal user POST without inclusive_tax -> should remain True
        resp = self._post_invoice(self.user, inclusive_tax_checkbox_present=False)
        self.assertEqual(resp.status_code, 302)
        inv = SalesInvoice.objects.order_by('-id').first()
        self.assertIsNotNone(inv)
        self.assertTrue(inv.inclusive_tax)

        # normal user should have had create log, but no 'update' call for inclusive change
        calls = [c.args for c in self.mock_log_user_activity.call_args_list]
        self.assertTrue(any(len(c) >= 2 and c[1] == 'create' for c in calls))
        self.assertFalse(any(len(c) >= 2 and c[1] == 'update' for c in calls))

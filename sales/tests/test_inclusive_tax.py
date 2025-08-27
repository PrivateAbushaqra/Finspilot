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

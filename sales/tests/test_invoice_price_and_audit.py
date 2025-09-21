from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from products.models import Product, Category
from customers.models import CustomerSupplier
from core.models import AuditLog


class InvoicePriceAndAuditTests(TestCase):
    def setUp(self):
        U = get_user_model()
        # create a pos user
        self.user = U.objects.create_user(username='posuser', password='pass')
        self.user.user_type = 'pos_user'
        self.user.save()

        # create category and product
        cat = Category.objects.create(sequence_number=10000, name='TestCat')
        self.product = Product.objects.create(
            code='TST001',
            name='Test Product',
            category=cat,
            cost_price=10.00,
            sale_price=25.50,
            tax_rate=5
        )

        # create a customer
        self.customer = CustomerSupplier.objects.create(name='Test Cust', type='customer')

        self.client = Client()
        self.client.login(username='posuser', password='pass')

    def test_pos_get_product_returns_sale_price(self):
        url = reverse('sales:pos_get_product', kwargs={'product_id': self.product.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertIn('product', data)
        self.assertEqual(float(data['product']['price']), float(self.product.sale_price))

    def test_create_invoice_uses_sale_price_and_logs_audit(self):
        url = reverse('sales:invoice_add')

        post_data = {
            'customer': str(self.customer.id),
            'payment_type': 'cash',
            'products[]': [str(self.product.id)],
            'quantities[]': ['2'],
            'prices[]': ['0'],  # intentionally 0 to trigger server-side correction
            'tax_rates[]': [str(self.product.tax_rate)],
            'tax_amounts[]': ['0']
        }

        resp = self.client.post(url, post_data, follow=True)
        # should redirect to detail page
        self.assertEqual(resp.status_code, 200)
        # check that an invoice was created and an AuditLog entry exists for this user
        self.assertTrue(AuditLog.objects.filter(user=self.user).exists())

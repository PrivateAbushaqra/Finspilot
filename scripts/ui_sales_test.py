from django.test import Client
from django.contrib.auth import get_user_model
from products.models import Category, Product
from customers.models import CustomerSupplier
from cashboxes.models import Cashbox
from sales.models import SalesInvoice
from decimal import Decimal
from django.utils import timezone

User = get_user_model()


def ensure_objects():
    cat = Category.objects.first() or Category.objects.create(name='UI-CAT', sequence_number=10001)
    prod = Product.objects.filter(code='UI-P001').first()
    if not prod:
        prod = Product.objects.create(code='UI-P001', name='UI Product', product_type='physical', category=cat, sale_price=Decimal('50.000'), tax_rate=Decimal('10.00'))
    cust = CustomerSupplier.objects.filter(name='UI-CUST').first() or CustomerSupplier.objects.create(name='UI-CUST', type='customer')
    cb = Cashbox.objects.filter(name='UI-CASH').first() or Cashbox.objects.create(name='UI-CASH')
    return prod, cust, cb


def ensure_user(username='ui_super'):
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password('password')
        user.is_superuser = True
        user.is_staff = True
        user.save()
    return user


def ensure_normal_user(username='ui_user'):
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password('password')
        user.is_superuser = False
        user.is_staff = False
        user.save()
    return user


def run_ui_tests():
    prod, cust, cb = ensure_objects()
    super_user = ensure_user()
    normal_user = ensure_normal_user()

    client = Client()

    # Login as normal user and GET create page
    client.login(username=normal_user.username, password='password')
    res = client.get('/sales/invoices/add/', HTTP_HOST='127.0.0.1')
    print('Normal user GET add page status:', res.status_code)
    # normal user should see checkbox disabled
    if b'name="inclusive_tax"' in res.content and b'disabled' in res.content:
        print('Normal user: inclusive_tax checkbox present and disabled')
    else:
        print('Normal user: checkbox missing or not disabled')

    client.logout()

    # Login as super user and GET create page
    client.login(username=super_user.username, password='password')
    res = client.get('/sales/invoices/add/', HTTP_HOST='127.0.0.1')
    print('Super user GET add page status:', res.status_code)
    if b'name="inclusive_tax"' in res.content and b'disabled' not in res.content:
        print('Super user: inclusive_tax checkbox present and editable')
    else:
        print('Super user: checkbox missing or still disabled')

    # Try POST as normal user attempting to unset inclusive_tax
    client.logout()
    client.login(username=normal_user.username, password='password')
    post_data = {
        'customer': str(cust.id),
        'payment_type': 'cash',
        'products[]': [str(prod.id)],
        'quantities[]': ['1'],
        'prices[]': [str(prod.sale_price)],
        'tax_rates[]': [str(prod.tax_rate)],
        'discount': '0',
        'notes': 'UI test',
        # attempt to unset
        # do not include 'inclusive_tax' => should remain True
    }
    res = client.post('/sales/invoices/add/', post_data, follow=True, HTTP_HOST='127.0.0.1')
    print('Normal user POST create status:', res.status_code)
    created_invoice = SalesInvoice.objects.filter(notes='UI test').first()
    if created_invoice:
        print('Invoice created by normal user inclusive_tax=', created_invoice.inclusive_tax)
        created_invoice.delete()

    client.logout()

    # Try POST as super user unsetting inclusive_tax
    client.login(username=super_user.username, password='password')
    post_data['notes'] = 'UI test super'
    # include inclusive_tax unchecked by sending hidden 0 and no checkbox value
    post_data['inclusive_tax'] = '0'
    res = client.post('/sales/invoices/add/', post_data, follow=True, HTTP_HOST='127.0.0.1')
    print('Super user POST create status:', res.status_code)
    created_invoice = SalesInvoice.objects.filter(notes='UI test super').first()
    if created_invoice:
        print('Invoice created by super inclusive_tax=', created_invoice.inclusive_tax)
        created_invoice.delete()

    print('UI tests done.')

if __name__ == '__main__':
    run_ui_tests()

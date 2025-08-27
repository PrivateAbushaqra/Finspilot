from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from products.models import Category, Product
from customers.models import CustomerSupplier
from cashboxes.models import Cashbox
from sales.models import SalesInvoice, SalesInvoiceItem

User = get_user_model()


def ensure_category():
    # Prefer an existing test category, otherwise fall back to any existing category.
    cat = Category.objects.filter(name__icontains='TEST').first()
    if cat:
        return cat
    cat = Category.objects.first()
    if cat:
        return cat
    # As last resort create a category with an explicit sequence_number to avoid
    # invoking the sequence-finding logic that previously triggered an IntegrityError.
    return Category.objects.create(name='DEFAULT-CAT', sequence_number=10000)


def ensure_product():
    cat = ensure_category()
    prod, created = Product.objects.get_or_create(code='TEST-P001', defaults={
        'name': 'Test Product',
        'product_type': 'physical',
        'category': cat,
        'sale_price': Decimal('100.000'),
        'tax_rate': Decimal('5.00'),
    })
    return prod


def ensure_customer():
    cust, created = CustomerSupplier.objects.get_or_create(name='TEST-CUST', defaults={'type': 'customer'})
    return cust


def ensure_cashbox():
    cb, created = Cashbox.objects.get_or_create(name='TEST-CASHBOX')
    return cb


def ensure_user(username='testsuper'):
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.is_superuser = True
        user.set_password('testpassword')
        user.is_staff = True
        user.save()
    return user


def run_tests():
    print('Preparing test data...')
    user = ensure_user()
    prod = ensure_product()
    cust = ensure_customer()
    cb = ensure_cashbox()

    # Create invoice with inclusive_tax True (default)
    invoice1 = SalesInvoice.objects.create(
        invoice_number='TEST-INV-1',
        date=timezone.now().date(),
        customer=cust,
        payment_type='cash',
        cashbox=cb,
        subtotal=Decimal('100.000'),
        tax_amount=Decimal('5.000'),
        discount_amount=Decimal('0'),
        total_amount=Decimal('105.000'),
        inclusive_tax=True,
        created_by=user
    )
    item1 = SalesInvoiceItem.objects.create(
        invoice=invoice1,
        product=prod,
        quantity=Decimal('1'),
        unit_price=prod.sale_price,
        tax_rate=prod.tax_rate
    )
    print('Created invoice1:', invoice1.id, 'inclusive_tax=', invoice1.inclusive_tax, 'tax_amount=', invoice1.tax_amount, 'total=', invoice1.total_amount)

    # Create invoice with inclusive_tax False — emulate permission by using superuser
    invoice2 = SalesInvoice.objects.create(
        invoice_number='TEST-INV-2',
        date=timezone.now().date(),
        customer=cust,
        payment_type='cash',
        cashbox=cb,
        subtotal=Decimal('100.000'),
        tax_amount=Decimal('0'),
        discount_amount=Decimal('0'),
        total_amount=Decimal('100.000'),
        inclusive_tax=False,
        created_by=user
    )
    item2 = SalesInvoiceItem.objects.create(
        invoice=invoice2,
        product=prod,
        quantity=Decimal('1'),
        unit_price=prod.sale_price,
        tax_rate=prod.tax_rate
    )
    print('Created invoice2:', invoice2.id, 'inclusive_tax=', invoice2.inclusive_tax, 'tax_amount=', invoice2.tax_amount, 'total=', invoice2.total_amount)

    # Cleanup test data
    print('Cleaning up test data...')
    item1.delete()
    item2.delete()
    invoice1.delete()
    invoice2.delete()
    prod.delete()
    cust.delete()
    cb.delete()
    user.delete()
    print('Cleanup done.')


if __name__ == '__main__':
    run_tests()

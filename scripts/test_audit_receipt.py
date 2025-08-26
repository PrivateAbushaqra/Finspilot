from django.contrib.auth import get_user_model
from customers.models import CustomerSupplier
from cashboxes.models import Cashbox
from receipts.models import PaymentReceipt
from core.models import AuditLog
from django.utils import timezone
from datetime import date, timedelta

User = get_user_model()

u = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first()
if not u:
    print('NO_USER_FOUND')
    raise SystemExit(1)

print('Using user:', u.username)

# Create test customer
cust = CustomerSupplier.objects.create(name='TEST_CUSTOMER_AUTO', type='customer', city='City', email='test@example.com')
print('Created customer id=', cust.id)

# Create test cashbox
cb = Cashbox.objects.create(name='TEST_CASHBOX_AUTO')
print('Created cashbox id=', cb.id)

# Create a PaymentReceipt (check)
today = date.today()
rcp = PaymentReceipt(
    receipt_number='TESTRCP' + timezone.now().strftime('%Y%m%d%H%M%S'),
    date=today,
    customer=cust,
    payment_type='check',
    amount=100,
    check_number='CHK123',
    check_date=today,
    check_due_date=today + timedelta(days=30),
    bank_name='Test Bank',
    check_cashbox=cb,
    created_by=u
)
# Attach audit user so signals log with this user
rcp._audit_user = u
rcp.save()
print('Created receipt id=', rcp.id)

# Show AuditLog entries for this receipt
logs = AuditLog.objects.filter(content_type='PaymentReceipt', object_id=rcp.id).order_by('timestamp')
print('Audit logs for receipt count=', logs.count())
for l in logs:
    print(l.timestamp, l.action_type, l.description)

# Now delete the receipt (should create a delete log)
rcp._audit_user = u
rcp.delete()
print('Deleted receipt id=', rcp.id)

logs_after = AuditLog.objects.filter(content_type='PaymentReceipt', object_id=rcp.id).order_by('timestamp')
print('Audit logs for receipt after deletion count=', logs_after.count())
for l in logs_after:
    print(l.timestamp, l.action_type, l.description)

# Cleanup customer and cashbox
cust._audit_user = u
cust.delete()
print('Deleted customer id=', cust.id)
cb._audit_user = u
cb.delete()
print('Deleted cashbox id=', cb.id)

print('Cleanup done')

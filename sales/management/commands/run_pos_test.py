from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth import get_user_model
import json
from sales import views as sales_views
from sales.models import SalesInvoice
from core.models import AuditLog


class Command(BaseCommand):
    help = 'Run a POS create-invoice test using RequestFactory as pos user'

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username='pos')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('User "pos" does not exist.'))
            return

        rf = RequestFactory()

        test_items = [
            {
                'product_id': 1,
                'quantity': 1,
                'unit_price': 1.00,
                'total': 1.00,
                'tax_rate': 0,
                'tax_amount': 0
            }
        ]

        payload = {
            'items': test_items,
            'subtotal': 1.00,
            'tax_amount': 0,
            'discount_amount': 0,
            'total': 1.00
        }

        body = json.dumps(payload)

        request = rf.post('/sales/pos/create-invoice/', data=body, content_type='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = user

        self.stdout.write('Sending test request as user: %s' % user.username)

        response = sales_views.pos_create_invoice(request)

        try:
            content = response.content.decode('utf-8')
        except Exception:
            content = str(response)

        self.stdout.write('Response status: %s' % getattr(response, 'status_code', 'N/A'))
        self.stdout.write('Response content: %s' % content)

        # If created, show invoice summary
        try:
            last = SalesInvoice.objects.filter(created_by=user).order_by('-id').first()
            if last:
                self.stdout.write(self.style.SUCCESS('Found invoice id=%s number=%s total=%s' % (last.id, last.invoice_number, last.total_amount)))
            else:
                self.stdout.write(self.style.WARNING('No invoice found for user after test'))
        except Exception as e:
            self.stdout.write(self.style.ERROR('Error querying invoices: %s' % e))

        # AuditLog check
        try:
            al = AuditLog.objects.filter(user=user).order_by('-id').first()
            if al:
                self.stdout.write('Latest AuditLog: %s - %s' % (al.action_type, al.description))
            else:
                self.stdout.write('No AuditLog entries for user')
        except Exception as e:
            self.stdout.write('Error checking AuditLog: %s' % e)

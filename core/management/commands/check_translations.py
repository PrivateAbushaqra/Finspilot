from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import AuditLog
from django.test import Client


class Command(BaseCommand):
    help = 'Check Arabic translations appear for Credit/Debit Notes and log to AuditLog'

    def handle(self, *args, **options):
        U = get_user_model()
        user = U.objects.filter(is_superuser=True).first()
        if not user:
            self.stdout.write('no super user found')
            return
        AuditLog.objects.create(user=user, action_type='update', content_type='i18n.translations', description='تحديث ترجمات عربية: Credit Notes و Debit Notes')
        self.stdout.write(f'audit created for translations by {user.username}')

        c = Client()
        logged = c.login(username='super', password='password')
        self.stdout.write(f'client login: {logged}')
        resp = c.get('/ar/sales/credit-notes/')
        self.stdout.write(f'GET /ar/sales/credit-notes/ status: {resp.status_code}')
        cont = resp.content.decode('utf-8')
        self.stdout.write(f"has إشعارات دائن: {'إشعارات دائن' in cont}")
        self.stdout.write(f"has إشعارات مدين: {'إشعارات مدين' in cont}")
        if 'إشعارات دائن' in cont:
            i = cont.find('إشعارات دائن')
            self.stdout.write('snippet: ' + cont[max(0, i-80):i+80])

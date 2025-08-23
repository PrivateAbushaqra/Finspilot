from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.translation import activate
from decimal import Decimal
from .models import Account, JournalEntry, JournalLine


class JournalEntryCreateTests(TestCase):
    def setUp(self):
        # تفعيل اللغة العربية لتوليد المسار /ar/
        activate('ar')
        User = get_user_model()
        self.user = User.objects.create_user(
            username='tester', password='pass', is_superuser=True, is_staff=True
        )
        self.client.login(username='tester', password='pass')
        # إنشاء حسابين
        self.debit_acc = Account.objects.create(
            code='1000', name='الصندوق', account_type='asset', is_active=True
        )
        self.credit_acc = Account.objects.create(
            code='4000', name='إيرادات', account_type='revenue', is_active=True
        )

    def test_create_journal_entry_success(self):
        url = reverse('journal:entry_create')
        # بيانات النموذج الرئيسي
        data = {
            'entry_date': '2025-08-23',
            'reference_type': 'manual',
            'reference_id': '',
            'description': 'اختبار إنشاء قيد',
            # إدارة الفورمست
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '2',
            'form-MAX_NUM_FORMS': '1000',
            # السطر الأول (مدين)
            'form-0-account': str(self.debit_acc.id),
            'form-0-debit': '100.000',
            'form-0-credit': '0',
            'form-0-line_description': 'بند مدين',
            # السطر الثاني (دائن)
            'form-1-account': str(self.credit_acc.id),
            'form-1-debit': '0',
            'form-1-credit': '100.000',
            'form-1-line_description': 'بند دائن',
        }
        resp = self.client.post(url, data)
        self.assertIn(resp.status_code, [302, 303])
        self.assertEqual(JournalEntry.objects.count(), 1)
        entry = JournalEntry.objects.first()
        self.assertEqual(entry.total_amount, Decimal('100.000'))
        self.assertEqual(entry.lines.count(), 2)

    def test_create_journal_entry_unbalanced(self):
        url = reverse('journal:entry_create')
        data = {
            'entry_date': '2025-08-23',
            'reference_type': 'manual',
            'reference_id': '',
            'description': 'اختبار قيد غير متوازن',
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '2',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-account': str(self.debit_acc.id),
            'form-0-debit': '50.000',
            'form-0-credit': '0',
            'form-0-line_description': 'مدين',
            'form-1-account': str(self.credit_acc.id),
            'form-1-debit': '0',
            'form-1-credit': '100.000',
            'form-1-line_description': 'دائن',
        }
        # يجب أن لا يُنشئ قيداً وأن يعيد عرض الصفحة برسالة خطأ، وليس 500
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(JournalEntry.objects.count(), 0)

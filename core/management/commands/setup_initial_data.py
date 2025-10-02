from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import DocumentSequence, CompanySettings

User = get_user_model()


class Command(BaseCommand):
    help = 'إنشاء البيانات الأولية للنظام'

    def handle(self, *args, **options):
        # إنشاء المستخدمين الأساسيين
        self.create_default_users()
        
        # إنشاء تسلسل أرقام المستندات
        self.create_document_sequences()
        
        # إنشاء إعدادات الشركة
        self.create_company_settings()
        
        self.stdout.write(
            self.style.SUCCESS('تم إنشاء البيانات الأولية بنجاح')
        )

    def create_default_users(self):
        """إنشاء المستخدمين الافتراضيين - معطل"""
        # تم تعطيل إنشاء المستخدمين الافتراضيين
        self.stdout.write(self.style.WARNING('تم تخطي إنشاء المستخدمين الافتراضيين'))
        return



    def create_document_sequences(self):
        """إنشاء تسلسل أرقام المستندات"""
        sequences = [
            ('sales_invoice', 'فاتورة المبيعات', 'SI'),
            ('sales_return', 'مردود المبيعات', 'SR'),
            ('purchase_invoice', 'فاتورة المشتريات', 'PI'),
            ('purchase_return', 'مردود المشتريات', 'PR'),
            ('bank_transfer', 'التحويل بين الحسابات البنكية', 'BT'),
            ('bank_cash_transfer', 'التحويل بين البنوك والصناديق', 'BCT'),
            ('journal_entry', 'القيود المحاسبية', 'JE'),
            ('warehouse_transfer', 'التحويل بين المستودعات', 'WT'),
            ('receipt_voucher', 'سند قبض', 'RV'),
            ('payment_voucher', 'سند صرف', 'PV'),
        ]

        for doc_type, name, prefix in sequences:
            sequence, created = DocumentSequence.objects.get_or_create(
                document_type=doc_type,
                defaults={
                    'prefix': prefix,
                    'digits': 6,
                    'current_number': 1,
                }
            )
            if created:
                self.stdout.write(f'تم إنشاء تسلسل: {name}')

    def create_company_settings(self):
        """إنشاء إعدادات الشركة"""
        settings = CompanySettings.get_settings()
        if not settings.company_name or settings.company_name == 'FinsPilot':
            settings.company_name = 'FinsPilot'
            settings.currency = 'JOD'
            settings.save()
            self.stdout.write('تم إنشاء إعدادات الشركة')

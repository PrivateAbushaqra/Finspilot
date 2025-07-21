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
        """إنشاء المستخدمين الافتراضيين"""
        # Super Admin
        if not User.objects.filter(username='superadmin').exists():
            superadmin = User.objects.create_user(
                username='superadmin',
                email='superadmin@triangle.com',
                first_name='Super',
                last_name='Admin',
                user_type='superadmin',
                is_superuser=True,
                is_staff=True,
                can_access_sales=True,
                can_access_purchases=True,
                can_access_inventory=True,
                can_access_banks=True,
                can_access_reports=True,
                can_delete_invoices=True,
                can_edit_dates=True,
                can_edit_invoice_numbers=True,
                can_see_low_stock_alerts=True,
            )
            # تعيين كلمة المرور بشكل صحيح
            superadmin.set_password('password')
            superadmin.save()
            self.stdout.write(f'تم إنشاء المستخدم: {superadmin.username}')

        # Admin
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_user(
                username='admin',
                email='admin@triangle.com',
                first_name='Admin',
                last_name='User',
                user_type='admin',
                is_staff=True,
                can_access_sales=True,
                can_access_purchases=True,
                can_access_inventory=True,
                can_access_banks=True,
                can_access_reports=True,
                can_delete_invoices=True,
                can_edit_dates=True,
                can_edit_invoice_numbers=True,
                can_see_low_stock_alerts=True,
            )
            # تعيين كلمة المرور بشكل صحيح
            admin.set_password('admin')
            admin.save()
            self.stdout.write(f'تم إنشاء المستخدم: {admin.username}')

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
        if not settings.company_name or settings.company_name == 'Triangle':
            settings.company_name = 'Triangle'
            settings.currency = 'JOD'
            settings.save()
            self.stdout.write('تم إنشاء إعدادات الشركة')

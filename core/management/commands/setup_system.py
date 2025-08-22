from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from inventory.models import Warehouse
from core.models import DocumentSequence, CompanySettings

User = get_user_model()


class Command(BaseCommand):
    help = 'إعداد البيانات الأساسية للنظام (Document Sequences ومستودع Main)'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== بدء إعداد البيانات الأساسية للنظام ==='))
        
        # إنشاء مستودع "Main" إذا لم يكن موجوداً
        if not Warehouse.objects.filter(name='Main').exists():
            try:
                main_warehouse = Warehouse.objects.create(
                    name='Main',
                    code='MAIN',
                    address='الموقع الرئيسي',
                    is_active=True,
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✅ تم إنشاء المستودع الرئيسي: {main_warehouse.name}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ خطأ في إنشاء المستودع الرئيسي: {e}')
                )
        else:
            self.stdout.write(self.style.WARNING('⚠️  المستودع الرئيسي "Main" موجود بالفعل'))
        
        # إنشاء Document Sequences إذا لم تكن موجودة
        sequences = [
            {'document_type': 'sales_invoice', 'prefix': 'INV'},
            {'document_type': 'purchase_invoice', 'prefix': 'PUR'},
            {'document_type': 'sales_return', 'prefix': 'SRN'},
            {'document_type': 'purchase_return', 'prefix': 'PRN'},
            {'document_type': 'receipt_voucher', 'prefix': 'RCP'},
            {'document_type': 'payment_voucher', 'prefix': 'PAY'},
            {'document_type': 'journal_entry', 'prefix': 'JE'},
        ]
        
        created_count = 0
        for seq_data in sequences:
            if not DocumentSequence.objects.filter(document_type=seq_data['document_type']).exists():
                try:
                    sequence = DocumentSequence.objects.create(
                        document_type=seq_data['document_type'],
                        prefix=seq_data['prefix'],
                        digits=6,
                        current_number=1,
                    )
                    created_count += 1
                    document_name = sequence.get_document_type_display()
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ تم إنشاء تسلسل: {document_name}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ خطأ في إنشاء التسلسل {seq_data["document_type"]}: {e}')
                    )
        
        if created_count == 0:
            self.stdout.write(self.style.WARNING('⚠️  جميع تسلسلات المستندات موجودة بالفعل'))
        
        # التأكد من وجود إعدادات الشركة
        if not CompanySettings.objects.exists():
            try:
                CompanySettings.objects.create(
                    company_name='FinsPilot',
                    currency='JOD',
                )
                self.stdout.write(self.style.SUCCESS('✅ تم إنشاء إعدادات الشركة الافتراضية'))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ خطأ في إنشاء إعدادات الشركة: {e}')
                )
        else:
            self.stdout.write(self.style.WARNING('⚠️  إعدادات الشركة موجودة بالفعل'))
        
        self.stdout.write(self.style.SUCCESS('=== انتهاء إعداد البيانات الأساسية للنظام ==='))

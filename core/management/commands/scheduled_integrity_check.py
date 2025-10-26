from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import CompanySettings, AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'فحص سلامة البيانات المحاسبية تلقائياً حسب الإعدادات'

    def handle(self, *args, **options):
        settings = CompanySettings.get_settings()
        
        if not settings.enable_integrity_checks:
            self.stdout.write('ℹ️  فحص سلامة البيانات معطل في الإعدادات')
            return
        
        # التحقق من آخر فحص
        last_check = AuditLog.objects.filter(
            action_type='system_check',
            content_type='data_integrity'
        ).order_by('-timestamp').first()
        
        if last_check:
            hours_since_last_check = (timezone.now() - last_check.timestamp).total_seconds() / 3600
            if hours_since_last_check < settings.integrity_check_frequency:
                self.stdout.write(f'ℹ️  آخر فحص كان منذ {hours_since_last_check:.1f} ساعة. التالي بعد {settings.integrity_check_frequency} ساعة.')
                return
        
        self.stdout.write('🔍 بدء الفحص التلقائي لسلامة البيانات...\n')
        
        # فحص فواتير الشراء
        from purchases.models import PurchaseInvoice
        from journal.models import JournalEntry
        
        purchase_issues = 0
        purchase_invoices = PurchaseInvoice.objects.all()
        
        for invoice in purchase_invoices:
            # فحص سلامة المجاميع الداخلية
            if not invoice.verify_totals_integrity():
                purchase_issues += 1
                self.stdout.write(self.style.WARNING(f'⚠️  فاتورة شراء {invoice.invoice_number}: مجاميع غير متطابقة'))
                
                # إصلاح تلقائي
                if invoice.items.exists():
                    subtotal = invoice.calculate_subtotal_from_items()
                    tax_amount = invoice.calculate_tax_from_items()
                    total_amount = invoice.calculate_total_from_items()
                    
                    invoice.subtotal = subtotal
                    invoice.tax_amount = tax_amount
                    invoice.total_amount = total_amount
                    invoice.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])
                    
                    self.stdout.write(self.style.SUCCESS(f'  ✅ تم إصلاح فاتورة {invoice.invoice_number}'))
            
            # فحص القيد المحاسبي
            try:
                journal_entry = JournalEntry.objects.get(
                    reference_type='purchase_invoice',
                    reference_id=invoice.id
                )
                
                if invoice.total_amount != journal_entry.total_amount:
                    purchase_issues += 1
                    self.stdout.write(self.style.WARNING(f'⚠️  فاتورة شراء {invoice.invoice_number}: قيد غير متطابق'))
                    
                    # إصلاح القيد
                    journal_entry.delete()
                    from journal.services import JournalService
                    JournalService.create_purchase_invoice_entry(invoice, invoice.created_by)
                    
                    self.stdout.write(self.style.SUCCESS(f'  ✅ تم إصلاح قيد فاتورة {invoice.invoice_number}'))
                    
            except JournalEntry.DoesNotExist:
                purchase_issues += 1
                self.stdout.write(self.style.WARNING(f'⚠️  فاتورة شراء {invoice.invoice_number}: لا يوجد قيد محاسبي'))
                
                # إنشاء قيد جديد
                from journal.services import JournalService
                JournalService.create_purchase_invoice_entry(invoice, invoice.created_by)
                
                self.stdout.write(self.style.SUCCESS(f'  ✅ تم إنشاء قيد لفاتورة {invoice.invoice_number}'))
                
            except JournalEntry.MultipleObjectsReturned:
                purchase_issues += 1
                self.stdout.write(self.style.WARNING(f'⚠️  فاتورة شراء {invoice.invoice_number}: قيود متعددة'))
                
                # توحيد القيود
                JournalEntry.objects.filter(
                    reference_type='purchase_invoice',
                    reference_id=invoice.id
                ).delete()
                from journal.services import JournalService
                JournalService.create_purchase_invoice_entry(invoice, invoice.created_by)
                
                self.stdout.write(self.style.SUCCESS(f'  ✅ تم توحيد قيود فاتورة {invoice.invoice_number}'))
        
        # فحص فواتير المبيعات (يمكن إضافة لاحقاً)
        sales_issues = 0
        
        # تسجيل نتيجة الفحص
        system_user = User.objects.filter(is_superuser=True).first()
        if not system_user:
            system_user = User.objects.first()
        
        AuditLog.objects.create(
            user=system_user,
            action_type='system_check',
            content_type='data_integrity',
            object_id=None,
            description=f'فحص سلامة البيانات: فواتير شراء={purchase_issues} مشاكل, فواتير مبيعات={sales_issues} مشاكل',
            ip_address='127.0.0.1'
        )
        
        total_issues = purchase_issues + sales_issues
        
        if total_issues == 0:
            self.stdout.write(self.style.SUCCESS(f'\n🎉 الفحص التلقائي مكتمل - لا توجد مشاكل'))
        else:
            self.stdout.write(self.style.WARNING(f'\n⚠️  الفحص التلقائي مكتمل - تم إصلاح {total_issues} مشكلة'))
        
        self.stdout.write(f'📅 التالي فحص تلقائي بعد {settings.integrity_check_frequency} ساعة')
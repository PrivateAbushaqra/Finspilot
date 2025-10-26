from django.core.management.base import BaseCommand
from purchases.models import PurchaseInvoice
from journal.models import JournalEntry
from decimal import Decimal


class Command(BaseCommand):
    help = 'فحص سلامة فواتير الشراء والقيود المحاسبية المرتبطة بها'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='إصلاح المشاكل المكتشفة تلقائياً',
        )
        parser.add_argument(
            '--invoice',
            type=str,
            help='فحص فاتورة محددة برقمها',
        )

    def handle(self, *args, **options):
        self.stdout.write('🔍 بدء فحص سلامة فواتير الشراء...\n')

        # تحديد الفواتير المراد فحصها
        if options['invoice']:
            try:
                invoices = PurchaseInvoice.objects.filter(invoice_number=options['invoice']).order_by('-id')
                if not invoices:
                    self.stdout.write(self.style.ERROR(f'❌ الفاتورة {options["invoice"]} غير موجودة'))
                    return
                self.stdout.write(f'📋 فحص {invoices.count()} فاتورة برقم {options["invoice"]}\n')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ خطأ في البحث عن الفاتورة: {e}'))
                return
        else:
            invoices = PurchaseInvoice.objects.all()
            self.stdout.write(f'📋 فحص {invoices.count()} فاتورة شراء\n')

        issues_found = 0
        fixed_count = 0

        for invoice in invoices:
            self.stdout.write(f'🔍 فحص فاتورة: {invoice.invoice_number}')

            # فحص سلامة المجاميع الداخلية
            if not invoice.verify_totals_integrity():
                self.stdout.write(self.style.WARNING(f'  ⚠️  المجاميع الداخلية غير متطابقة مع العناصر'))
                issues_found += 1

                if options['fix']:
                    # إعادة حساب المجاميع من العناصر
                    if invoice.items.exists():
                        subtotal = Decimal('0')
                        tax_amount = Decimal('0')
                        total_amount = Decimal('0')

                        for item in invoice.items.all():
                            subtotal += item.quantity * item.unit_price
                            tax_amount += item.tax_amount
                            total_amount += item.total_amount

                        invoice.subtotal = subtotal.quantize(Decimal('0.001'), rounding=Decimal('0.001').quantize(Decimal('0.001')))
                        invoice.tax_amount = tax_amount.quantize(Decimal('0.001'), rounding=Decimal('0.001').quantize(Decimal('0.001')))
                        invoice.total_amount = total_amount.quantize(Decimal('0.001'), rounding=Decimal('0.001').quantize(Decimal('0.001')))
                        invoice.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])

                        self.stdout.write(self.style.SUCCESS(f'  ✅ تم إصلاح المجاميع الداخلية'))
                        fixed_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(f'  ⚠️  لا توجد عناصر في الفاتورة'))
                else:
                    self.stdout.write(f'    المتوقع: subtotal={invoice.calculate_subtotal_from_items():.3f}, tax={invoice.calculate_tax_from_items():.3f}, total={invoice.calculate_total_from_items():.3f}')
                    self.stdout.write(f'    الحالي: subtotal={invoice.subtotal:.3f}, tax={invoice.tax_amount:.3f}, total={invoice.total_amount:.3f}')

            # فحص تطابق القيد المحاسبي
            try:
                journal_entry = JournalEntry.objects.get(
                    reference_type='purchase_invoice',
                    reference_id=invoice.id
                )

                if invoice.total_amount != journal_entry.total_amount:
                    self.stdout.write(self.style.WARNING(f'  ⚠️  القيد المحاسبي غير متطابق: الفاتورة={invoice.total_amount}, القيد={journal_entry.total_amount}'))
                    issues_found += 1

                    if options['fix']:
                        # حذف القيد القديم وإنشاء قيد جديد
                        journal_entry.delete()
                        from journal.services import JournalService
                        JournalService.create_purchase_invoice_entry(invoice, invoice.created_by)
                        self.stdout.write(self.style.SUCCESS(f'  ✅ تم إعادة إنشاء القيد المحاسبي'))
                        fixed_count += 1
                else:
                    self.stdout.write(f'  ✅ القيد المحاسبي متطابق')

            except JournalEntry.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  ⚠️  لا يوجد قيد محاسبي للفاتورة'))
                issues_found += 1

                if options['fix']:
                    # إنشاء قيد محاسبي جديد
                    from journal.services import JournalService
                    JournalService.create_purchase_invoice_entry(invoice, invoice.created_by)
                    self.stdout.write(self.style.SUCCESS(f'  ✅ تم إنشاء قيد محاسبي جديد'))
                    fixed_count += 1

            except JournalEntry.MultipleObjectsReturned:
                self.stdout.write(self.style.ERROR(f'  ❌ يوجد أكثر من قيد محاسبي للفاتورة'))
                issues_found += 1

                if options['fix']:
                    # حذف جميع القيود وإنشاء قيد واحد
                    JournalEntry.objects.filter(
                        reference_type='purchase_invoice',
                        reference_id=invoice.id
                    ).delete()
                    from journal.services import JournalService
                    JournalService.create_purchase_invoice_entry(invoice, invoice.created_by)
                    self.stdout.write(self.style.SUCCESS(f'  ✅ تم توحيد القيود المحاسبية'))
                    fixed_count += 1

        self.stdout.write(f'\n📊 ملخص الفحص:')
        self.stdout.write(f'   المشاكل المكتشفة: {issues_found}')
        if options['fix']:
            self.stdout.write(f'   المشاكل المصلحة: {fixed_count}')

        if issues_found == 0:
            self.stdout.write(self.style.SUCCESS('🎉 جميع الفواتير سليمة!'))
        elif not options['fix']:
            self.stdout.write(self.style.WARNING('💡 استخدم --fix لإصلاح المشاكل المكتشفة تلقائياً'))
        else:
            remaining = issues_found - fixed_count
            if remaining == 0:
                self.stdout.write(self.style.SUCCESS('🎉 تم إصلاح جميع المشاكل!'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  لم يتم إصلاح {remaining} مشكلة'))
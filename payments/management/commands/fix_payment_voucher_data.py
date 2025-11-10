"""
أمر Django لإصلاح بيانات سندات الصرف الموجودة
Fix existing payment voucher data - remove duplicates and create missing journal entries
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from payments.models import PaymentVoucher
from cashboxes.models import CashboxTransaction
from journal.models import JournalEntry
from journal.services import JournalService
from decimal import Decimal


class Command(BaseCommand):
    help = 'إصلاح بيانات سندات الصرف - إزالة التكرار وإنشاء القيود الناقصة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--voucher-number',
            type=str,
            help='رقم سند صرف محدد لإصلاحه',
        )

    def handle(self, *args, **options):
        voucher_number = options.get('voucher_number')
        
        if voucher_number:
            # إصلاح سند صرف محدد
            vouchers = PaymentVoucher.objects.filter(voucher_number=voucher_number)
            if not vouchers.exists():
                self.stdout.write(self.style.ERROR(f'سند الصرف رقم {voucher_number} غير موجود'))
                return
        else:
            # إصلاح جميع سندات الصرف
            vouchers = PaymentVoucher.objects.all()
        
        self.stdout.write(self.style.WARNING(f'سيتم إصلاح {vouchers.count()} سند صرف'))
        
        fixed_count = 0
        error_count = 0
        
        for voucher in vouchers:
            try:
                with transaction.atomic():
                    self.stdout.write(f'\n--- معالجة سند الصرف {voucher.voucher_number} ---')
                    
                    # 1. إصلاح حركات الصندوق المكررة
                    if voucher.payment_type == 'cash' and voucher.cashbox:
                        cashbox_trans = CashboxTransaction.objects.filter(
                            reference_type='payment',
                            reference_id=voucher.id,
                            transaction_type='withdrawal'
                        ).order_by('created_at')
                        
                        trans_count = cashbox_trans.count()
                        if trans_count > 1:
                            self.stdout.write(self.style.WARNING(f'  وجد {trans_count} حركة صندوق مكررة'))
                            
                            # حذف الحركات المكررة (الإبقاء على الأولى فقط)
                            duplicates = cashbox_trans[1:]
                            for dup in duplicates:
                                self.stdout.write(f'    حذف حركة صندوق مكررة: {dup.id}')
                                dup.delete()
                            
                            self.stdout.write(self.style.SUCCESS(f'  ✓ تم حذف {len(duplicates)} حركة صندوق مكررة'))
                        
                        elif trans_count == 0:
                            # إنشاء حركة صندوق مفقودة
                            self.stdout.write(self.style.WARNING(f'  لا توجد حركة صندوق - سيتم إنشاؤها'))
                            CashboxTransaction.objects.create(
                                cashbox=voucher.cashbox,
                                transaction_type='withdrawal',
                                amount=-voucher.amount,
                                description=f'سند صرف {voucher.voucher_number} - {voucher.beneficiary_display}',
                                date=voucher.date,
                                reference_type='payment',
                                reference_id=voucher.id,
                                created_by=voucher.created_by
                            )
                            self.stdout.write(self.style.SUCCESS(f'  ✓ تم إنشاء حركة صندوق'))
                        else:
                            self.stdout.write(self.style.SUCCESS(f'  ✓ حركة الصندوق صحيحة'))
                    
                    # 2. إصلاح القيود المحاسبية
                    journal_entries = JournalEntry.objects.filter(
                        reference_type='payment_voucher',
                        reference_id=voucher.id
                    )
                    
                    entries_count = journal_entries.count()
                    if entries_count > 1:
                        self.stdout.write(self.style.WARNING(f'  وجد {entries_count} قيد محاسبي مكرر'))
                        
                        # حذف القيود المكررة (الإبقاء على الأول فقط)
                        duplicates = journal_entries.order_by('created_at')[1:]
                        for dup in duplicates:
                            self.stdout.write(f'    حذف قيد محاسبي مكرر: {dup.entry_number}')
                            dup.delete()
                        
                        self.stdout.write(self.style.SUCCESS(f'  ✓ تم حذف {len(duplicates)} قيد محاسبي مكرر'))
                    
                    elif entries_count == 0:
                        # إنشاء قيد محاسبي مفقود
                        self.stdout.write(self.style.WARNING(f'  لا يوجد قيد محاسبي - سيتم إنشاؤه'))
                        try:
                            entry = JournalService.create_payment_voucher_entry(voucher, voucher.created_by)
                            self.stdout.write(self.style.SUCCESS(f'  ✓ تم إنشاء قيد محاسبي: {entry.entry_number}'))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'  ✗ خطأ في إنشاء القيد المحاسبي: {e}'))
                            raise
                    else:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ القيد المحاسبي صحيح'))
                    
                    # 3. التحقق من حركة حساب المورد (إن وجد)
                    if voucher.supplier and voucher.voucher_type == 'supplier':
                        from accounts.models import AccountTransaction
                        account_trans = AccountTransaction.objects.filter(
                            reference_type='payment',
                            reference_id=voucher.id
                        )
                        
                        if account_trans.count() > 1:
                            self.stdout.write(self.style.WARNING(f'  وجد {account_trans.count()} حركة حساب مكررة'))
                            duplicates = account_trans.order_by('created_at')[1:]
                            for dup in duplicates:
                                self.stdout.write(f'    حذف حركة حساب مكررة: {dup.transaction_number}')
                                dup.delete()
                            self.stdout.write(self.style.SUCCESS(f'  ✓ تم حذف {len(duplicates)} حركة حساب مكررة'))
                        elif account_trans.count() == 0:
                            self.stdout.write(self.style.WARNING(f'  لا توجد حركة حساب للمورد - سيتم إنشاؤها'))
                            # يمكن إضافة كود لإنشاء حركة الحساب إذا لزم الأمر
                    
                    fixed_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ تم إصلاح سند الصرف {voucher.voucher_number} بنجاح\n'))
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'✗ خطأ في معالجة سند الصرف {voucher.voucher_number}: {e}\n'))
                import traceback
                traceback.print_exc()
        
        # ملخص النتائج
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'تم إصلاح {fixed_count} سند صرف بنجاح'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'فشل إصلاح {error_count} سند صرف'))
        self.stdout.write('='*60)

"""
Django management command لإصلاح أرصدة Balance After
الاستخدام: python manage.py fix_balance_after
"""
from django.core.management.base import BaseCommand
from accounts.models import AccountTransaction
from customers.models import CustomerSupplier
from decimal import Decimal
from core.models import AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'إصلاح جميع أرصدة Balance After في معاملات الحسابات (متوافق مع IFRS)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض المشاكل فقط دون إصلاحها',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  وضع الفحص فقط (Dry Run) - لن يتم إجراء أي تعديلات'))
        
        self.stdout.write('=' * 80)
        self.stdout.write('🔧 إصلاح أرصدة Balance After')
        self.stdout.write('=' * 80)
        self.stdout.write('')
        
        # الحصول على المستخدم المسؤول
        admin_user = User.objects.filter(is_superuser=True).first()
        
        # تسجيل بداية العملية
        if admin_user and not dry_run:
            AuditLog.objects.create(
                user=admin_user,
                action_type='maintenance',
                content_type='account_transaction',
                description='بدء إصلاح أرصدة Balance After (IFRS compliant)',
                ip_address='system'
            )
        
        # معالجة جميع العملاء
        customers = CustomerSupplier.objects.filter(transactions__isnull=False).distinct()
        total_checked = 0
        total_fixed = 0
        
        for customer in customers:
            self.stdout.write(f'📊 {customer.name}')
            
            transactions = AccountTransaction.objects.filter(
                customer_supplier=customer
            ).order_by('date', 'created_at', 'id')
            
            balance = Decimal('0')
            fixed_count = 0
            
            for txn in transactions:
                total_checked += 1
                
                if txn.direction == 'debit':
                    balance += txn.amount
                else:
                    balance -= txn.amount
                
                if abs(balance - txn.balance_after) >= Decimal('0.001'):
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f'   ⚠️  {txn.transaction_number}: '
                                f'{float(txn.balance_after):.3f} → {float(balance):.3f}'
                            )
                        )
                    else:
                        old_balance = txn.balance_after
                        txn.balance_after = balance
                        txn._skip_balance_update = True
                        txn.save(update_fields=['balance_after'])
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'   ✅ {txn.transaction_number}: '
                                f'{float(old_balance):.3f} → {float(balance):.3f}'
                            )
                        )
                    
                    fixed_count += 1
                    total_fixed += 1
            
            if fixed_count == 0:
                self.stdout.write(f'   ℹ️  صحيح ({transactions.count()} معاملة)')
            else:
                self.stdout.write(f'   🎯 {fixed_count}/{transactions.count()}')
            
            self.stdout.write('')
        
        # تسجيل انتهاء العملية
        if admin_user and not dry_run:
            AuditLog.objects.create(
                user=admin_user,
                action_type='maintenance',
                content_type='account_transaction',
                description=f'اكتمل إصلاح الأرصدة: {total_checked} معاملة، {total_fixed} مُصلح',
                ip_address='system'
            )
        
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS(f'✅ النتيجة:'))
        self.stdout.write(f'   المفحوص: {total_checked}')
        self.stdout.write(f'   المُصلح: {total_fixed}')
        self.stdout.write(f'   العملاء: {customers.count()}')
        self.stdout.write('=' * 80)
        
        if dry_run and total_fixed > 0:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  تم العثور على {total_fixed} مشكلة. '
                    'قم بتشغيل الأمر بدون --dry-run للإصلاح.'
                )
            )

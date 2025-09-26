from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from revenues_expenses.models import RecurringRevenueExpense, RevenueExpenseEntry
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'معالجة الإيرادات والمصاريف المتكررة وإنشاء القيود التلقائية'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض ما سيتم إنشاؤه دون تنفيذه فعلياً',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('تشغيل تجريبي - لن يتم إنشاء أي قيود'))

        today = date.today()

        # الحصول على جميع الإيرادات والمصاريف المتكررة النشطة والتي تحتاج إلى معالجة
        recurring_items = RecurringRevenueExpense.objects.filter(
            is_active=True,
            auto_generate=True,
            next_due_date__lte=today
        )

        if not recurring_items.exists():
            self.stdout.write(self.style.SUCCESS('لا توجد إيرادات أو مصاريف متكررة تحتاج إلى معالجة'))
            return

        # الحصول على مستخدم النظام أو المشرف الأول
        system_user = User.objects.filter(is_superuser=True).first()
        if not system_user:
            system_user = User.objects.filter(user_type='superadmin').first()
        if not system_user:
            self.stdout.write(self.style.ERROR('لا يوجد مستخدم نظام لإنشاء القيود'))
            return

        created_count = 0

        for recurring in recurring_items:
            try:
                # التحقق من عدم وجود قيد لهذا التاريخ بالفعل
                existing_entry = RevenueExpenseEntry.objects.filter(
                    description__icontains=f'توليد تلقائي - {recurring.name}',
                    date=recurring.next_due_date,
                    type=recurring.category.type,
                    category=recurring.category,
                    amount=recurring.amount
                ).exists()

                if existing_entry:
                    self.stdout.write(
                        self.style.WARNING(f'تم تجاهل {recurring.name} - قيد موجود بالفعل')
                    )
                    continue

                if not dry_run:
                    # إنشاء القيد
                    entry = RevenueExpenseEntry.objects.create(
                        type=recurring.category.type,
                        category=recurring.category,
                        sector=recurring.sector,
                        amount=recurring.amount,
                        currency=recurring.currency,
                        description=f'توليد تلقائي - {recurring.name}',
                        payment_method=recurring.payment_method,
                        date=recurring.next_due_date,
                        created_by=system_user,
                        is_approved=True,  # اعتماد تلقائي للقيود المتكررة
                        approved_by=system_user,
                        approved_at=timezone.now()
                    )

                    # تحديث تاريخ آخر توليد
                    recurring.last_generated = recurring.next_due_date

                    # حساب التاريخ التالي
                    if recurring.frequency == 'daily':
                        next_date = recurring.next_due_date + timedelta(days=1)
                    elif recurring.frequency == 'weekly':
                        next_date = recurring.next_due_date + timedelta(weeks=1)
                    elif recurring.frequency == 'monthly':
                        # إضافة شهر
                        if recurring.next_due_date.month == 12:
                            next_date = recurring.next_due_date.replace(year=recurring.next_due_date.year + 1, month=1)
                        else:
                            next_date = recurring.next_due_date.replace(month=recurring.next_due_date.month + 1)
                    elif recurring.frequency == 'quarterly':
                        # إضافة 3 أشهر
                        month = recurring.next_due_date.month + 3
                        year = recurring.next_due_date.year
                        if month > 12:
                            month -= 12
                            year += 1
                        next_date = recurring.next_due_date.replace(year=year, month=month)
                    elif recurring.frequency == 'semi_annual':
                        # إضافة 6 أشهر
                        month = recurring.next_due_date.month + 6
                        year = recurring.next_due_date.year
                        if month > 12:
                            month -= 12
                            year += 1
                        next_date = recurring.next_due_date.replace(year=year, month=month)
                    elif recurring.frequency == 'annual':
                        next_date = recurring.next_due_date.replace(year=recurring.next_due_date.year + 1)
                    else:
                        next_date = recurring.next_due_date + timedelta(days=1)  # fallback

                    # التحقق من تاريخ النهاية
                    if recurring.end_date and next_date > recurring.end_date:
                        recurring.is_active = False
                        recurring.next_due_date = None
                    else:
                        recurring.next_due_date = next_date

                    recurring.save()

                    self.stdout.write(
                        self.style.SUCCESS(f'تم إنشاء قيد لـ {recurring.name} بتاريخ {recurring.next_due_date}')
                    )
                else:
                    self.stdout.write(
                        f'سيتم إنشاء قيد لـ {recurring.name} بتاريخ {recurring.next_due_date}'
                    )

                created_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'خطأ في معالجة {recurring.name}: {str(e)}')
                )

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'سيتم إنشاء {created_count} قيد'))
        else:
            self.stdout.write(self.style.SUCCESS(f'تم إنشاء {created_count} قيد بنجاح'))
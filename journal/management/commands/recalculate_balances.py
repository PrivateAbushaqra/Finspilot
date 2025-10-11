from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from journal.models import Account
from core.models import AuditLog
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'إعادة حساب وتحديث أرصدة جميع الحسابات المحاسبية'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='فحص الأرصدة فقط دون تحديث (عرض الفروقات)',
        )
        parser.add_argument(
            '--account-code',
            type=str,
            help='إعادة حساب رصيد حساب محدد فقط',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='تصحيح الأرصدة غير المتطابقة تلقائياً',
        )

    def handle(self, *args, **options):
        check_only = options['check_only']
        account_code = options.get('account_code')
        auto_fix = options['fix']

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("🔍 فحص أرصدة الحسابات المحاسبية"))
        self.stdout.write("=" * 80)

        # الحصول على الحسابات المطلوب فحصها
        if account_code:
            accounts = Account.objects.filter(code=account_code)
            if not accounts.exists():
                self.stdout.write(self.style.ERROR(f"❌ لم يتم العثور على حساب بالكود: {account_code}"))
                return
        else:
            accounts = Account.objects.all()

        total_accounts = accounts.count()
        mismatched_accounts = []
        matched_accounts = 0

        self.stdout.write(f"\n📊 عدد الحسابات: {total_accounts}")
        self.stdout.write("\n" + "-" * 80)

        # فحص كل حساب
        for i, account in enumerate(accounts, 1):
            calculated_balance = account.get_balance()
            db_balance = account.balance
            
            # عرض التقدم كل 50 حساب
            if i % 50 == 0:
                self.stdout.write(f"⏳ تم فحص {i}/{total_accounts} حساب...")

            # مقارنة الأرصدة
            if calculated_balance != db_balance:
                difference = calculated_balance - db_balance
                mismatched_accounts.append({
                    'account': account,
                    'code': account.code,
                    'name': account.name,
                    'db_balance': db_balance,
                    'calculated_balance': calculated_balance,
                    'difference': difference
                })
            else:
                matched_accounts += 1

        # عرض النتائج
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📈 نتائج الفحص:"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"\n✅ حسابات متطابقة: {matched_accounts}")
        self.stdout.write(f"⚠️  حسابات غير متطابقة: {len(mismatched_accounts)}")

        if mismatched_accounts:
            self.stdout.write("\n" + "-" * 80)
            self.stdout.write(self.style.WARNING("🔧 الحسابات التي تحتاج تصحيح:"))
            self.stdout.write("-" * 80)

            for item in mismatched_accounts:
                self.stdout.write(f"\n📌 الحساب: {item['code']} - {item['name']}")
                self.stdout.write(f"   💾 رصيد قاعدة البيانات: {item['db_balance']}")
                self.stdout.write(f"   🧮 رصيد محسوب من القيود: {item['calculated_balance']}")
                self.stdout.write(self.style.ERROR(f"   ⚡ الفرق: {item['difference']}"))

            # تصحيح الأرصدة إذا طُلب ذلك
            if not check_only and (auto_fix or self.confirm_fix()):
                self.stdout.write("\n" + "=" * 80)
                self.stdout.write(self.style.WARNING("🔧 بدء تصحيح الأرصدة..."))
                self.stdout.write("=" * 80)
                
                fixed_count = 0
                errors = []

                with transaction.atomic():
                    for item in mismatched_accounts:
                        try:
                            account = item['account']
                            old_balance = account.balance
                            new_balance = item['calculated_balance']
                            
                            # تحديث الرصيد
                            account.balance = new_balance
                            account.save(update_fields=['balance'])
                            
                            fixed_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"✅ تم تصحيح: {account.code} - من {old_balance} إلى {new_balance}"
                                )
                            )

                            # تسجيل في audit log
                            try:
                                # محاولة الحصول على مستخدم النظام
                                system_user = User.objects.filter(is_superuser=True).first()
                                if system_user:
                                    AuditLog.objects.create(
                                        user=system_user,
                                        action='update',
                                        model_name='Account',
                                        object_id=str(account.id),
                                        object_repr=f"{account.code} - {account.name}",
                                        changes={
                                            'field': 'balance',
                                            'old_value': str(old_balance),
                                            'new_value': str(new_balance),
                                            'difference': str(item['difference']),
                                            'reason': 'تصحيح تلقائي للرصيد بواسطة recalculate_balances',
                                            'timestamp': str(timezone.now())
                                        }
                                    )
                            except Exception as audit_error:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"⚠️  تحذير: فشل تسجيل في audit log: {audit_error}"
                                    )
                                )

                        except Exception as e:
                            errors.append(f"حساب {item['code']}: {str(e)}")
                            self.stdout.write(
                                self.style.ERROR(f"❌ خطأ في تصحيح {item['code']}: {e}")
                            )

                # عرض ملخص التصحيح
                self.stdout.write("\n" + "=" * 80)
                self.stdout.write(self.style.SUCCESS("✨ اكتمل التصحيح"))
                self.stdout.write("=" * 80)
                self.stdout.write(f"\n✅ تم تصحيح: {fixed_count} حساب")
                
                if errors:
                    self.stdout.write(f"❌ أخطاء: {len(errors)}")
                    for error in errors:
                        self.stdout.write(self.style.ERROR(f"   - {error}"))

        else:
            self.stdout.write("\n" + self.style.SUCCESS("✅ جميع الحسابات متطابقة! لا حاجة للتصحيح."))

        self.stdout.write("\n" + "=" * 80)

    def confirm_fix(self):
        """طلب تأكيد من المستخدم لتصحيح الأرصدة"""
        self.stdout.write("\n" + "=" * 80)
        response = input("⚠️  هل تريد تصحيح هذه الأرصدة؟ (yes/no): ")
        return response.lower() in ['yes', 'y', 'نعم']

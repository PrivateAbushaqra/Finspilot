from django.core.management.base import BaseCommand
from django.db import transaction
from journal.sync_utils import sync_all_cashboxes_and_banks


class Command(BaseCommand):
    help = 'مزامنة أرصدة جميع الصناديق والبنوك مع أرصدة حساباتهم المحاسبية'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("🔄 بدء مزامنة أرصدة الصناديق والبنوك"))
        self.stdout.write("=" * 80)

        with transaction.atomic():
            report = sync_all_cashboxes_and_banks()

        # عرض النتائج
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 نتائج المزامنة:"))
        self.stdout.write("=" * 80)

        self.stdout.write(f"\n💰 الصناديق:")
        self.stdout.write(f"   ✅ تم مزامنة: {report['cashboxes']['synced']} صندوق")
        if report['cashboxes']['errors']:
            self.stdout.write(f"   ❌ أخطاء: {len(report['cashboxes']['errors'])}")
            for error in report['cashboxes']['errors']:
                self.stdout.write(self.style.ERROR(f"      - {error}"))

        self.stdout.write(f"\n🏦 البنوك:")
        self.stdout.write(f"   ✅ تم مزامنة: {report['banks']['synced']} حساب بنكي")
        if report['banks']['errors']:
            self.stdout.write(f"   ❌ أخطاء: {len(report['banks']['errors'])}")
            for error in report['banks']['errors']:
                self.stdout.write(self.style.ERROR(f"      - {error}"))

        total_synced = report['cashboxes']['synced'] + report['banks']['synced']
        total_errors = len(report['cashboxes']['errors']) + len(report['banks']['errors'])

        self.stdout.write("\n" + "=" * 80)
        if total_synced > 0:
            self.stdout.write(self.style.SUCCESS(f"✅ تم مزامنة {total_synced} حساب بنجاح"))
        if total_errors > 0:
            self.stdout.write(self.style.WARNING(f"⚠️  {total_errors} خطأ"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ لا توجد أخطاء"))
        
        self.stdout.write("=" * 80)

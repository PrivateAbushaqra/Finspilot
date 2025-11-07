"""
أمر Django لتحديث الحسابات المحاسبية لتطابق IFRS

الاستخدام:
    python manage.py update_accounts_to_ifrs [--dry-run]

الخيارات:
    --dry-run: عرض التغييرات فقط دون تنفيذها
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from journal.models import Account


class Command(BaseCommand):
    help = 'تحديث الحسابات المحاسبية لتطابق المعايير الدولية IFRS'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض التغييرات فقط دون تنفيذها',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️ وضع المراجعة (Dry Run) - لن يتم تنفيذ أي تغييرات'))
        
        self.stdout.write(self.style.SUCCESS('🔍 بدء فحص وتحديث الحسابات المحاسبية...'))
        
        # تعريف الحسابات الرئيسية المطلوبة
        parent_accounts = [
            {'code': '10', 'name': 'النقد وما في حكمه', 'type': 'asset'},
            {'code': '102', 'name': 'الحسابات البنكية', 'type': 'asset'},
            {'code': '12', 'name': 'المخزون', 'type': 'asset'},
            {'code': '1301', 'name': 'حسابات العملاء', 'type': 'asset'},
            {'code': '14', 'name': 'ذمم مدينة أخرى', 'type': 'asset'},
            {'code': '201', 'name': 'حسابات الموردين', 'type': 'liability'},
            {'code': '210', 'name': 'حسابات الموردين', 'type': 'liability'},
            {'code': '2101', 'name': 'حسابات الموردين', 'type': 'liability'},
            {'code': '40', 'name': 'الإيرادات', 'type': 'revenue'},
            {'code': '42', 'name': 'خصومات ومسموحات المبيعات', 'type': 'expense'},
            {'code': '50', 'name': 'تكلفة المبيعات والمشتريات', 'type': 'expense'},
            {'code': '60', 'name': 'المصاريف العمومية والإدارية', 'type': 'expense'},
        ]
        
        # تعريف الحسابات الفرعية وحساباتها الرئيسية
        child_accounts_mapping = [
            {'code': '101', 'parent_code': '10'},
            {'code_prefix': '102', 'parent_code': '102', 'exclude_codes': ['102']},
            {'code': '1020', 'parent_code': '12'},
            {'code_prefix': '1301', 'parent_code': '1301', 'exclude_codes': ['1301']},
            {'code': '141', 'parent_code': '14'},
            {'code_prefix': '201-', 'parent_code': '201'},
            {'code_prefix': '210', 'parent_code': '210', 'exclude_codes': ['210', '2101']},
            {'code_prefix': '2101', 'parent_code': '2101', 'exclude_codes': ['2101']},
            {'code': '4010', 'parent_code': '40'},
            {'code': '4020', 'parent_code': '42'},
            {'code': '501', 'parent_code': '50'},
            {'code': '5001', 'parent_code': '50'},
            {'code': '6010', 'parent_code': '60'},
        ]
        
        created_parents = 0
        updated_children = 0
        errors = []
        
        try:
            with transaction.atomic():
                # 1. إنشاء الحسابات الرئيسية
                self.stdout.write(self.style.MIGRATE_HEADING('\n📂 إنشاء الحسابات الرئيسية...'))
                for parent_data in parent_accounts:
                    parent, created = Account.objects.get_or_create(
                        code=parent_data['code'],
                        defaults={
                            'name': parent_data['name'],
                            'account_type': parent_data['type'],
                            'description': f'حساب رئيسي - حسب IFRS',
                            'is_active': True,
                        }
                    )
                    
                    if created:
                        created_parents += 1
                        self.stdout.write(f'  ✅ تم إنشاء الحساب الرئيسي: {parent.code} - {parent.name}')
                    else:
                        self.stdout.write(f'  ⏭️  الحساب موجود: {parent.code} - {parent.name}')
                
                # 2. تحديث الحسابات الفرعية
                self.stdout.write(self.style.MIGRATE_HEADING('\n🔗 ربط الحسابات الفرعية بالرئيسية...'))
                for mapping in child_accounts_mapping:
                    if 'code' in mapping:
                        # حساب فرعي محدد
                        children = Account.objects.filter(
                            code=mapping['code'],
                            parent__isnull=True
                        )
                    elif 'code_prefix' in mapping:
                        # حسابات فرعية بنفس البادئة
                        children = Account.objects.filter(
                            code__startswith=mapping['code_prefix'],
                            parent__isnull=True
                        )
                        
                        # استثناء بعض الأكواد
                        if 'exclude_codes' in mapping:
                            children = children.exclude(code__in=mapping['exclude_codes'])
                    else:
                        continue
                    
                    # الحصول على الحساب الأب
                    try:
                        parent = Account.objects.get(code=mapping['parent_code'])
                    except Account.DoesNotExist:
                        error_msg = f'لم يتم العثور على الحساب الأب: {mapping["parent_code"]}'
                        errors.append(error_msg)
                        self.stdout.write(self.style.ERROR(f'  ❌ {error_msg}'))
                        continue
                    
                    # تحديث الحسابات الفرعية
                    for child in children:
                        if not dry_run:
                            child.parent = parent
                            child.save()
                        
                        updated_children += 1
                        self.stdout.write(f'  ✅ تم ربط: {child.code} - {child.name} ← {parent.code}')
                
                # 3. تصحيح نوع حساب المبيعات
                self.stdout.write(self.style.MIGRATE_HEADING('\n🔧 تصحيح أنواع الحسابات...'))
                sales_account = Account.objects.filter(code='4010').first()
                if sales_account and sales_account.account_type == 'sales':
                    if not dry_run:
                        sales_account.account_type = 'revenue'
                        sales_account.save()
                    self.stdout.write(f'  ✅ تم تصحيح نوع حساب المبيعات من "sales" إلى "revenue"')
                
                # 4. عرض الإحصائيات
                self.stdout.write(self.style.MIGRATE_HEADING('\n📊 الإحصائيات:'))
                total_accounts = Account.objects.count()
                parent_accounts_count = Account.objects.filter(parent__isnull=True).count()
                child_accounts_count = Account.objects.filter(parent__isnull=False).count()
                orphan_accounts = Account.objects.filter(
                    parent__isnull=True
                ).exclude(
                    code__in=[p['code'] for p in parent_accounts]
                )
                
                self.stdout.write(f'  📈 إجمالي الحسابات: {total_accounts}')
                self.stdout.write(f'  📂 حسابات رئيسية: {parent_accounts_count}')
                self.stdout.write(f'  📄 حسابات فرعية: {child_accounts_count}')
                self.stdout.write(f'  ⚠️  حسابات بدون أب (يتيمة): {orphan_accounts.count()}')
                
                if orphan_accounts.exists():
                    self.stdout.write(self.style.WARNING('\n⚠️  الحسابات التالية لا تزال بدون حساب أب:'))
                    for account in orphan_accounts:
                        self.stdout.write(f'    - {account.code} - {account.name}')
                
                # 5. عرض النتيجة النهائية
                self.stdout.write(self.style.MIGRATE_HEADING('\n✅ النتيجة النهائية:'))
                self.stdout.write(f'  ✨ تم إنشاء {created_parents} حساب رئيسي جديد')
                self.stdout.write(f'  🔗 تم ربط {updated_children} حساب فرعي')
                
                if errors:
                    self.stdout.write(self.style.ERROR(f'\n❌ حدثت {len(errors)} أخطاء:'))
                    for error in errors:
                        self.stdout.write(f'    - {error}')
                
                if dry_run:
                    self.stdout.write(self.style.WARNING('\n⚠️ وضع المراجعة - لم يتم حفظ أي تغييرات'))
                    raise Exception('Dry run - rollback')
                else:
                    self.stdout.write(self.style.SUCCESS('\n🎉 تم تحديث الحسابات بنجاح!'))
                    self.stdout.write(self.style.SUCCESS('✅ الحسابات الآن متوافقة مع IFRS'))
        
        except Exception as e:
            if not dry_run:
                self.stdout.write(self.style.ERROR(f'\n❌ خطأ أثناء التحديث: {str(e)}'))
                raise

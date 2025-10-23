from django.core.management.base import BaseCommand
from journal.models import Account

class Command(BaseCommand):
    help = 'إنشاء الحسابات المحاسبية الأساسية حسب IFRS'

    def handle(self, *args, **options):
        # الحسابات الأساسية حسب IFRS - معدلة لتكون أكثر اكتمالاً
        accounts_data = [
            # الأصول المتداولة (Current Assets)
            {'code': '101', 'name': 'النقد في الصندوق', 'type': 'asset'},
            {'code': '102', 'name': 'الحسابات البنكية', 'type': 'asset'},
            {'code': '103', 'name': 'الاستثمارات قصيرة الأجل', 'type': 'asset'},
            {'code': '1031', 'name': 'استثمارات قصيرة أخرى', 'type': 'asset'},
            {'code': '104', 'name': 'الدفعات المقدمة', 'type': 'asset'},
            {'code': '1041', 'name': 'دفعات مقدمة أخرى', 'type': 'asset'},
            {'code': '1101', 'name': 'أصول متداولة أخرى', 'type': 'asset'},
            {'code': '1201', 'name': 'مخزون المستودعات', 'type': 'asset'},
            {'code': '1301', 'name': 'حسابات العملاء', 'type': 'asset'},
            {'code': '1302', 'name': 'حسابات مدينة أخرى', 'type': 'asset'},
            {'code': '1303', 'name': 'حسابات مدينة متنوعة', 'type': 'asset'},
            {'code': '1070', 'name': 'ضريبة القيمة المضافة مدخلة', 'type': 'asset'},

            # الأصول غير المتداولة (Non-current Assets)
            {'code': '1401', 'name': 'الأصول الثابتة', 'type': 'asset'},
            {'code': '1402', 'name': 'الإهلاك المتراكم', 'type': 'liability'},
            {'code': '1403', 'name': 'أصول ثابتة أخرى', 'type': 'asset'},
            {'code': '1501', 'name': 'الاستثمارات طويلة الأجل', 'type': 'asset'},
            {'code': '1502', 'name': 'استثمارات أخرى طويلة الأجل', 'type': 'asset'},
            {'code': '1601', 'name': 'أصول ضريبية مؤجلة', 'type': 'asset'},

            # المطلوبات المتداولة (Current Liabilities)
            {'code': '2030', 'name': 'ضريبة القيمة المضافة مستحقة الدفع', 'type': 'liability'},
            {'code': '2101', 'name': 'حسابات الموردين', 'type': 'liability'},
            {'code': '2102', 'name': 'حسابات دائنة أخرى', 'type': 'liability'},
            {'code': '2103', 'name': 'حسابات دائنة متنوعة', 'type': 'liability'},
            {'code': '2201', 'name': 'القروض قصيرة الأجل', 'type': 'liability'},
            {'code': '2301', 'name': 'الضرائب المستحقة', 'type': 'liability'},
            {'code': '2302', 'name': 'ضرائب أخرى مستحقة', 'type': 'liability'},
            {'code': '2401', 'name': 'الفوائد المستحقة الدفع', 'type': 'liability'},
            {'code': '2402', 'name': 'فوائد أخرى مستحقة', 'type': 'liability'},
            {'code': '2501', 'name': 'احتياطيات', 'type': 'liability'},
            {'code': '2503', 'name': 'مطلوبات متداولة أخرى', 'type': 'liability'},

            # المطلوبات طويلة الأجل (Long-term Liabilities)
            {'code': '2202', 'name': 'القروض طويلة الأجل', 'type': 'liability'},
            {'code': '2502', 'name': 'التزامات ضريبية مؤجلة', 'type': 'liability'},

            # حقوق الملكية (Equity)
            {'code': '301', 'name': 'رأس المال', 'type': 'equity'},
            {'code': '305', 'name': 'الأرباح المحتجزة', 'type': 'equity'},
            {'code': '3101', 'name': 'الأرباح والخسائر', 'type': 'equity'},
            {'code': '3102', 'name': 'صافي الربح أو الخسارة', 'type': 'equity'},
            {'code': '3202', 'name': 'احتياطيات', 'type': 'equity'},
            {'code': '3203', 'name': 'أرباح متراكمة', 'type': 'equity'},
            {'code': '3204', 'name': 'خسائر متراكمة', 'type': 'equity'},

            # الإيرادات (Revenues)
            {'code': '401', 'name': 'المبيعات', 'type': 'revenue'},
            {'code': '4011', 'name': 'إيرادات الفوائد البنكية', 'type': 'revenue'},
            {'code': '4012', 'name': 'إيرادات أخرى', 'type': 'revenue'},
            {'code': '4022', 'name': 'إيرادات الخصم المستلم', 'type': 'revenue'},
            {'code': '403', 'name': 'إيرادات أخرى', 'type': 'revenue'},
            {'code': '404', 'name': 'إيرادات تشغيلية أخرى', 'type': 'revenue'},
            {'code': '4099', 'name': 'إيرادات متنوعة', 'type': 'revenue'},

            # المصروفات (Expenses)
            {'code': '501', 'name': 'تكلفة المبيعات', 'type': 'expense'},
            {'code': '5011', 'name': 'مصاريف الرسوم البنكية', 'type': 'expense'},
            {'code': '5012', 'name': 'مصروفات أخرى', 'type': 'expense'},
            {'code': '502', 'name': 'المصروفات الإدارية', 'type': 'expense'},
            {'code': '5021', 'name': 'مصاريف الديون المعدومة', 'type': 'expense'},
            {'code': '5022', 'name': 'مصاريف الخصم المسموح', 'type': 'expense'},
            {'code': '5023', 'name': 'مصروفات إدارية أخرى', 'type': 'expense'},
            {'code': '503', 'name': 'المصروفات البيعية', 'type': 'expense'},
            {'code': '5031', 'name': 'مصروفات بيعية أخرى', 'type': 'expense'},
            {'code': '504', 'name': 'مصروف الفوائد', 'type': 'expense'},
            {'code': '505', 'name': 'مصروف الضرائب', 'type': 'expense'},
            {'code': '506', 'name': 'مصروف الإهلاك', 'type': 'expense'},
            {'code': '507', 'name': 'مصروفات أخرى', 'type': 'expense'},
            {'code': '5099', 'name': 'مصاريف متنوعة', 'type': 'expense'},

            # المشتريات (Purchases)
            {'code': '6101', 'name': 'مشتريات البضائع', 'type': 'purchases'},

            # المبيعات (Sales)
            {'code': '7101', 'name': 'مردودات ومسموحات المبيعات', 'type': 'sales'},
        ]

        created_count = 0
        for account_data in accounts_data:
            account, created = Account.objects.get_or_create(
                code=account_data['code'],
                defaults={
                    'name': account_data['name'],
                    'account_type': account_data['type'],
                    'description': f'حساب أساسي - {account_data["name"]}',
                    'is_active': True
                }
            )
            # تحديث النوع إذا كان مختلف
            if not created and account.account_type != account_data['type']:
                account.account_type = account_data['type']
                account.save(update_fields=['account_type'])
                self.stdout.write(
                    self.style.WARNING(f'تم تحديث نوع الحساب: {account.code} - {account.name} إلى {account_data["type"]}')
                )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'تم إنشاء الحساب: {account.code} - {account.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'الحساب موجود بالفعل: {account.code} - {account.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'تم إنشاء {created_count} حساب أساسي جديد')
        )
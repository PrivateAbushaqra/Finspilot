from django.core.management.base import BaseCommand
from journal.models import Account

class Command(BaseCommand):
    help = 'إنشاء الحسابات المحاسبية الأساسية حسب IFRS'

    def handle(self, *args, **options):
        # الحسابات الأساسية حسب IFRS - شاملة ومتوافقة
        accounts_data = [
            # ========== الأصول المتداولة (Current Assets) - 1xxx ==========
            
            # النقد وما في حكمه (10xx)
            {'code': '10', 'name': 'النقد وما في حكمه', 'type': 'asset', 'parent': None},
            {'code': '101', 'name': 'النقد في الصندوق', 'type': 'asset', 'parent': '10'},
            {'code': '1010', 'name': 'الصندوق', 'type': 'asset', 'parent': '101'},
            {'code': '102', 'name': 'الحسابات البنكية', 'type': 'asset', 'parent': '10'},
            
            # الاستثمارات قصيرة الأجل (103x)
            {'code': '103', 'name': 'الاستثمارات قصيرة الأجل', 'type': 'asset', 'parent': '10'},
            {'code': '1031', 'name': 'استثمارات قصيرة أخرى', 'type': 'asset', 'parent': '103'},
            
            # الدفعات المقدمة (104x)
            {'code': '104', 'name': 'الدفعات المقدمة', 'type': 'asset', 'parent': '10'},
            {'code': '1041', 'name': 'دفعات مقدمة أخرى', 'type': 'asset', 'parent': '104'},
            
            # ضريبة القيمة المضافة المدخلة (107x)
            {'code': '1070', 'name': 'ضريبة القيمة المضافة مدخلة', 'type': 'asset', 'parent': '10'},
            
            # أصول متداولة أخرى (11xx)
            {'code': '1101', 'name': 'أصول متداولة أخرى', 'type': 'asset', 'parent': '10'},
            
            # المخزون (12xx)
            {'code': '12', 'name': 'المخزون', 'type': 'asset', 'parent': None},
            {'code': '1020', 'name': 'المخزون العام', 'type': 'asset', 'parent': '12'},
            {'code': '1201', 'name': 'مخزون المستودعات', 'type': 'asset', 'parent': '12'},
            
            # حسابات العملاء (13xx)
            {'code': '1301', 'name': 'حسابات العملاء', 'type': 'asset', 'parent': None},
            {'code': '1302', 'name': 'حسابات مدينة أخرى', 'type': 'asset', 'parent': None},
            {'code': '1303', 'name': 'حسابات مدينة متنوعة', 'type': 'asset', 'parent': None},
            
            # ذمم مدينة أخرى (14xx)
            {'code': '14', 'name': 'ذمم مدينة أخرى', 'type': 'asset', 'parent': None},
            {'code': '141', 'name': 'ضريبة القيمة المضافة مدخلة', 'type': 'asset', 'parent': '14'},
            
            # الشيكات والأدوات المالية قصيرة الأجل (15xx)
            {'code': '15', 'name': 'أدوات مالية قصيرة الأجل', 'type': 'asset', 'parent': None},
            {'code': '150', 'name': 'أوراق مالية قصيرة الأجل', 'type': 'asset', 'parent': '15'},
            {'code': '1501', 'name': 'شيكات تحت التحصيل', 'type': 'asset', 'parent': '15'},
            {'code': '1502', 'name': 'أوراق قبض', 'type': 'asset', 'parent': '15'},
            
            # ========== الأصول غير المتداولة (Non-current Assets) - 14xx-16xx ==========
            
            # الأصول الثابتة (140x)
            {'code': '1401', 'name': 'الأصول الثابتة', 'type': 'asset', 'parent': None},
            {'code': '1402', 'name': 'الإهلاك المتراكم', 'type': 'contra_asset', 'parent': None},
            {'code': '1403', 'name': 'أصول ثابتة أخرى', 'type': 'asset', 'parent': None},
            
            # الاستثمارات طويلة الأجل (151x)
            {'code': '1510', 'name': 'الاستثمارات طويلة الأجل', 'type': 'asset', 'parent': None},
            {'code': '1511', 'name': 'استثمارات أخرى طويلة الأجل', 'type': 'asset', 'parent': '1510'},
            
            # أصول ضريبية مؤجلة (16xx)
            {'code': '1601', 'name': 'أصول ضريبية مؤجلة', 'type': 'asset', 'parent': None},
            
            # ========== المطلوبات المتداولة (Current Liabilities) - 2xxx ==========
            
            # حسابات الموردين (21xx)
            {'code': '2101', 'name': 'حسابات الموردين', 'type': 'liability', 'parent': None},
            {'code': '2102', 'name': 'حسابات دائنة أخرى', 'type': 'liability', 'parent': None},
            {'code': '2103', 'name': 'حسابات دائنة متنوعة', 'type': 'liability', 'parent': None},
            
            # الشيكات والأدوات المالية قصيرة الأجل - المطلوبات (22xx)
            {'code': '22', 'name': 'التزامات متداولة أخرى', 'type': 'liability', 'parent': None},
            {'code': '2201', 'name': 'شيكات تحت الصرف', 'type': 'liability', 'parent': '22'},
            {'code': '2202', 'name': 'أوراق دفع قصيرة الأجل', 'type': 'liability', 'parent': '22'},
            
            # ضريبة القيمة المضافة والضرائب (203x-23xx)
            {'code': '2030', 'name': 'الضرائب المستحقة الدفع', 'type': 'liability', 'parent': None},
            {'code': '203001', 'name': 'ضريبة القيمة المضافة مستحقة الدفع', 'type': 'liability', 'parent': '2030'},
            {'code': '2301', 'name': 'الضرائب المستحقة', 'type': 'liability', 'parent': None},
            {'code': '2302', 'name': 'ضرائب أخرى مستحقة', 'type': 'liability', 'parent': None},
            
            # الفوائد والاحتياطيات (24xx-25xx)
            {'code': '2401', 'name': 'الفوائد المستحقة الدفع', 'type': 'liability', 'parent': None},
            {'code': '2402', 'name': 'فوائد أخرى مستحقة', 'type': 'liability', 'parent': None},
            {'code': '2501', 'name': 'احتياطيات قصيرة الأجل', 'type': 'liability', 'parent': None},
            {'code': '2503', 'name': 'مطلوبات متداولة أخرى', 'type': 'liability', 'parent': None},
            
            # ========== المطلوبات طويلة الأجل (Long-term Liabilities) - 26xx-27xx ==========
            
            {'code': '2601', 'name': 'القروض طويلة الأجل', 'type': 'liability', 'parent': None},
            {'code': '2502', 'name': 'التزامات ضريبية مؤجلة', 'type': 'liability', 'parent': None},
            
            # ========== حقوق الملكية (Equity) - 3xxx ==========
            
            # رأس المال (301x)
            {'code': '301', 'name': 'رأس المال', 'type': 'equity', 'parent': None},
            {'code': '30101', 'name': 'رأس المال المصرح به', 'type': 'equity', 'parent': '301'},
            {'code': '30102', 'name': 'رأس المال المدفوع', 'type': 'equity', 'parent': '301'},
            {'code': '30103', 'name': 'مساهمات إضافية', 'type': 'equity', 'parent': '301'},
            
            # الأرباح المحتجزة (305x-31xx-32xx)
            {'code': '305', 'name': 'الأرباح المحتجزة', 'type': 'equity', 'parent': None},
            {'code': '3101', 'name': 'الأرباح والخسائر', 'type': 'equity', 'parent': None},
            {'code': '3102', 'name': 'صافي الربح أو الخسارة', 'type': 'equity', 'parent': None},
            {'code': '3202', 'name': 'احتياطيات', 'type': 'equity', 'parent': None},
            {'code': '3203', 'name': 'أرباح متراكمة', 'type': 'equity', 'parent': None},
            {'code': '3204', 'name': 'خسائر متراكمة', 'type': 'equity', 'parent': None},
            
            # ========== الإيرادات (Revenues) - 4xxx ==========
            
            {'code': '40', 'name': 'الإيرادات', 'type': 'revenue', 'parent': None},
            {'code': '4010', 'name': 'المبيعات', 'type': 'revenue', 'parent': '40'},
            {'code': '4011', 'name': 'إيرادات الفوائد البنكية', 'type': 'revenue', 'parent': '40'},
            {'code': '4012', 'name': 'إيرادات أخرى', 'type': 'revenue', 'parent': '40'},
            
            # الخصومات والمسموحات (42xx)
            {'code': '42', 'name': 'خصومات ومسموحات المبيعات', 'type': 'expense', 'parent': None},
            {'code': '4020', 'name': 'خصم المبيعات', 'type': 'expense', 'parent': '42'},
            {'code': '4022', 'name': 'إيرادات الخصم المستلم', 'type': 'revenue', 'parent': '40'},
            
            {'code': '403', 'name': 'إيرادات أخرى', 'type': 'revenue', 'parent': None},
            {'code': '404', 'name': 'إيرادات تشغيلية أخرى', 'type': 'revenue', 'parent': None},
            {'code': '4099', 'name': 'إيرادات متنوعة', 'type': 'revenue', 'parent': None},
            
            # ========== المصروفات (Expenses) - 5xxx ==========
            
            # تكلفة المبيعات والمشتريات (50xx)
            {'code': '50', 'name': 'تكلفة المبيعات والمشتريات', 'type': 'expense', 'parent': None},
            {'code': '501', 'name': 'تكلفة المبيعات', 'type': 'expense', 'parent': '50'},
            {'code': '5001', 'name': 'تكلفة البضاعة المباعة', 'type': 'expense', 'parent': '50'},
            {'code': '5011', 'name': 'مصاريف الرسوم البنكية', 'type': 'expense', 'parent': '50'},
            {'code': '5012', 'name': 'مصروفات أخرى', 'type': 'expense', 'parent': '50'},
            
            # المصروفات الإدارية (502x)
            {'code': '502', 'name': 'المصروفات الإدارية', 'type': 'expense', 'parent': None},
            {'code': '5021', 'name': 'مصاريف الديون المعدومة', 'type': 'expense', 'parent': '502'},
            {'code': '5022', 'name': 'مصاريف الخصم المسموح', 'type': 'expense', 'parent': '502'},
            {'code': '5023', 'name': 'مصروفات إدارية أخرى', 'type': 'expense', 'parent': '502'},
            
            # المصروفات البيعية (503x)
            {'code': '503', 'name': 'المصروفات البيعية', 'type': 'expense', 'parent': None},
            {'code': '5031', 'name': 'مصروفات بيعية أخرى', 'type': 'expense', 'parent': '503'},
            
            # مصاريف أخرى (504x-507x)
            {'code': '504', 'name': 'مصروف الفوائد', 'type': 'expense', 'parent': None},
            {'code': '505', 'name': 'مصروف الضرائب', 'type': 'expense', 'parent': None},
            {'code': '506', 'name': 'مصروف الإهلاك', 'type': 'expense', 'parent': None},
            {'code': '507', 'name': 'مصروفات أخرى', 'type': 'expense', 'parent': None},
            {'code': '5099', 'name': 'مصاريف متنوعة', 'type': 'expense', 'parent': None},
            
            # المصاريف العمومية والإدارية (60xx)
            {'code': '60', 'name': 'المصاريف العمومية والإدارية', 'type': 'expense', 'parent': None},
            {'code': '6010', 'name': 'المصاريف العامة', 'type': 'expense', 'parent': '60'},
            
            # ========== المشتريات (Purchases) - 61xx ==========
            
            {'code': '6101', 'name': 'مشتريات البضائع', 'type': 'purchases', 'parent': None},
            
            # ========== مردودات ومسموحات (71xx) ==========
            
            {'code': '7101', 'name': 'مردودات ومسموحات المبيعات', 'type': 'revenue', 'parent': None},
        ]

        # إنشاء الحسابات
        created_count = 0
        updated_count = 0
        
        # أولاً، إنشاء جميع الحسابات بدون parent
        accounts_by_code = {}
        for account_data in accounts_data:
            code = account_data['code']
            account, created = Account.objects.get_or_create(
                code=code,
                defaults={
                    'name': account_data['name'],
                    'account_type': account_data['type'],
                    'description': f'حساب أساسي - {account_data["name"]} (IFRS)',
                    'is_active': True
                }
            )
            accounts_by_code[code] = account
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ تم إنشاء الحساب: {code} - {account.name}')
                )
            else:
                # تحديث النوع إذا كان مختلفاً
                if account.account_type != account_data['type']:
                    account.account_type = account_data['type']
                    account.save(update_fields=['account_type'])
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'⟳ تم تحديث نوع الحساب: {code} - {account.name} إلى {account_data["type"]}')
                    )
        
        # ثانياً، تحديث العلاقات parent
        for account_data in accounts_data:
            if account_data['parent']:
                code = account_data['code']
                parent_code = account_data['parent']
                
                if code in accounts_by_code and parent_code in accounts_by_code:
                    account = accounts_by_code[code]
                    parent = accounts_by_code[parent_code]
                    
                    if account.parent != parent:
                        account.parent = parent
                        account.save(update_fields=['parent'])
                        self.stdout.write(
                            self.style.SUCCESS(f'↳ تم ربط الحساب {code} بالحساب الأب {parent_code}')
                        )

        self.stdout.write(
            self.style.SUCCESS(f'\n✅ اكتمل إنشاء الحسابات الأساسية:')
        )
        self.stdout.write(
            self.style.SUCCESS(f'   - حسابات جديدة: {created_count}')
        )
        if updated_count > 0:
            self.stdout.write(
                self.style.WARNING(f'   - حسابات محدّثة: {updated_count}')
            )
        self.stdout.write(
            self.style.SUCCESS(f'   - إجمالي الحسابات: {len(accounts_data)}')
        )
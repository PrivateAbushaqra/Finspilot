import os
import django
import random
import string
from decimal import Decimal

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.contrib.auth.models import User as DjangoUser, Group, Permission
from django.contrib.contenttypes.models import ContentType
from users.models import User, UserGroup, UserGroupMembership
from cashboxes.models import Cashbox
from banks.models import BankAccount
from customers.models import CustomerSupplier
from journal.models import Account
from products.models import Category, Product

def random_string(length=10):
    """إنشاء نص عشوائي"""
    letters = string.ascii_letters + 'ابتثجحخدذرزسشصضطظعغفقكلمنهوي'
    return ''.join(random.choice(letters) for i in range(length))

def random_phone():
    """إنشاء رقم هاتف عشوائي"""
    return f"07{random.randint(70000000, 99999999)}"

def random_email(name):
    """إنشاء بريد إلكتروني عشوائي"""
    domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
    return f"{name.lower().replace(' ', '_')}@{random.choice(domains)}"

def random_address():
    """إنشاء عنوان عشوائي"""
    cities = ['عمان', 'إربد', 'الزرقاء', 'العقبة', 'الكرك', 'معان', 'الطفيلة', 'السلط', 'مادبا', 'جرش']
    streets = ['شارع الملك عبدالله', 'شارع المدينة', 'شارع الجامعة', 'شارع الصناعة', 'شارع التجارة']
    return f"{random.choice(streets)} {random.randint(1, 200)}, {random.choice(cities)}"

def create_users():
    """إنشاء المستخدمين مع الصلاحيات"""
    print("إنشاء المستخدمين...")

    # إنشاء مجموعات المستخدمين
    groups_data = {
        'مدير_عام': {
            'permissions': ['can_access_system_management', 'can_manage_users', 'can_view_audit_logs',
                          'can_access_sales', 'can_access_inventory', 'can_access_products',
                          'can_access_banks', 'can_access_cashboxes', 'can_access_pos',
                          'can_access_company_settings', 'can_delete_invoices', 'can_delete_accounts',
                          'can_edit_dates', 'can_edit_invoice_numbers']
        },
        'مدير_مبيعات': {
            'permissions': ['can_access_sales', 'can_access_inventory', 'can_access_products',
                          'can_view_reports', 'can_export_reports']
        },
        'محاسب': {
            'permissions': ['can_access_accounts', 'can_access_banks', 'can_access_cashboxes',
                          'can_view_journal', 'can_add_journal_entries', 'can_edit_journal_entries']
        },
        'موظف_مبيعات': {
            'permissions': ['can_access_sales', 'can_add_sales_invoices']
        },
        'أمين_صندوق': {
            'permissions': ['can_access_cashboxes', 'can_access_receipts', 'can_access_payments']
        }
    }

    groups = {}
    for group_name, data in groups_data.items():
        group, created = UserGroup.objects.get_or_create(
            name=group_name,
            defaults={'description': f'مجموعة {group_name}'}
        )
        if created:
            permissions = {}
            for perm in data['permissions']:
                permissions[perm] = ['view', 'add', 'change', 'delete']
            group.permissions = permissions
            group.save()
        groups[group_name] = group

    # إنشاء المستخدمين
    users_data = [
        {'username': 'admin', 'first_name': 'مدير', 'last_name': 'عام', 'user_type': 'superadmin', 'group': 'مدير_عام'},
        {'username': 'sales_manager', 'first_name': 'مدير', 'last_name': 'مبيعات', 'user_type': 'admin', 'group': 'مدير_مبيعات'},
        {'username': 'accountant', 'first_name': 'محاسب', 'last_name': 'رئيسي', 'user_type': 'user', 'group': 'محاسب'},
        {'username': 'sales_rep', 'first_name': 'موظف', 'last_name': 'مبيعات', 'user_type': 'user', 'group': 'موظف_مبيعات'},
        {'username': 'cashier', 'first_name': 'أمين', 'last_name': 'صندوق', 'user_type': 'user', 'group': 'أمين_صندوق'}
    ]

    for user_data in users_data:
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'user_type': user_data['user_type'],
                'email': f"{user_data['username']}@example.com",
                'phone': random_phone(),
                'department': user_data.get('group', ''),
                'is_active': True
            }
        )
        if created:
            user.set_password('password123')
            user.save()

        # ربط المستخدم بالمجموعة
        membership, _ = UserGroupMembership.objects.get_or_create(
            user=user,
            group=groups[user_data['group']]
        )

    print("تم إنشاء المستخدمين بنجاح")

def create_cashboxes():
    """إنشاء الصناديق النقدية"""
    print("إنشاء الصناديق النقدية...")

    cashboxes_data = [
        {'name': 'الصندوق الرئيسي', 'description': 'الصندوق النقدي الرئيسي', 'location': 'المكتب الرئيسي'},
        {'name': 'صندوق الشيكات', 'description': 'صندوق خاص بالشيكات', 'location': 'المكتب الرئيسي'}
    ]

    for cb_data in cashboxes_data:
        cashbox, created = Cashbox.objects.get_or_create(
            name=cb_data['name'],
            defaults={
                'description': cb_data['description'],
                'location': cb_data['location'],
                'balance': Decimal('0.000'),
                'currency': 'JOD',
                'is_active': True
            }
        )

    print("تم إنشاء الصناديق النقدية بنجاح")

def create_bank_accounts():
    """إنشاء الحسابات البنكية"""
    print("إنشاء الحسابات البنكية...")

    banks_data = [
        {'name': 'حساب البنك الأهلي', 'bank_name': 'البنك الأهلي الأردني', 'account_number': '1234567890123456'},
        {'name': 'حساب بنك الراجحي', 'bank_name': 'بنك الراجحي', 'account_number': '9876543210987654'}
    ]

    for bank_data in banks_data:
        bank_account, created = BankAccount.objects.get_or_create(
            name=bank_data['name'],
            defaults={
                'bank_name': bank_data['bank_name'],
                'account_number': bank_data['account_number'],
                'iban': f"JO{random.randint(10,99)}{random_string(2).upper()}{random.randint(1000000000000000,9999999999999999)}",
                'swift_code': f"{random_string(4).upper()}{random_string(2).upper()}{random_string(2).upper()}",
                'balance': Decimal('0.000'),
                'initial_balance': Decimal('0.000'),
                'currency': 'JOD',
                'is_active': True,
                'notes': f'حساب بنكي في {bank_data["bank_name"]}'
            }
        )

    print("تم إنشاء الحسابات البنكية بنجاح")

def create_customers():
    """إنشاء العملاء"""
    print("إنشاء العملاء...")

    for i in range(50):
        customer_type = random.choice(['customer', 'both'])
        customer_name = random.choice([
            f"شركة {random_string(8)} التجارية",
            f"{random_string(6)} {random_string(6)}"
        ])
        customer, created = CustomerSupplier.objects.get_or_create(
            name=customer_name,
            defaults={
                'type': customer_type,
                'email': random_email(customer_name),
                'phone': random_phone(),
                'address': random_address(),
                'city': random.choice(['عمان', 'إربد', 'الزرقاء', 'العقبة', 'الكرك']),
                'tax_number': f"TR{random.randint(100000000, 999999999)}",
                'credit_limit': Decimal(str(random.uniform(1000, 50000))),
                'balance': Decimal('0.000'),
                'is_active': True,
                'notes': f"عميل {customer_name} - تم إنشاؤه تلقائياً"
            }
        )

    print("تم إنشاء العملاء بنجاح")

def create_suppliers():
    """إنشاء الموردين"""
    print("إنشاء الموردين...")

    for i in range(10):
        supplier_type = random.choice(['supplier', 'both'])
        supplier_name = f"شركة {random_string(8)} للتجارة"
        supplier, created = CustomerSupplier.objects.get_or_create(
            name=supplier_name,
            defaults={
                'type': supplier_type,
                'email': random_email(supplier_name),
                'phone': random_phone(),
                'address': random_address(),
                'city': random.choice(['عمان', 'إربد', 'الزرقاء', 'العقبة', 'الكرك']),
                'tax_number': f"TS{random.randint(100000000, 999999999)}",
                'credit_limit': Decimal(str(random.uniform(5000, 100000))),
                'balance': Decimal('0.000'),
                'is_active': True,
                'notes': f"مورد {supplier_name} - تم إنشاؤه تلقائياً"
            }
        )

    print("تم إنشاء الموردين بنجاح")

def create_accounts():
    """إنشاء شجرة الحسابات المحاسبية"""
    print("إنشاء شجرة الحسابات...")

    # الحسابات الرئيسية
    main_accounts = [
        {'code': '1', 'name': 'الأصول', 'account_type': 'asset'},
        {'code': '2', 'name': 'الخصوم', 'account_type': 'liability'},
        {'code': '3', 'name': 'حقوق الملكية', 'account_type': 'equity'},
        {'code': '4', 'name': 'الإيرادات', 'account_type': 'revenue'},
        {'code': '5', 'name': 'المصاريف', 'account_type': 'expense'}
    ]

    accounts_dict = {}
    for acc_data in main_accounts:
        account, created = Account.objects.get_or_create(
            code=acc_data['code'],
            defaults={
                'name': acc_data['name'],
                'account_type': acc_data['account_type'],
                'description': f'حساب رئيسي - {acc_data["name"]}',
                'is_active': True,
                'balance': Decimal('0.000')
            }
        )
        accounts_dict[acc_data['code']] = account

    # الأصول
    assets = [
        {'code': '11', 'name': 'الأصول المتداولة', 'parent': '1'},
        {'code': '12', 'name': 'الأصول الثابتة', 'parent': '1'},
        {'code': '1101', 'name': 'النقدية', 'parent': '11'},
        {'code': '1102', 'name': 'البنوك', 'parent': '11'},
        {'code': '1103', 'name': 'الذمم المدينة', 'parent': '11'},
        {'code': '1104', 'name': 'المخزون', 'parent': '11'},
        {'code': '1201', 'name': 'الأصول الثابتة', 'parent': '12'}
    ]

    # الخصوم
    liabilities = [
        {'code': '21', 'name': 'الخصوم المتداولة', 'parent': '2'},
        {'code': '22', 'name': 'الخصوم طويلة الأجل', 'parent': '2'},
        {'code': '2101', 'name': 'الذمم الدائنة', 'parent': '21'},
        {'code': '2102', 'name': 'القروض قصيرة الأجل', 'parent': '21'},
        {'code': '2201', 'name': 'القروض طويلة الأجل', 'parent': '22'}
    ]

    # حقوق الملكية
    equity = [
        {'code': '31', 'name': 'رأس المال', 'parent': '3'},
        {'code': '32', 'name': 'الأرباح المحتجزة', 'parent': '3'}
    ]

    # الإيرادات
    revenues = [
        {'code': '41', 'name': 'إيرادات المبيعات', 'parent': '4'},
        {'code': '42', 'name': 'إيرادات أخرى', 'parent': '4'}
    ]

    # المصاريف
    expenses = [
        {'code': '51', 'name': 'مصاريف تشغيلية', 'parent': '5'},
        {'code': '52', 'name': 'مصاريف إدارية', 'parent': '5'},
        {'code': '53', 'name': 'مصاريف مالية', 'parent': '5'}
    ]

    all_sub_accounts = assets + liabilities + equity + revenues + expenses

    for acc_data in all_sub_accounts:
        parent_code = acc_data['parent']
        if parent_code in accounts_dict:
            parent_account = accounts_dict[parent_code]
        else:
            # البحث عن الحساب الأب
            try:
                parent_account = Account.objects.get(code=parent_code)
                accounts_dict[parent_code] = parent_account
            except Account.DoesNotExist:
                print(f"لم يتم العثور على الحساب الأب {parent_code}")
                continue
        
        account, created = Account.objects.get_or_create(
            code=acc_data['code'],
            defaults={
                'name': acc_data['name'],
                'account_type': parent_account.account_type,
                'parent': parent_account,
                'description': f'حساب فرعي - {acc_data["name"]}',
                'is_active': True,
                'balance': Decimal('0.000')
            }
        )
        accounts_dict[acc_data['code']] = account

    print("تم إنشاء شجرة الحسابات بنجاح")

def create_categories():
    """إنشاء فئات المنتجات"""
    print("إنشاء فئات المنتجات...")

    categories_data = [
        {'name': 'لابتوبات', 'name_en': 'Laptops', 'description': 'أجهزة كمبيوتر محمولة'},
        {'name': 'مكونات الكمبيوتر', 'name_en': 'Computer Components', 'description': 'قطع غيار ومكونات'},
        {'name': 'شاشات', 'name_en': 'Monitors', 'description': 'شاشات العرض'},
        {'name': 'طابعات', 'name_en': 'Printers', 'description': 'أجهزة الطباعة'},
        {'name': 'مستلزمات مكتبية', 'name_en': 'Office Supplies', 'description': 'أدوات ومستلزمات المكتب'},
        {'name': 'أقراص تخزين', 'name_en': 'Storage Devices', 'description': 'أقراص صلبة وفلاش'},
        {'name': 'ملحقات', 'name_en': 'Accessories', 'description': 'ملحقات متنوعة'},
        {'name': 'برمجيات', 'name_en': 'Software', 'description': 'برامج وتطبيقات'},
        {'name': 'شبكات', 'name_en': 'Networking', 'description': 'معدات الشبكات'},
        {'name': 'أجهزة لوحية', 'name_en': 'Tablets', 'description': 'أجهزة لوحية وتابلت'}
    ]

    for cat_data in categories_data:
        category, created = Category.objects.get_or_create(
            name=cat_data['name'],
            defaults={
                'name_en': cat_data['name_en'],
                'description': cat_data['description'],
                'is_active': True
            }
        )

    print("تم إنشاء فئات المنتجات بنجاح")

def create_products():
    """إنشاء المنتجات"""
    print("إنشاء المنتجات...")

    categories = list(Category.objects.all())
    if not categories:
        print("لا توجد فئات، يرجى إنشاء الفئات أولاً")
        return

    for i in range(50):
        category = random.choice(categories)
        cost_price = Decimal(str(random.uniform(50, 2000)))
        profit_margin = Decimal(str(random.uniform(0.2, 0.5)))
        sale_price = cost_price * (1 + profit_margin)
        tax_rate = Decimal(str(random.choice([0, 5, 10, 16])))

        product, created = Product.objects.get_or_create(
            code=f"PRD{random.randint(10000, 99999)}",
            defaults={
                'name': f"{random_string(6)} {random_string(4)}",
                'name_en': f"{random_string(6)} {random_string(4)}",
                'product_type': 'physical',
                'category': category,
                'description': f"منتج {random_string(10)} - تم إنشاؤه تلقائياً",
                'cost_price': cost_price,
                'sale_price': sale_price,
                'wholesale_price': sale_price * Decimal('0.9'),
                'tax_rate': tax_rate,
                'minimum_quantity': Decimal(str(random.randint(1, 10))),
                'is_active': True
            }
        )

    print("تم إنشاء المنتجات بنجاح")

def create_services():
    """إنشاء الخدمات"""
    print("إنشاء الخدمات...")

    # الحصول على فئة الخدمات أو إنشاؤها
    service_category, created = Category.objects.get_or_create(
        name='خدمات الصيانة',
        defaults={
            'name_en': 'Maintenance Services',
            'description': 'خدمات صيانة وإصلاح الأجهزة',
            'is_active': True
        }
    )

    services_data = [
        {'name': 'صيانة لابتوب', 'description': 'صيانة وإصلاح الأجهزة المحمولة'},
        {'name': 'تغيير هارد ديسك', 'description': 'استبدال وتركيب أقراص التخزين'},
        {'name': 'تركيب ذاكرة RAM', 'description': 'إضافة وترقية ذاكرة الوصول العشوائي'},
        {'name': 'صيانة شاشة', 'description': 'إصلاح واستبدال شاشات العرض'},
        {'name': 'صيانة دورية شاملة', 'description': 'فحص وصيانة شاملة للأجهزة'}
    ]

    for service_data in services_data:
        service, created = Product.objects.get_or_create(
            code=f"SVC{random.randint(10000, 99999)}",
            defaults={
                'name': service_data['name'],
                'name_en': service_data['name'] + " Service",
                'product_type': 'service',
                'category': service_category,
                'description': service_data['description'],
                'cost_price': Decimal(str(random.uniform(20, 200))),
                'sale_price': Decimal(str(random.uniform(50, 500))),
                'tax_rate': Decimal('16'),
                'is_active': True
            }
        )

    print("تم إنشاء الخدمات بنجاح")

if __name__ == '__main__':
    print("بدء إنشاء البيانات الأساسية للنظام المحاسبي...")

    try:
        create_users()
        create_cashboxes()
        create_bank_accounts()
        create_customers()
        create_suppliers()
        create_accounts()
        create_categories()
        create_products()
        create_services()

        print("تم إنشاء جميع البيانات الأساسية بنجاح!")

    except Exception as e:
        print(f"حدث خطأ: {e}")
        import traceback
        traceback.print_exc()
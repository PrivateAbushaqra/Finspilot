"""
Script مصحح لإضافة بيانات تجريبية لوحدة HR
يجب تشغيله من Django shell: python manage.py shell < hr_sample_data_fixed.py
"""

from django.contrib.auth.models import User
from hr.models import Department, Position, Employee, LeaveType
from datetime import date, timedelta

# إنشاء الأقسام
departments_data = [
    {'name': 'الموارد البشرية', 'code': 'HR', 'description': 'إدارة شؤون الموظفين'},
    {'name': 'المحاسبة', 'code': 'ACC', 'description': 'إدارة الشؤون المالية'},
    {'name': 'تقنية المعلومات', 'code': 'IT', 'description': 'إدارة الأنظمة التقنية'},
    {'name': 'المبيعات', 'code': 'SALES', 'description': 'إدارة المبيعات والعملاء'},
    {'name': 'الإدارة العامة', 'code': 'ADMIN', 'description': 'الإدارة التنفيذية'},
]

print("إنشاء الأقسام...")
for dept_data in departments_data:
    dept, created = Department.objects.get_or_create(
        code=dept_data['code'],
        defaults={
            'name': dept_data['name'],
            'description': dept_data['description']
        }
    )
    if created:
        print(f"تم إنشاء قسم: {dept.name}")
    else:
        print(f"قسم موجود: {dept.name}")

# إنشاء المناصب
positions_data = [
    {'title': 'مدير عام', 'code': 'GM', 'department_code': 'ADMIN'},
    {'title': 'مدير الموارد البشرية', 'code': 'HRM', 'department_code': 'HR'},
    {'title': 'محاسب أول', 'code': 'SACC', 'department_code': 'ACC'},
    {'title': 'محاسب', 'code': 'ACC', 'department_code': 'ACC'},
    {'title': 'مطور برمجيات', 'code': 'DEV', 'department_code': 'IT'},
    {'title': 'مدير المبيعات', 'code': 'SM', 'department_code': 'SALES'},
    {'title': 'موظف مبيعات', 'code': 'SALES', 'department_code': 'SALES'},
    {'title': 'موظف موارد بشرية', 'code': 'HR', 'department_code': 'HR'},
]

print("\nإنشاء المناصب...")
for pos_data in positions_data:
    try:
        department = Department.objects.get(code=pos_data['department_code'])
        position, created = Position.objects.get_or_create(
            code=pos_data['code'],
            defaults={
                'title': pos_data['title'],
                'department': department
            }
        )
        if created:
            print(f"تم إنشاء منصب: {position.title}")
        else:
            print(f"منصب موجود: {position.title}")
    except Department.DoesNotExist:
        print(f"خطأ: قسم {pos_data['department_code']} غير موجود")

# إنشاء أنواع الإجازات
leave_types_data = [
    {'name': 'إجازة سنوية', 'max_days_per_year': 30, 'requires_approval': True},
    {'name': 'إجازة مرضية', 'max_days_per_year': 15, 'requires_approval': True},
    {'name': 'إجازة طارئة', 'max_days_per_year': 5, 'requires_approval': True},
    {'name': 'إجازة أمومة', 'max_days_per_year': 90, 'requires_approval': True},
    {'name': 'إجازة حج', 'max_days_per_year': 15, 'requires_approval': True},
]

print("\nإنشاء أنواع الإجازات...")
for leave_data in leave_types_data:
    leave_type, created = LeaveType.objects.get_or_create(
        name=leave_data['name'],
        defaults={
            'max_days_per_year': leave_data['max_days_per_year'],
            'requires_approval': leave_data['requires_approval']
        }
    )
    if created:
        print(f"تم إنشاء نوع إجازة: {leave_type.name}")
    else:
        print(f"نوع إجازة موجود: {leave_type.name}")

# الحصول على مستخدم للربط كصانع البيانات
try:
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.first()
    if not admin_user:
        print("لا يوجد مستخدمين في النظام!")
        exit()
except Exception as e:
    print(f"خطأ في الحصول على مستخدم: {e}")
    exit()

# إنشاء موظفين تجريبيين
employees_data = [
    {
        'first_name': 'أحمد',
        'last_name': 'محمد',
        'employee_id': 'EMP001',
        'national_id': '1234567890',
        'email': 'ahmed.mohamed@company.com',
        'phone': '+966501234567',
        'birth_date': date(1985, 5, 15),
        'gender': 'M',
        'marital_status': 'married',
        'employment_type': 'full_time',
        'department_code': 'ADMIN',
        'position_code': 'GM',
        'basic_salary': 15000.000,
        'address': 'الرياض، السعودية',
    },
    {
        'first_name': 'فاطمة',
        'last_name': 'علي',
        'employee_id': 'EMP002',
        'national_id': '1234567891',
        'email': 'fatima.ali@company.com',
        'phone': '+966501234568',
        'birth_date': date(1988, 8, 20),
        'gender': 'F',
        'marital_status': 'single',
        'employment_type': 'full_time',
        'department_code': 'HR',
        'position_code': 'HRM',
        'basic_salary': 12000.000,
        'address': 'جدة، السعودية',
    },
    {
        'first_name': 'خالد',
        'last_name': 'السعودي',
        'employee_id': 'EMP003',
        'national_id': '1234567892',
        'email': 'khalid.saudi@company.com',
        'phone': '+966501234569',
        'birth_date': date(1982, 12, 10),
        'gender': 'M',
        'marital_status': 'married',
        'employment_type': 'full_time',
        'department_code': 'ACC',
        'position_code': 'SACC',
        'basic_salary': 10000.000,
        'address': 'الدمام، السعودية',
    },
    {
        'first_name': 'نورا',
        'last_name': 'أحمد',
        'employee_id': 'EMP004',
        'national_id': '1234567893',
        'email': 'nora.ahmed@company.com',
        'phone': '+966501234570',
        'birth_date': date(1990, 3, 25),
        'gender': 'F',
        'marital_status': 'single',
        'employment_type': 'full_time',
        'department_code': 'IT',
        'position_code': 'DEV',
        'basic_salary': 8000.000,
        'address': 'الرياض، السعودية',
    },
]

print("\nإنشاء الموظفين...")
for emp_data in employees_data:
    try:
        department = Department.objects.get(code=emp_data['department_code'])
        position = Position.objects.get(code=emp_data['position_code'])
        
        employee, created = Employee.objects.get_or_create(
            employee_id=emp_data['employee_id'],
            defaults={
                'first_name': emp_data['first_name'],
                'last_name': emp_data['last_name'],
                'national_id': emp_data['national_id'],
                'email': emp_data['email'],
                'phone': emp_data['phone'],
                'birth_date': emp_data['birth_date'],
                'gender': emp_data['gender'],
                'marital_status': emp_data['marital_status'],
                'employment_type': emp_data['employment_type'],
                'department': department,
                'position': position,
                'hire_date': date.today() - timedelta(days=365),  # منذ سنة
                'status': 'active',
                'basic_salary': emp_data['basic_salary'],
                'address': emp_data['address'],
                'created_by': admin_user,
            }
        )
        if created:
            print(f"تم إنشاء موظف: {employee.first_name} {employee.last_name}")
        else:
            print(f"موظف موجود: {employee.first_name} {employee.last_name}")
    except (Department.DoesNotExist, Position.DoesNotExist) as e:
        print(f"خطأ في إنشاء موظف {emp_data['first_name']}: {e}")
    except Exception as e:
        print(f"خطأ عام في إنشاء موظف {emp_data['first_name']}: {e}")

print("\nتم الانتهاء من إنشاء البيانات التجريبية!")
print(f"عدد الأقسام: {Department.objects.count()}")
print(f"عدد المناصب: {Position.objects.count()}")
print(f"عدد الموظفين: {Employee.objects.count()}")
print(f"عدد أنواع الإجازات: {LeaveType.objects.count()}")

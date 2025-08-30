"""
Script نهائي مصحح لإضافة بيانات تجريبية لوحدة HR
"""

from django.contrib.auth import get_user_model
from hr.models import Department, Position, Employee, LeaveType
from datetime import date, timedelta

User = get_user_model()

# إنشاء الأقسام
departments_data = [
    {'name': 'الموارد البشرية', 'code': 'HR01', 'description': 'إدارة شؤون الموظفين'},
    {'name': 'المحاسبة', 'code': 'ACC01', 'description': 'إدارة الشؤون المالية'},
    {'name': 'تقنية المعلومات', 'code': 'IT01', 'description': 'إدارة الأنظمة التقنية'},
    {'name': 'المبيعات', 'code': 'SALES01', 'description': 'إدارة المبيعات والعملاء'},
    {'name': 'الإدارة العامة', 'code': 'ADMIN01', 'description': 'الإدارة التنفيذية'},
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
    {'title': 'مدير عام', 'code': 'GM01', 'department_code': 'ADMIN01'},
    {'title': 'مدير الموارد البشرية', 'code': 'HRM01', 'department_code': 'HR01'},
    {'title': 'محاسب أول', 'code': 'SACC01', 'department_code': 'ACC01'},
    {'title': 'محاسب', 'code': 'ACC01', 'department_code': 'ACC01'},
    {'title': 'مطور برمجيات', 'code': 'DEV01', 'department_code': 'IT01'},
    {'title': 'مدير المبيعات', 'code': 'SM01', 'department_code': 'SALES01'},
    {'title': 'موظف مبيعات', 'code': 'SALES01', 'department_code': 'SALES01'},
    {'title': 'موظف موارد بشرية', 'code': 'HR01', 'department_code': 'HR01'},
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
    {'name': 'إجازة سنوية', 'code': 'ANNUAL', 'days_per_year': 30},
    {'name': 'إجازة مرضية', 'code': 'SICK', 'days_per_year': 15},
    {'name': 'إجازة طارئة', 'code': 'EMERGENCY', 'days_per_year': 5},
    {'name': 'إجازة أمومة', 'code': 'MATERNITY', 'days_per_year': 90},
    {'name': 'إجازة حج', 'code': 'HAJJ', 'days_per_year': 15},
]

print("\nإنشاء أنواع الإجازات...")
for leave_data in leave_types_data:
    leave_type, created = LeaveType.objects.get_or_create(
        code=leave_data['code'],
        defaults={
            'name': leave_data['name'],
            'days_per_year': leave_data['days_per_year'],
            'requires_approval': True
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
    print(f"سيتم استخدام المستخدم: {admin_user.username}")
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
        'department_code': 'ADMIN01',
        'position_code': 'GM01',
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
        'department_code': 'HR01',
        'position_code': 'HRM01',
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
        'department_code': 'ACC01',
        'position_code': 'SACC01',
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
        'department_code': 'IT01',
        'position_code': 'DEV01',
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

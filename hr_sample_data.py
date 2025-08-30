"""
Script لإضافة بيانات تجريبية لوحدة HR
يجب تشغيله من Django shell: python manage.py shell < hr_sample_data.py
"""

from django.contrib.auth.models import User
from hr.models import Department, Position, Employee, LeaveType
from datetime import date, timedelta

# إنشاء الأقسام
departments_data = [
    {'name': 'الموارد البشرية', 'description': 'إدارة شؤون الموظفين'},
    {'name': 'المحاسبة', 'description': 'إدارة الشؤون المالية'},
    {'name': 'تقنية المعلومات', 'description': 'إدارة الأنظمة التقنية'},
    {'name': 'المبيعات', 'description': 'إدارة المبيعات والعملاء'},
    {'name': 'الإدارة العامة', 'description': 'الإدارة التنفيذية'},
]

print("إنشاء الأقسام...")
for dept_data in departments_data:
    dept, created = Department.objects.get_or_create(
        name=dept_data['name'],
        defaults={'description': dept_data['description']}
    )
    if created:
        print(f"تم إنشاء قسم: {dept.name}")
    else:
        print(f"قسم موجود: {dept.name}")

# إنشاء المناصب
positions_data = [
    {'title': 'مدير عام', 'department': 'الإدارة العامة'},
    {'title': 'مدير الموارد البشرية', 'department': 'الموارد البشرية'},
    {'title': 'محاسب أول', 'department': 'المحاسبة'},
    {'title': 'محاسب', 'department': 'المحاسبة'},
    {'title': 'مطور برمجيات', 'department': 'تقنية المعلومات'},
    {'title': 'مدير المبيعات', 'department': 'المبيعات'},
    {'title': 'موظف مبيعات', 'department': 'المبيعات'},
    {'title': 'موظف موارد بشرية', 'department': 'الموارد البشرية'},
]

print("\nإنشاء المناصب...")
for pos_data in positions_data:
    try:
        department = Department.objects.get(name=pos_data['department'])
        position, created = Position.objects.get_or_create(
            title=pos_data['title'],
            department=department
        )
        if created:
            print(f"تم إنشاء منصب: {position.title}")
        else:
            print(f"منصب موجود: {position.title}")
    except Department.DoesNotExist:
        print(f"خطأ: قسم {pos_data['department']} غير موجود")

# إنشاء أنواع الإجازات
leave_types_data = [
    {'name': 'إجازة سنوية', 'days_allowed': 30, 'requires_approval': True},
    {'name': 'إجازة مرضية', 'days_allowed': 15, 'requires_approval': True},
    {'name': 'إجازة طارئة', 'days_allowed': 5, 'requires_approval': True},
    {'name': 'إجازة أمومة', 'days_allowed': 90, 'requires_approval': True},
    {'name': 'إجازة حج', 'days_allowed': 15, 'requires_approval': True},
]

print("\nإنشاء أنواع الإجازات...")
for leave_data in leave_types_data:
    leave_type, created = LeaveType.objects.get_or_create(
        name=leave_data['name'],
        defaults={
            'days_allowed': leave_data['days_allowed'],
            'requires_approval': leave_data['requires_approval']
        }
    )
    if created:
        print(f"تم إنشاء نوع إجازة: {leave_type.name}")
    else:
        print(f"نوع إجازة موجود: {leave_type.name}")

# إنشاء موظفين تجريبيين
employees_data = [
    {
        'first_name': 'أحمد',
        'last_name': 'محمد',
        'employee_id': 'EMP001',
        'email': 'ahmed.mohamed@company.com',
        'phone_number': '+966501234567',
        'department': 'الإدارة العامة',
        'position': 'مدير عام',
    },
    {
        'first_name': 'فاطمة',
        'last_name': 'علي',
        'employee_id': 'EMP002',
        'email': 'fatima.ali@company.com',
        'phone_number': '+966501234568',
        'department': 'الموارد البشرية',
        'position': 'مدير الموارد البشرية',
    },
    {
        'first_name': 'خالد',
        'last_name': 'السعودي',
        'employee_id': 'EMP003',
        'email': 'khalid.saudi@company.com',
        'phone_number': '+966501234569',
        'department': 'المحاسبة',
        'position': 'محاسب أول',
    },
    {
        'first_name': 'نورا',
        'last_name': 'أحمد',
        'employee_id': 'EMP004',
        'email': 'nora.ahmed@company.com',
        'phone_number': '+966501234570',
        'department': 'تقنية المعلومات',
        'position': 'مطور برمجيات',
    },
]

print("\nإنشاء الموظفين...")
for emp_data in employees_data:
    try:
        department = Department.objects.get(name=emp_data['department'])
        position = Position.objects.get(title=emp_data['position'])
        
        employee, created = Employee.objects.get_or_create(
            employee_id=emp_data['employee_id'],
            defaults={
                'first_name': emp_data['first_name'],
                'last_name': emp_data['last_name'],
                'email': emp_data['email'],
                'phone_number': emp_data['phone_number'],
                'department': department,
                'position': position,
                'date_joined': date.today() - timedelta(days=365),  # منذ سنة
                'is_active': True,
            }
        )
        if created:
            print(f"تم إنشاء موظف: {employee.first_name} {employee.last_name}")
        else:
            print(f"موظف موجود: {employee.first_name} {employee.last_name}")
    except (Department.DoesNotExist, Position.DoesNotExist) as e:
        print(f"خطأ في إنشاء موظف {emp_data['first_name']}: {e}")

print("\nتم الانتهاء من إنشاء البيانات التجريبية!")
print(f"عدد الأقسام: {Department.objects.count()}")
print(f"عدد المناصب: {Position.objects.count()}")
print(f"عدد الموظفين: {Employee.objects.count()}")
print(f"عدد أنواع الإجازات: {LeaveType.objects.count()}")

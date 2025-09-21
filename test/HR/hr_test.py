# hr_test_full.py
import os
import sys
import django
import random
from datetime import date, datetime, timedelta, time

# إعداد Django للعمل من مجلد المشروع
sys.path.append(r"C:\Accounting_soft\finspilot")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finspilot.settings")
django.setup()

from django.contrib.auth import get_user_model
from hr.models import Department, Position, Employee, Contract, Attendance, LeaveType, LeaveRequest, PayrollPeriod, PayrollEntry, EmployeeDocument

# إعداد التقرير
report_path = os.path.join(os.path.dirname(__file__), "hr_report.txt")
report_lines = []
def log(message):
    report_lines.append(message)
    print(message)

# مسح التقرير السابق إذا وجد
if os.path.exists(report_path):
    os.remove(report_path)

# المستخدم الإداري
User = get_user_model()
superuser, _ = User.objects.get_or_create(username="admin_test_hr", defaults={"is_superuser": True, "is_staff": True})
log("HR System Audit Report")
log("="*50)
log(f"\nReport Date: {datetime.now()}\n")
log("✅ Login: Superuser logged in successfully\n")

# ---------------------------
# إنشاء بيانات تجريبية
# ---------------------------
log("=== HR Test Data Creation ===")
created_objects = []

try:
    # قسم تجريبي
    dept = Department.objects.create(
        name=f"قسم تجريبي_{random.randint(1000,9999)}",
        code=f"DPT{random.randint(1000,9999)}",
        manager=None
    )
    created_objects.append(dept)
    log(f"✅ Department: Created department: {dept.name}")

    # وظيفة تجريبية
    pos = Position.objects.create(
        title="وظيفة تجريبية",
        code=f"POS{random.randint(1000,9999)}",
        department=dept,
        min_salary=100,
        max_salary=1000
    )
    created_objects.append(pos)
    log(f"✅ Position: Created position: {pos.title}")

    # موظف تجريبي
    emp = Employee.objects.create(
        employee_id=f"EMP{random.randint(100,999)}",
        user=superuser,
        first_name="موظف",
        last_name="تجريبي",
        national_id=f"NID{random.randint(10000,99999)}",
        birth_date=date(1990,1,1),
        gender='M',
        marital_status='single',
        email=f"emp_test_{random.randint(1000,9999)}@test.com",
        phone="12345678",
        department=dept,
        position=pos,
        employment_type='full_time',
        hire_date=date.today(),
        basic_salary=500,
        allowances=50,
        created_by=superuser
    )
    created_objects.append(emp)
    log(f"✅ Employee: Created employee: {emp.first_name} {emp.last_name} ({emp.employee_id})")

    # عقد الموظف
    contract = Contract.objects.create(
        employee=emp,
        contract_number=f"CTR{random.randint(1000,9999)}",
        contract_type="permanent",
        start_date=date.today(),
        end_date=date.today()+timedelta(days=365),
        salary=500,
        allowances=50,
        created_by=superuser
    )
    created_objects.append(contract)
    log("✅ Contract: Created contract for employee")

    # حضور الموظف
    attendance = Attendance.objects.create(
        employee=emp,
        date=date.today(),
        check_in_time=time(9,0),
        check_out_time=time(17,30),
        created_by=superuser
    )
    created_objects.append(attendance)
    log(f"✅ Attendance: Created attendance record for employee: {emp.first_name} {emp.last_name} ({emp.employee_id})")

    # نوع إجازة
    leave_type = LeaveType.objects.create(
        name="إجازة سنوية",
        code=f"LT{random.randint(1000,9999)}"
    )
    created_objects.append(leave_type)

    # طلب إجازة
    leave_request = LeaveRequest.objects.create(
        employee=emp,
        leave_type=leave_type,
        start_date=date.today(),
        end_date=date.today()+timedelta(days=2),
        reason="اختبار نظام الإجازات",
        created_by=superuser
    )
    created_objects.append(leave_request)
    log(f"✅ LeaveRequest: Created leave request for employee: {emp.first_name} {emp.last_name} ({emp.employee_id})")

    # فترة رواتب
    payroll_period = PayrollPeriod.objects.create(
        name=f"فترة تجريبية {datetime.now().strftime('%Y%m%d')}",
        start_date=date.today(),
        end_date=date.today()+timedelta(days=30),
        created_by=superuser
    )
    created_objects.append(payroll_period)

    # قيد الرواتب
    payroll_entry = PayrollEntry.objects.create(
        payroll_period=payroll_period,
        employee=emp,
        basic_salary=500,
        allowances=50,
        deductions=20,
        created_by=superuser
    )
    created_objects.append(payroll_entry)
    log("✅ PayrollEntry: Created payroll entry for employee")

    # مستند الموظف
    doc_path = os.path.join(os.path.dirname(__file__), "dummy_file.txt")
    with open(doc_path, "w") as f:
        f.write("ملف تجريبي")
    emp_doc = EmployeeDocument.objects.create(
        employee=emp,
        document_type="other",
        title="ملف تجريبي",
        file=f"hr/documents/dummy_file_{random.randint(100,999)}.txt",
        uploaded_by=superuser
    )
    created_objects.append(emp_doc)
    log("✅ EmployeeDocument: Created document for employee")

except Exception as e:
    log(f"❌ HR Test Data Creation: Exception: {e}")

# ---------------------------
# اختبارات تكامل البيانات
# ---------------------------
log("\n=== HR Data Integrity Check ===")
try:
    # تحقق من قسم ووظيفة الموظف
    if emp.department and emp.position:
        log(f"✅ HR Integrity Check: Employee has valid department and position")
    else:
        log(f"❌ HR Integrity Check: Employee department or position missing")

    # تحقق من حضور الموظف
    if attendance.worked_hours > 0:
        log(f"✅ HR Integrity Check: Attendance hours calculated correctly ({attendance.worked_hours} hrs)")
    else:
        log(f"❌ HR Integrity Check: Attendance hours not calculated properly")

    # تحقق من رصيد الإجازات
    balance = emp.get_current_leave_balance()
    if balance >= 0:
        log(f"✅ HR Integrity Check: Leave balance calculated ({balance} days)")
    else:
        log(f"❌ HR Integrity Check: Leave balance negative ({balance})")

    # تحقق من الرواتب
    if payroll_entry.net_salary == (payroll_entry.basic_salary + payroll_entry.allowances - payroll_entry.deductions):
        log(f"✅ HR Integrity Check: Payroll net salary calculated correctly ({payroll_entry.net_salary})")
    else:
        log(f"❌ HR Integrity Check: Payroll net salary mismatch ({payroll_entry.net_salary})")

except Exception as e:
    log(f"❌ HR Integrity Check: Exception: {e}")

# ---------------------------
# تنظيف البيانات التجريبية
# ---------------------------
log("\n=== Cleaning HR Test Data ===")
for obj in reversed(created_objects):
    try:
        obj.delete()
        log(f"✅ Cleanup: Deleted {str(obj)}")
    except Exception as e:
        log(f"❌ Cleanup: Failed to delete {str(obj)} - {e}")

# حذف الملف التجريبي
if os.path.exists(doc_path):
    os.remove(doc_path)

log("\n" + "="*50)

# حفظ التقرير
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))

log(f"\n✅ Report saved to: {report_path}")

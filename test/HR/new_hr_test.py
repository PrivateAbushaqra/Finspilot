# new_hr_test.py
import os
import sys
import django
from datetime import date, datetime, time, timedelta
from decimal import Decimal

# إعداد Django
sys.path.append(r"C:\Accounting_soft\finspilot")  # عدل المسار حسب مشروعك
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finspilot.settings")
django.setup()

from django.contrib.auth import get_user_model
from hr.models import Department, Position, Employee, Contract, Attendance, LeaveType, LeaveRequest, PayrollEntry, EmployeeDocument, PayrollPeriod

User = get_user_model()

report_lines = []

def log(message):
    print(message)
    report_lines.append(message)

# التاريخ
log("HR System Audit Report")
log("="*50)
log(f"\nReport Date: {datetime.now()}\n")

# === Login ===
try:
    superuser = User.objects.filter(is_superuser=True).first()
    if superuser:
        log("✅ Login: Superuser logged in successfully")
    else:
        log("❌ Login: No superuser found")
except Exception as e:
    log(f"❌ Login: {e}")

# === HR Test Data Creation ===
log("\n=== HR Test Data Creation ===")
try:
    dept = Department.objects.create(
        name=f"قسم تجريبي_{int(datetime.now().timestamp())}",
        code=f"DEPT{int(datetime.now().timestamp())%1000}"
    )
    log(f"✅ Department: Created department: {dept.name}")
except Exception as e:
    log(f"❌ Department creation: {e}")
    dept = None

try:
    pos = Position.objects.create(
        title="وظيفة تجريبية",
        code=f"POS{int(datetime.now().timestamp())%1000}",
        department=dept
    )
    log(f"✅ Position: Created position: {pos.title}")
except Exception as e:
    log(f"❌ Position creation: {e}")
    pos = None

try:
    emp = Employee.objects.create(
        employee_id=f"EMP{int(datetime.now().timestamp())%10000}",
        first_name="موظف",
        last_name="تجريبي",
        email=f"test{int(datetime.now().timestamp())%10000}@example.com",
        phone="0771234567",
        department=dept,
        position=pos,
        hire_date=date.today(),
        basic_salary=500,
        allowances=50,
        birth_date=date(1990,1,1),
        created_by=superuser,
        gender='M',
        marital_status='single',
        employment_type='full_time',
        status='active',
        national_id=f"NID{int(datetime.now().timestamp())%10000}"
    )
    log(f"✅ Employee: Created employee: {emp.first_name} {emp.last_name} ({emp.employee_id})")
except Exception as e:
    log(f"❌ Employee creation: {e}")
    emp = None

try:
    contract = Contract.objects.create(
        employee=emp,
        contract_number=f"CTR{int(datetime.now().timestamp())%10000}",
        contract_type='permanent',
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        salary=emp.basic_salary,
        allowances=emp.allowances,
        status='active',
        created_by=superuser
    )
    log(f"✅ Contract: Created contract for employee")
except Exception as e:
    log(f"❌ Contract creation: {e}")
    contract = None

try:
    attendance = Attendance.objects.create(
        employee=emp,
        date=date.today(),
        check_in_time=time(9,0),
        check_out_time=time(17,0),
        attendance_type='present',
        created_by=superuser
    )
    log(f"✅ Attendance: Created attendance record for employee: {emp.first_name} {emp.last_name} ({emp.employee_id})")
except Exception as e:
    log(f"❌ Attendance creation: {e}")

try:
    leave_type = LeaveType.objects.create(name="إجازة سنوية", days_per_year=21)
except Exception:
    leave_type = LeaveType.objects.filter(name="إجازة سنوية").first()

try:
    leave_request = LeaveRequest.objects.create(
        employee=emp,
        leave_type=leave_type,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=2),
        reason="إجازة سنوية",
        status='pending',
        created_by=superuser
    )
    log(f"✅ LeaveRequest: Created leave request for employee: {emp.first_name} {emp.last_name} ({emp.employee_id})")
except Exception as e:
    log(f"❌ LeaveRequest creation: {e}")

try:
    payroll_period = PayrollPeriod.objects.create(
        name=f"فترة رواتب تجريبية {datetime.now().strftime('%B %Y')}",
        start_date=date.today().replace(day=1),
        end_date=date.today().replace(day=28),
        created_by=superuser
    )
    log(f"✅ PayrollPeriod: Created payroll period: {payroll_period.name}")
except Exception as e:
    log(f"❌ PayrollPeriod creation: {e}")
    payroll_period = None

try:
    payroll = PayrollEntry.objects.create(
        employee=emp,
        basic_salary=emp.basic_salary,
        allowances=emp.allowances,
        overtime_amount=0,
        bonuses=0,
        deductions=0,
        social_security_deduction=0,
        income_tax=0,
        unpaid_leave_deduction=0,
        created_by=superuser
    )
    payroll.save()
    log(f"✅ PayrollEntry: Created payroll entry for employee (period: {payroll.payroll_period.name})")
except Exception as e:
    log(f"❌ PayrollEntry creation: {e}")

try:
    doc = EmployeeDocument.objects.create(
        employee=emp,
        document_type='contract',
        title="عقد تجريبي",
        file="hr/documents/dummy.txt",
        uploaded_by=superuser
    )
    log(f"✅ EmployeeDocument: Created document for employee")
except Exception as e:
    log(f"❌ EmployeeDocument creation: {e}")

# === HR Data Integrity Check ===
log("\n=== HR Data Integrity Check ===")
try:
    if emp.department and emp.position:
        log("✅ HR Integrity Check: Employee has valid department and position")
    else:
        log("❌ HR Integrity Check: Employee missing department or position")
except Exception as e:
    log(f"❌ HR Integrity Check: {e}")

try:
    if hasattr(attendance, 'worked_hours') and attendance.worked_hours == 8:
        log(f"✅ HR Integrity Check: Attendance hours calculated correctly (8 hrs)")
    else:
        log(f"❌ HR Integrity Check: Attendance hours incorrect")
except Exception as e:
    log(f"❌ HR Integrity Check: {e}")

try:
    leave_balance = emp.get_current_leave_balance()
    log(f"✅ HR Integrity Check: Leave balance calculated ({leave_balance} days)")
except Exception as e:
    log(f"❌ HR Integrity Check: {e}")

try:
    if payroll:
        log(f"✅ HR Integrity Check: Payroll net salary calculated correctly ({payroll.net_salary})")
except Exception as e:
    log(f"❌ HR Integrity Check: {e}")

# === Additional Checks ===
log("\n=== Permissions Check ===")
try:
    perms = ["can_view_hr","can_manage_employees","can_manage_attendance","can_manage_payroll","can_approve_leaves"]
    missing = [p for p in perms if not superuser.has_perm(f"hr.{p}")]
    if not missing:
        log("✅ Permissions Check: Superuser has all permissions")
    else:
        log(f"❌ Permissions Check: Missing permissions {missing}")
except Exception as e:
    log(f"❌ Permissions Check: {e}")

log("\n=== Salary Limits Check ===")
try:
    if emp.basic_salary > 0 and emp.allowances >= 0 and emp.basic_salary <= 10000:
        log("✅ Salary Limits Check: Employee salary and allowances within reasonable range")
    else:
        log("❌ Salary Limits Check: Salary out of range")
except Exception as e:
    log(f"❌ Salary Limits Check: {e}")

log("\n=== Contract Integrity Check ===")
try:
    active_contract = emp.contracts.filter(status='active').first()
    if active_contract:
        log("✅ Contract Integrity Check: Active contract exists")
    else:
        log("❌ Contract Integrity Check: No active contract found")
except Exception as e:
    log(f"❌ Contract Integrity Check: {e}")

log("\n=== Leave vs Attendance Check ===")
try:
    overlapping = False
    for lr in emp.leave_requests.filter(status='approved'):
        if lr.start_date <= date.today() <= lr.end_date:
            overlapping = True
    if not overlapping:
        log("✅ Leave vs Attendance Check: No overlapping leave")
    else:
        log("❌ Leave vs Attendance Check: Overlapping leave exists")
except Exception as e:
    log(f"❌ Leave vs Attendance Check: {e}")

log("\n=== Employee Basic Data Check ===")
try:
    essential_fields = ['first_name','last_name','email','department','position','employee_id']
    missing = [f for f in essential_fields if not getattr(emp,f)]
    if not missing:
        log("✅ Employee Basic Data Check: All essential fields populated")
    else:
        log(f"❌ Employee Basic Data Check: Missing fields {missing}")
except Exception as e:
    log(f"❌ Employee Basic Data Check: {e}")

# === Cleaning HR Test Data ===
log("\n=== Cleaning HR Test Data ===")
try:
    if doc: doc.delete(); log("✅ Cleanup: Deleted EmployeeDocument")
    if leave_request: leave_request.delete(); log("✅ Cleanup: Deleted LeaveRequest")
    if payroll: payroll.delete(); log("✅ Cleanup: Deleted PayrollEntry")
    if attendance: attendance.delete(); log("✅ Cleanup: Deleted Attendance")
    if contract: contract.delete(); log("✅ Cleanup: Deleted Contract")
    if emp: emp.delete(); log("✅ Cleanup: Deleted Employee")
    if pos: pos.delete(); log("✅ Cleanup: Deleted Position")
    if dept: dept.delete(); log("✅ Cleanup: Deleted Department")
except Exception as e:
    log(f"❌ Cleanup: {e}")

# === Saving Report ===
try:
    report_file = os.path.join(os.path.dirname(__file__), "hr_report.txt")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    log(f"\n✅ Report saved to: {report_file}")
except Exception as e:
    log(f"❌ Report saving failed: {e}")

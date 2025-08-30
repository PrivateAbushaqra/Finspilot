from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from datetime import datetime, date, timedelta
import csv
import io
from decimal import Decimal

from .models import (
    Department, Position, Employee, Contract, Attendance, 
    LeaveType, LeaveRequest, PayrollPeriod, PayrollEntry, EmployeeDocument
)
from .forms import (
    EmployeeForm, ContractForm, AttendanceForm, LeaveRequestForm,
    PayrollPeriodForm, PayrollEntryForm, AttendanceUploadForm,
    DepartmentForm, PositionForm, EmployeeDocumentForm
)
from core.models import AuditLog
from core.utils import get_client_ip


def create_hr_audit_log(request, action_type, content_type_model, object_id, description):
    """دالة مساعدة لإنشاء سجل المراجعة لوحدة HR"""
    try:
        AuditLog.objects.create(
            user=request.user,
            action_type=action_type,
            content_type=ContentType.objects.get_for_model(content_type_model),
            object_id=object_id,
            description=description,
            ip_address=get_client_ip(request),
        )
    except Exception:
        pass


class HRMixin(LoginRequiredMixin):
    """Mixin للتحقق من صلاحيات HR"""
    
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.has_perm('hr.can_view_hr')):
            messages.error(request, _('You do not have permission to access HR module.'))
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)


# Employee Views
class EmployeeListView(HRMixin, ListView):
    model = Employee
    template_name = 'hr/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 20

    def get_queryset(self):
        queryset = Employee.objects.select_related('department', 'position', 'user')
        
        # البحث
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(email__icontains=search)
            )
        
        # التصفية
        department = self.request.GET.get('department')
        if department:
            queryset = queryset.filter(department_id=department)
            
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset.order_by('first_name', 'last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.filter(is_active=True)
        context['status_choices'] = Employee.STATUS_CHOICES
        return context


class EmployeeDetailView(HRMixin, DetailView):
    model = Employee
    template_name = 'hr/employee_detail.html'
    context_object_name = 'employee'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.get_object()
        
        # العقود
        context['contracts'] = employee.contracts.all()[:5]
        
        # الحضور الأخير
        context['recent_attendance'] = employee.attendances.all()[:10]
        
        # طلبات الإجازات الأخيرة
        context['recent_leaves'] = employee.leave_requests.all()[:5]
        
        # كشوف الرواتب الأخيرة
        context['recent_payrolls'] = employee.payroll_entries.all()[:5]
        
        # رصيد الإجازات
        context['leave_balance'] = employee.get_current_leave_balance()
        
        return context


class EmployeeCreateView(HRMixin, PermissionRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    success_url = reverse_lazy('hr:employee_list')
    permission_required = 'hr.can_manage_employees'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        # تسجيل في سجل الأنشطة
        AuditLog.objects.create(
            user=self.request.user,
            action='create',
            model_name='Employee',
            object_id=self.object.id,
            description=f'تم إنشاء موظف جديد: {self.object.full_name}'
        )
        
        messages.success(self.request, _('Employee created successfully.'))
        return response


class EmployeeUpdateView(HRMixin, PermissionRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    success_url = reverse_lazy('hr:employee_list')
    permission_required = 'hr.can_manage_employees'

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # تسجيل في سجل الأنشطة
        AuditLog.objects.create(
            user=self.request.user,
            action='update',
            model_name='Employee',
            object_id=self.object.id,
            description=f'تم تحديث بيانات الموظف: {self.object.full_name}'
        )
        
        messages.success(self.request, _('Employee updated successfully.'))
        return response


class EmployeeDeleteView(HRMixin, PermissionRequiredMixin, DeleteView):
    model = Employee
    template_name = 'hr/employee_confirm_delete.html'
    success_url = reverse_lazy('hr:employee_list')
    permission_required = 'hr.can_manage_employees'

    def delete(self, request, *args, **kwargs):
        employee = self.get_object()
        employee_name = employee.full_name
        
        # تسجيل في سجل الأنشطة
        AuditLog.objects.create(
            user=request.user,
            action='delete',
            model_name='Employee',
            object_id=employee.id,
            description=f'تم حذف الموظف: {employee_name}'
        )
        
        response = super().delete(request, *args, **kwargs)
        messages.success(request, _('Employee deleted successfully.'))
        return response


# Attendance Views
class AttendanceListView(HRMixin, ListView):
    model = Attendance
    template_name = 'hr/attendance_list.html'
    context_object_name = 'attendances'
    paginate_by = 20

    def get_queryset(self):
        queryset = Attendance.objects.select_related('employee', 'employee__department')
        
        # التصفية بالتاريخ
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
            
        # التصفية بالموظف
        employee = self.request.GET.get('employee')
        if employee:
            queryset = queryset.filter(employee_id=employee)
            
        return queryset.order_by('-date', 'employee__first_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = Employee.objects.filter(status='active')
        return context


@login_required
@permission_required('hr.can_manage_attendance')
def attendance_upload(request):
    """رفع ملف الحضور CSV"""
    if request.method == 'POST':
        form = AttendanceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # التحقق من نوع الملف
            if not csv_file.name.endswith('.csv'):
                messages.error(request, _('File must be CSV format.'))
                return render(request, 'hr/attendance_upload.html', {'form': form})
            
            # قراءة الملف
            data_set = csv_file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            next(io_string)  # تخطي العنوان
            
            created_count = 0
            error_count = 0
            
            for column in csv.reader(io_string, delimiter=',', quotechar='"'):
                try:
                    employee_id = column[0]
                    date_str = column[1]
                    check_in = column[2] if column[2] else None
                    check_out = column[3] if column[3] else None
                    
                    # البحث عن الموظف
                    employee = Employee.objects.get(employee_id=employee_id)
                    
                    # تحويل التاريخ
                    attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    # إنشاء سجل الحضور
                    attendance, created = Attendance.objects.get_or_create(
                        employee=employee,
                        date=attendance_date,
                        defaults={
                            'check_in_time': check_in,
                            'check_out_time': check_out,
                            'is_manual_entry': False,
                            'created_by': request.user
                        }
                    )
                    
                    if created:
                        created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    continue
            
            # تسجيل في سجل الأنشطة
            AuditLog.objects.create(
                user=request.user,
                action='upload',
                model_name='Attendance',
                description=f'تم رفع ملف الحضور: {created_count} سجل جديد، {error_count} خطأ'
            )
            
            if created_count > 0:
                messages.success(request, f'تم رفع {created_count} سجل حضور بنجاح.')
            if error_count > 0:
                messages.warning(request, f'فشل في رفع {error_count} سجل.')
                
            return redirect('hr:attendance_list')
    else:
        form = AttendanceUploadForm()
    
    return render(request, 'hr/attendance_upload.html', {'form': form})


# Leave Views
class LeaveRequestListView(HRMixin, ListView):
    model = LeaveRequest
    template_name = 'hr/leave_request_list.html'
    context_object_name = 'leave_requests'
    paginate_by = 20

    def get_queryset(self):
        queryset = LeaveRequest.objects.select_related('employee', 'leave_type')
        
        # التصفية بالحالة
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset.order_by('-created_at')


@login_required
@permission_required('hr.can_approve_leaves')
def approve_leave_request(request, pk):
    """الموافقة على طلب إجازة"""
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            leave_request.status = 'approved'
            leave_request.approved_by = request.user
            leave_request.approval_date = timezone.now()
            leave_request.save()
            
            # تسجيل في سجل الأنشطة
            AuditLog.objects.create(
                user=request.user,
                action='approve',
                model_name='LeaveRequest',
                object_id=leave_request.id,
                description=f'تمت الموافقة على طلب إجازة: {leave_request}'
            )
            
            messages.success(request, _('Leave request approved successfully.'))
            
        elif action == 'reject':
            leave_request.status = 'rejected'
            leave_request.rejection_reason = request.POST.get('rejection_reason', '')
            leave_request.save()
            
            # تسجيل في سجل الأنشطة
            AuditLog.objects.create(
                user=request.user,
                action='reject',
                model_name='LeaveRequest',
                object_id=leave_request.id,
                description=f'تم رفض طلب إجازة: {leave_request}'
            )
            
            messages.success(request, _('Leave request rejected.'))
    
    return redirect('hr:leave_request_list')


# Payroll Views
class PayrollPeriodListView(HRMixin, ListView):
    model = PayrollPeriod
    template_name = 'hr/payroll_period_list.html'
    context_object_name = 'payroll_periods'
    paginate_by = 20


@login_required
@permission_required('hr.can_manage_payroll')
def process_payroll(request, pk):
    """معالجة الرواتب لفترة معينة"""
    payroll_period = get_object_or_404(PayrollPeriod, pk=pk)
    
    if payroll_period.is_processed:
        messages.warning(request, _('Payroll period already processed.'))
        return redirect('hr:payroll_period_list')
    
    if request.method == 'POST':
        # الحصول على جميع الموظفين النشطين
        active_employees = Employee.objects.filter(status='active')
        
        created_count = 0
        
        for employee in active_employees:
            # حساب الراتب الأساسي والبدلات
            basic_salary = employee.basic_salary
            allowances = employee.allowances
            
            # حساب الساعات الإضافية
            overtime_hours = Attendance.objects.filter(
                employee=employee,
                date__range=[payroll_period.start_date, payroll_period.end_date]
            ).aggregate(total_overtime=Sum('overtime_hours'))['total_overtime'] or 0
            
            # حساب مبلغ الساعات الإضافية (مضاعف 1.5)
            hourly_rate = basic_salary / Decimal('160')  # 160 ساعة شهرياً
            overtime_amount = overtime_hours * hourly_rate * Decimal('1.5')
            
            # حساب خصم الضمان الاجتماعي
            social_security_deduction = employee.basic_salary * employee.social_security_rate / 100
            
            # حساب خصم الإجازات غير المدفوعة
            unpaid_leave_days = LeaveRequest.objects.filter(
                employee=employee,
                start_date__range=[payroll_period.start_date, payroll_period.end_date],
                status='approved',
                leave_type__is_paid=False
            ).aggregate(total_days=Sum('days_count'))['total_days'] or 0
            
            daily_rate = basic_salary / 30
            unpaid_leave_deduction = unpaid_leave_days * daily_rate
            
            # إنشاء قيد الراتب
            payroll_entry = PayrollEntry.objects.create(
                payroll_period=payroll_period,
                employee=employee,
                basic_salary=basic_salary,
                allowances=allowances,
                overtime_amount=overtime_amount,
                social_security_deduction=social_security_deduction,
                unpaid_leave_deduction=unpaid_leave_deduction,
                created_by=request.user
            )
            
            created_count += 1
        
        # تحديث حالة الفترة
        payroll_period.is_processed = True
        payroll_period.processed_date = timezone.now()
        payroll_period.processed_by = request.user
        payroll_period.save()
        
        # تسجيل في سجل الأنشطة
        AuditLog.objects.create(
            user=request.user,
            action='process',
            model_name='PayrollPeriod',
            object_id=payroll_period.id,
            description=f'تم معالجة الرواتب للفترة: {payroll_period.name} ({created_count} موظف)'
        )
        
        messages.success(request, f'تم معالجة الرواتب لـ {created_count} موظف بنجاح.')
        return redirect('hr:payroll_period_list')
    
    # عرض معاينة الموظفين
    employees = Employee.objects.filter(status='active')
    return render(request, 'hr/process_payroll.html', {
        'payroll_period': payroll_period,
        'employees': employees
    })


@login_required
@permission_required('hr.can_manage_payroll')
def create_payroll_journal_entries(request, pk):
    """إنشاء قيود المحاسبة للرواتب"""
    payroll_period = get_object_or_404(PayrollPeriod, pk=pk)
    
    if not payroll_period.is_processed:
        messages.error(request, _('Payroll period must be processed first.'))
        return redirect('hr:payroll_period_list')
    
    from journal.models import JournalEntry, JournalEntryLine, Account
    from decimal import Decimal
    
    # البحث عن الحسابات المطلوبة
    try:
        salaries_expense_account = Account.objects.get(name__icontains='رواتب')
        social_security_payable_account = Account.objects.get(name__icontains='ضمان اجتماعي')
        salaries_payable_account = Account.objects.get(name__icontains='رواتب مستحقة')
    except Account.DoesNotExist:
        messages.error(request, _('Required accounts not found. Please create salary related accounts first.'))
        return redirect('hr:payroll_period_list')
    
    # حساب الإجماليات
    payroll_entries = payroll_period.payroll_entries.all()
    total_gross_salary = sum(entry.gross_salary for entry in payroll_entries)
    total_social_security = sum(entry.social_security_deduction for entry in payroll_entries)
    total_net_salary = sum(entry.net_salary for entry in payroll_entries)
    
    # إنشاء القيد
    journal_entry = JournalEntry.objects.create(
        date=payroll_period.end_date,
        description=f'قيد الرواتب للفترة: {payroll_period.name}',
        reference=f'PAYROLL-{payroll_period.id}',
        created_by=request.user
    )
    
    # خط القيد: مصروف الرواتب (مدين)
    JournalEntryLine.objects.create(
        journal_entry=journal_entry,
        account=salaries_expense_account,
        debit=total_gross_salary,
        credit=Decimal('0'),
        description='إجمالي الرواتب'
    )
    
    # خط القيد: الضمان الاجتماعي المستحق (دائن)
    if total_social_security > 0:
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=social_security_payable_account,
            debit=Decimal('0'),
            credit=total_social_security,
            description='الضمان الاجتماعي المستحق'
        )
    
    # خط القيد: الرواتب المستحقة (دائن)
    JournalEntryLine.objects.create(
        journal_entry=journal_entry,
        account=salaries_payable_account,
        debit=Decimal('0'),
        credit=total_net_salary,
        description='صافي الرواتب المستحقة'
    )
    
    # ربط القيد مع قيود الرواتب
    for payroll_entry in payroll_entries:
        payroll_entry.journal_entry = journal_entry
        payroll_entry.save()
    
    # تسجيل في سجل الأنشطة
    AuditLog.objects.create(
        user=request.user,
        action='create',
        model_name='JournalEntry',
        object_id=journal_entry.id,
        description=f'تم إنشاء قيد الرواتب للفترة: {payroll_period.name}'
    )
    
    messages.success(request, _('Payroll journal entries created successfully.'))
    return redirect('hr:payroll_period_list')


# Dashboard
@login_required
def hr_dashboard(request):
    """لوحة تحكم الموارد البشرية"""
    if not (request.user.is_superuser or request.user.has_perm('hr.can_view_hr')):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    context = {
        'total_employees': Employee.objects.filter(status='active').count(),
        'total_departments': Department.objects.filter(is_active=True).count(),
        'pending_leaves': LeaveRequest.objects.filter(status='pending').count(),
        'today_attendances': Attendance.objects.filter(date=date.today()).count(),
        
        # الموظفين الجدد هذا الشهر
        'new_employees': Employee.objects.filter(
            hire_date__year=date.today().year,
            hire_date__month=date.today().month
        ).count(),
        
        # أعياد الميلاد هذا الشهر
        'birthdays_this_month': Employee.objects.filter(
            birth_date__month=date.today().month,
            status='active'
        ).count(),
        
        # الإجازات المطلوبة موافقة
        'recent_leave_requests': LeaveRequest.objects.filter(
            status='pending'
        ).select_related('employee', 'leave_type')[:5],
        
        # احصائيات الحضور اليوم
        'today_attendance_stats': {
            'present': Attendance.objects.filter(date=date.today(), attendance_type='present').count(),
            'absent': Attendance.objects.filter(date=date.today(), attendance_type='absent').count(),
            'late': Attendance.objects.filter(date=date.today(), attendance_type='late').count(),
        }
    }
    
    return render(request, 'hr/dashboard.html', context)


# Department Views
class DepartmentListView(HRMixin, ListView):
    model = Department
    template_name = 'hr/department_list.html'
    context_object_name = 'departments'
    paginate_by = 20


class DepartmentDetailView(HRMixin, DetailView):
    model = Department
    template_name = 'hr/department_detail.html'
    context_object_name = 'department'


class DepartmentCreateView(HRMixin, PermissionRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'hr/department_form.html'
    success_url = reverse_lazy('hr:department_list')
    permission_required = 'hr.can_manage_employees'


class DepartmentUpdateView(HRMixin, PermissionRequiredMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'hr/department_form.html'
    success_url = reverse_lazy('hr:department_list')
    permission_required = 'hr.can_manage_employees'


class DepartmentDeleteView(HRMixin, PermissionRequiredMixin, DeleteView):
    model = Department
    template_name = 'hr/department_confirm_delete.html'
    success_url = reverse_lazy('hr:department_list')
    permission_required = 'hr.can_manage_employees'


# Position Views
class PositionListView(HRMixin, ListView):
    model = Position
    template_name = 'hr/position_list.html'
    context_object_name = 'positions'
    paginate_by = 20


class PositionDetailView(HRMixin, DetailView):
    model = Position
    template_name = 'hr/position_detail.html'
    context_object_name = 'position'


class PositionCreateView(HRMixin, PermissionRequiredMixin, CreateView):
    model = Position
    form_class = PositionForm
    template_name = 'hr/position_form.html'
    success_url = reverse_lazy('hr:position_list')
    permission_required = 'hr.can_manage_employees'


class PositionUpdateView(HRMixin, PermissionRequiredMixin, UpdateView):
    model = Position
    form_class = PositionForm
    template_name = 'hr/position_form.html'
    success_url = reverse_lazy('hr:position_list')
    permission_required = 'hr.can_manage_employees'


class PositionDeleteView(HRMixin, PermissionRequiredMixin, DeleteView):
    model = Position
    template_name = 'hr/position_confirm_delete.html'
    success_url = reverse_lazy('hr:position_list')
    permission_required = 'hr.can_manage_employees'


# Contract Views
class ContractListView(HRMixin, ListView):
    model = Contract
    template_name = 'hr/contract_list.html'
    context_object_name = 'contracts'
    paginate_by = 20


class ContractDetailView(HRMixin, DetailView):
    model = Contract
    template_name = 'hr/contract_detail.html'
    context_object_name = 'contract'


class ContractCreateView(HRMixin, PermissionRequiredMixin, CreateView):
    model = Contract
    form_class = ContractForm
    template_name = 'hr/contract_form.html'
    success_url = reverse_lazy('hr:contract_list')
    permission_required = 'hr.can_manage_employees'


class ContractUpdateView(HRMixin, PermissionRequiredMixin, UpdateView):
    model = Contract
    form_class = ContractForm
    template_name = 'hr/contract_form.html'
    success_url = reverse_lazy('hr:contract_list')
    permission_required = 'hr.can_manage_employees'


class ContractDeleteView(HRMixin, PermissionRequiredMixin, DeleteView):
    model = Contract
    template_name = 'hr/contract_confirm_delete.html'
    success_url = reverse_lazy('hr:contract_list')
    permission_required = 'hr.can_manage_employees'


# Additional Attendance Views
class AttendanceDetailView(HRMixin, DetailView):
    model = Attendance
    template_name = 'hr/attendance_detail.html'
    context_object_name = 'attendance'


class AttendanceCreateView(HRMixin, PermissionRequiredMixin, CreateView):
    model = Attendance
    form_class = AttendanceForm
    template_name = 'hr/attendance_form.html'
    success_url = reverse_lazy('hr:attendance_list')
    permission_required = 'hr.can_manage_attendance'


class AttendanceUpdateView(HRMixin, PermissionRequiredMixin, UpdateView):
    model = Attendance
    form_class = AttendanceForm
    template_name = 'hr/attendance_form.html'
    success_url = reverse_lazy('hr:attendance_list')
    permission_required = 'hr.can_manage_attendance'


class AttendanceDeleteView(HRMixin, PermissionRequiredMixin, DeleteView):
    model = Attendance
    template_name = 'hr/attendance_confirm_delete.html'
    success_url = reverse_lazy('hr:attendance_list')
    permission_required = 'hr.can_manage_attendance'


# Additional Leave Views
class LeaveRequestDetailView(HRMixin, DetailView):
    model = LeaveRequest
    template_name = 'hr/leave_request_detail.html'
    context_object_name = 'leave_request'


class LeaveRequestCreateView(HRMixin, CreateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'hr/leave_request_form.html'
    success_url = reverse_lazy('hr:leave_request_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class LeaveRequestUpdateView(HRMixin, UpdateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'hr/leave_request_form.html'
    success_url = reverse_lazy('hr:leave_request_list')


class LeaveRequestDeleteView(HRMixin, DeleteView):
    model = LeaveRequest
    template_name = 'hr/leave_request_confirm_delete.html'
    success_url = reverse_lazy('hr:leave_request_list')


# Leave Type Views
class LeaveTypeListView(HRMixin, ListView):
    model = LeaveType
    template_name = 'hr/leave_type_list.html'
    context_object_name = 'leave_types'
    paginate_by = 20


class LeaveTypeDetailView(HRMixin, DetailView):
    model = LeaveType
    template_name = 'hr/leave_type_detail.html'
    context_object_name = 'leave_type'


class LeaveTypeCreateView(HRMixin, PermissionRequiredMixin, CreateView):
    model = LeaveType
    fields = ['name', 'days_per_year', 'max_days', 'is_paid', 'is_active', 'notes']
    template_name = 'hr/leave_type_form.html'
    success_url = reverse_lazy('hr:leave_type_list')
    permission_required = 'hr.can_manage_employees'


class LeaveTypeUpdateView(HRMixin, PermissionRequiredMixin, UpdateView):
    model = LeaveType
    fields = ['name', 'days_per_year', 'max_days', 'is_paid', 'is_active', 'notes']
    template_name = 'hr/leave_type_form.html'
    success_url = reverse_lazy('hr:leave_type_list')
    permission_required = 'hr.can_manage_employees'


class LeaveTypeDeleteView(HRMixin, PermissionRequiredMixin, DeleteView):
    model = LeaveType
    template_name = 'hr/leave_type_confirm_delete.html'
    success_url = reverse_lazy('hr:leave_type_list')
    permission_required = 'hr.can_manage_employees'


# Additional Payroll Views
class PayrollPeriodDetailView(HRMixin, DetailView):
    model = PayrollPeriod
    template_name = 'hr/payroll_period_detail.html'
    context_object_name = 'payroll_period'


class PayrollPeriodCreateView(HRMixin, PermissionRequiredMixin, CreateView):
    model = PayrollPeriod
    form_class = PayrollPeriodForm
    template_name = 'hr/payroll_period_form.html'
    success_url = reverse_lazy('hr:payroll_period_list')
    permission_required = 'hr.can_manage_payroll'


class PayrollPeriodUpdateView(HRMixin, PermissionRequiredMixin, UpdateView):
    model = PayrollPeriod
    form_class = PayrollPeriodForm
    template_name = 'hr/payroll_period_form.html'
    success_url = reverse_lazy('hr:payroll_period_list')
    permission_required = 'hr.can_manage_payroll'


class PayrollPeriodDeleteView(HRMixin, PermissionRequiredMixin, DeleteView):
    model = PayrollPeriod
    template_name = 'hr/payroll_period_confirm_delete.html'
    success_url = reverse_lazy('hr:payroll_period_list')
    permission_required = 'hr.can_manage_payroll'


# Payroll Entry Views
class PayrollEntryListView(HRMixin, ListView):
    model = PayrollEntry
    template_name = 'hr/payroll_entry_list.html'
    context_object_name = 'payroll_entries'
    paginate_by = 20


class PayrollEntryDetailView(HRMixin, DetailView):
    model = PayrollEntry
    template_name = 'hr/payroll_entry_detail.html'
    context_object_name = 'payroll_entry'


class PayrollEntryCreateView(HRMixin, PermissionRequiredMixin, CreateView):
    model = PayrollEntry
    form_class = PayrollEntryForm
    template_name = 'hr/payroll_entry_form.html'
    success_url = reverse_lazy('hr:payroll_entry_list')
    permission_required = 'hr.can_manage_payroll'


class PayrollEntryUpdateView(HRMixin, PermissionRequiredMixin, UpdateView):
    model = PayrollEntry
    form_class = PayrollEntryForm
    template_name = 'hr/payroll_entry_form.html'
    success_url = reverse_lazy('hr:payroll_entry_list')
    permission_required = 'hr.can_manage_payroll'


class PayrollEntryDeleteView(HRMixin, PermissionRequiredMixin, DeleteView):
    model = PayrollEntry
    template_name = 'hr/payroll_entry_confirm_delete.html'
    success_url = reverse_lazy('hr:payroll_entry_list')
    permission_required = 'hr.can_manage_payroll'


# Employee Document Views
class EmployeeDocumentListView(HRMixin, ListView):
    model = EmployeeDocument
    template_name = 'hr/employee_document_list.html'
    context_object_name = 'employee_documents'
    paginate_by = 20


class EmployeeDocumentDetailView(HRMixin, DetailView):
    model = EmployeeDocument
    template_name = 'hr/employee_document_detail.html'
    context_object_name = 'employee_document'


class EmployeeDocumentCreateView(HRMixin, CreateView):
    model = EmployeeDocument
    form_class = EmployeeDocumentForm
    template_name = 'hr/employee_document_form.html'
    success_url = reverse_lazy('hr:employee_document_list')


class EmployeeDocumentUpdateView(HRMixin, UpdateView):
    model = EmployeeDocument
    form_class = EmployeeDocumentForm
    template_name = 'hr/employee_document_form.html'
    success_url = reverse_lazy('hr:employee_document_list')


class EmployeeDocumentDeleteView(HRMixin, DeleteView):
    model = EmployeeDocument
    template_name = 'hr/employee_document_confirm_delete.html'
    success_url = reverse_lazy('hr:employee_document_list')


# Report Views
@login_required
def hr_reports(request):
    """تقارير الموارد البشرية"""
    if not (request.user.is_superuser or request.user.has_perm('hr.can_view_hr')):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    return render(request, 'hr/reports.html')


@login_required
def employee_report(request):
    """تقرير الموظفين"""
    employees = Employee.objects.select_related('department', 'position')
    return render(request, 'hr/employee_report.html', {'employees': employees})


@login_required
def attendance_report(request):
    """تقرير الحضور والانصراف"""
    attendances = Attendance.objects.select_related('employee')
    return render(request, 'hr/attendance_report.html', {'attendances': attendances})


@login_required
def payroll_report(request, pk):
    """تقرير كشف الرواتب"""
    payroll_period = get_object_or_404(PayrollPeriod, pk=pk)
    payroll_entries = payroll_period.payroll_entries.select_related('employee')
    
    context = {
        'payroll_period': payroll_period,
        'payroll_entries': payroll_entries,
        'total_gross': sum(entry.gross_salary for entry in payroll_entries),
        'total_deductions': sum(entry.total_deductions for entry in payroll_entries),
        'total_net': sum(entry.net_salary for entry in payroll_entries),
    }
    
    return render(request, 'hr/payroll_report.html', context)


@login_required
def payroll_summary_report(request):
    """تقرير ملخص الرواتب"""
    payroll_periods = PayrollPeriod.objects.prefetch_related('payroll_entries')
    return render(request, 'hr/payroll_summary_report.html', {'payroll_periods': payroll_periods})


@login_required
def leave_balance_report(request):
    """تقرير أرصدة الإجازات"""
    employees = Employee.objects.filter(status='active')
    
    employee_balances = []
    for employee in employees:
        balance = employee.get_current_leave_balance()
        employee_balances.append({
            'employee': employee,
            'balance': balance
        })
    
    return render(request, 'hr/leave_balance_report.html', {'employee_balances': employee_balances})


@login_required
def expiring_documents(request):
    """المستندات المنتهية الصلاحية"""
    from datetime import timedelta
    
    warning_date = date.today() + timedelta(days=30)
    
    expiring_docs = EmployeeDocument.objects.filter(
        expiry_date__lte=warning_date,
        expiry_date__gte=date.today()
    ).select_related('employee')
    
    return render(request, 'hr/expiring_documents.html', {'expiring_docs': expiring_docs})


# API Views
@login_required
def get_positions_by_department(request, department_id):
    """جلب المناصب حسب القسم (AJAX)"""
    positions = Position.objects.filter(department_id=department_id, is_active=True)
    data = [{'id': pos.id, 'title': pos.title} for pos in positions]
    return JsonResponse(data, safe=False)


@login_required
def get_employee_info(request, employee_id):
    """جلب معلومات الموظف (AJAX)"""
    try:
        employee = Employee.objects.get(id=employee_id)
        data = {
            'full_name': employee.full_name,
            'department': employee.department.name,
            'position': employee.position.title,
            'basic_salary': float(employee.basic_salary),
            'allowances': float(employee.allowances),
        }
        return JsonResponse(data)
    except Employee.DoesNotExist:
        return JsonResponse({'error': 'Employee not found'}, status=404)


@login_required
def get_employee_leave_balance(request, employee_id):
    """جلب رصيد إجازات الموظف (AJAX)"""
    try:
        employee = Employee.objects.get(id=employee_id)
        balance = employee.get_current_leave_balance()
        return JsonResponse(balance)
    except Employee.DoesNotExist:
        return JsonResponse({'error': 'Employee not found'}, status=404)


# Report Views
@login_required
def department_report(request):
    """تقرير الموظفين حسب القسم"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    departments = Department.objects.filter(is_active=True).prefetch_related('employees')
    context = {
        'departments': departments,
        'title': _('Employees by Department Report')
    }
    
    # Log activity
    create_hr_audit_log(
        request=request,
        action_type='view',
        content_type_model=Department,
        object_id=None,
        description=_('Viewed department report')
    )
    
    return render(request, 'hr/reports/department_report.html', context)


@login_required
def new_hires_report(request):
    """تقرير الموظفين الجدد"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    new_hires = Employee.objects.filter(hire_date__gte=thirty_days_ago, is_active=True)
    
    context = {
        'new_hires': new_hires,
        'period': thirty_days_ago,
        'title': _('New Hires Report')
    }
    
    # Log activity
    create_hr_audit_log(
        request=request,
        action_type='view',
        content_type_model=Employee,
        object_id=None,
        description=_('Viewed new hires report')
    )
    
    return render(request, 'hr/reports/new_hires_report.html', context)


@login_required
def late_arrivals_report(request):
    """تقرير التأخير"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    from datetime import datetime, time
    late_attendances = Attendance.objects.filter(
        attendance_type='late',
        date__month=datetime.now().month
    ).select_related('employee')
    
    context = {
        'late_attendances': late_attendances,
        'title': _('Late Arrivals Report')
    }
    
    # Log activity
    create_hr_audit_log(
        request=request,
        action_type='view',
        content_type_model=Attendance,
        object_id=None,
        description=_('Viewed late arrivals report')
    )
    
    return render(request, 'hr/reports/late_arrivals_report.html', context)


@login_required
def overtime_report(request):
    """تقرير العمل الإضافي"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    from datetime import datetime
    overtime_records = Attendance.objects.filter(
        overtime_hours__gt=0,
        date__month=datetime.now().month
    ).select_related('employee')
    
    context = {
        'overtime_records': overtime_records,
        'title': _('Overtime Report')
    }
    
    # Log activity
    create_hr_audit_log(
        request=request,
        action_type='view',
        content_type_model=Attendance,
        object_id=None,
        description=_('Viewed overtime report')
    )
    
    return render(request, 'hr/reports/overtime_report.html', context)


@login_required
def leave_summary_report(request):
    """تقرير ملخص الإجازات"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    leave_types = LeaveType.objects.filter(is_active=True)
    leave_requests = LeaveRequest.objects.select_related('employee', 'leave_type')
    
    context = {
        'leave_types': leave_types,
        'leave_requests': leave_requests,
        'title': _('Leave Summary Report')
    }
    
    # Log activity
    create_audit_log(
        user=request.user,
        action_type='view',
        content_type_model=LeaveRequest,
        object_id=None,
        description=_('Viewed leave summary report')
    )
    
    return render(request, 'hr/reports/leave_summary_report.html', context)


@login_required
def upcoming_leaves_report(request):
    """تقرير الإجازات القادمة"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    from datetime import datetime, timedelta
    next_month = datetime.now().date() + timedelta(days=30)
    upcoming_leaves = LeaveRequest.objects.filter(
        start_date__lte=next_month,
        end_date__gte=datetime.now().date(),
        status='approved'
    ).select_related('employee', 'leave_type')
    
    context = {
        'upcoming_leaves': upcoming_leaves,
        'title': _('Upcoming Leaves Report')
    }
    
    # Log activity
    create_audit_log(
        user=request.user,
        action_type='view',
        content_type_model=LeaveRequest,
        object_id=None,
        description=_('Viewed upcoming leaves report')
    )
    
    return render(request, 'hr/reports/upcoming_leaves_report.html', context)


@login_required
def salary_breakdown_report(request):
    """تقرير تفصيل الرواتب"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    payroll_entries = PayrollEntry.objects.select_related('employee', 'payroll_period')
    
    context = {
        'payroll_entries': payroll_entries,
        'title': _('Salary Breakdown Report')
    }
    
    # Log activity
    create_audit_log(
        user=request.user,
        action_type='view',
        content_type_model=PayrollEntry,
        object_id=None,
        description=_('Viewed salary breakdown report')
    )
    
    return render(request, 'hr/reports/salary_breakdown_report.html', context)


@login_required
def payroll_comparison_report(request):
    """تقرير مقارنة الرواتب"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    payroll_periods = PayrollPeriod.objects.filter(is_processed=True)[:6]  # آخر 6 فترات
    
    context = {
        'payroll_periods': payroll_periods,
        'title': _('Payroll Comparison Report')
    }
    
    # Log activity
    create_audit_log(
        user=request.user,
        action_type='view',
        content_type_model=PayrollPeriod,
        object_id=None,
        description=_('Viewed payroll comparison report')
    )
    
    return render(request, 'hr/reports/payroll_comparison_report.html', context)


@login_required
def contract_expiry_report(request):
    """تقرير انتهاء العقود"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    from datetime import datetime, timedelta
    next_three_months = datetime.now().date() + timedelta(days=90)
    expiring_contracts = Contract.objects.filter(
        end_date__lte=next_three_months,
        end_date__gte=datetime.now().date(),
        status='active'
    ).select_related('employee')
    
    context = {
        'expiring_contracts': expiring_contracts,
        'title': _('Contract Expiry Report')
    }
    
    # Log activity
    create_audit_log(
        user=request.user,
        action_type='view',
        content_type_model=Contract,
        object_id=None,
        description=_('Viewed contract expiry report')
    )
    
    return render(request, 'hr/reports/contract_expiry_report.html', context)


@login_required
def contract_types_report(request):
    """تقرير أنواع العقود"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    from django.db.models import Count
    contract_stats = Contract.objects.values('contract_type').annotate(
        count=Count('id')
    ).order_by('contract_type')
    
    context = {
        'contract_stats': contract_stats,
        'title': _('Contract Types Report')
    }
    
    # Log activity
    create_audit_log(
        user=request.user,
        action_type='view',
        content_type_model=Contract,
        object_id=None,
        description=_('Viewed contract types report')
    )
    
    return render(request, 'hr/reports/contract_types_report.html', context)


@login_required
def probation_report(request):
    """تقرير فترة التجربة"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    probation_contracts = Contract.objects.filter(
        contract_type='probation'
    ).select_related('employee')
    
    context = {
        'probation_contracts': probation_contracts,
        'title': _('Probation Period Report')
    }
    
    # Log activity
    create_audit_log(
        user=request.user,
        action_type='view',
        content_type_model=Contract,
        object_id=None,
        description=_('Viewed probation report')
    )
    
    return render(request, 'hr/reports/probation_report.html', context)


@login_required
def headcount_report(request):
    """تقرير العدد الإجمالي للموظفين"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    from django.db.models import Count
    headcount_by_department = Department.objects.annotate(
        employee_count=Count('employees', filter=Q(employees__is_active=True))
    ).filter(is_active=True)
    
    context = {
        'headcount_by_department': headcount_by_department,
        'title': _('Headcount Report')
    }
    
    # Log activity
    create_audit_log(
        user=request.user,
        action_type='view',
        content_type_model=Employee,
        object_id=None,
        description=_('Viewed headcount report')
    )
    
    return render(request, 'hr/reports/headcount_report.html', context)


@login_required
def turnover_report(request):
    """تقرير دوران الموظفين"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    from datetime import datetime
    current_year = datetime.now().year
    terminated_employees = Employee.objects.filter(
        termination_date__year=current_year
    )
    
    context = {
        'terminated_employees': terminated_employees,
        'current_year': current_year,
        'title': _('Employee Turnover Report')
    }
    
    # Log activity
    create_audit_log(
        user=request.user,
        action_type='view',
        content_type_model=Employee,
        object_id=None,
        description=_('Viewed turnover report')
    )
    
    return render(request, 'hr/reports/turnover_report.html', context)


@login_required
def anniversary_report(request):
    """تقرير ذكرى العمل"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    from datetime import datetime
    current_month = datetime.now().month
    anniversary_employees = Employee.objects.filter(
        hire_date__month=current_month,
        is_active=True
    )
    
    context = {
        'anniversary_employees': anniversary_employees,
        'current_month': datetime.now().strftime('%B'),
        'title': _('Work Anniversary Report')
    }
    
    # Log activity
    create_audit_log(
        user=request.user,
        action_type='view',
        content_type_model=Employee,
        object_id=None,
        description=_('Viewed anniversary report')
    )
    
    return render(request, 'hr/reports/anniversary_report.html', context)


# Export Functions
@login_required
def export_employees_excel(request):
    """تصدير بيانات الموظفين إلى Excel"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    import openpyxl
    from django.http import HttpResponse
    from datetime import datetime
    
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = 'Employees'
    
    # Headers
    headers = [
        'Employee ID', 'First Name', 'Last Name', 'Email', 'Phone',
        'Department', 'Position', 'Hire Date', 'Status', 'Basic Salary'
    ]
    
    for col_num, header in enumerate(headers, 1):
        worksheet.cell(row=1, column=col_num, value=header)
    
    # Data
    employees = Employee.objects.select_related('department', 'position').all()
    for row_num, employee in enumerate(employees, 2):
        worksheet.cell(row=row_num, column=1, value=employee.employee_id)
        worksheet.cell(row=row_num, column=2, value=employee.first_name)
        worksheet.cell(row=row_num, column=3, value=employee.last_name)
        worksheet.cell(row=row_num, column=4, value=employee.email)
        worksheet.cell(row=row_num, column=5, value=employee.phone)
        worksheet.cell(row=row_num, column=6, value=str(employee.department))
        worksheet.cell(row=row_num, column=7, value=str(employee.position))
        worksheet.cell(row=row_num, column=8, value=employee.hire_date)
        worksheet.cell(row=row_num, column=9, value=employee.get_status_display())
        worksheet.cell(row=row_num, column=10, value=float(employee.basic_salary))
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=employees_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    workbook.save(response)
    
    # Log activity
    create_audit_log(
        user=request.user,
        action_type='export',
        content_type_model=Employee,
        object_id=None,
        description=_('Exported employees data to Excel')
    )
    
    return response


@login_required
def export_attendance_excel(request):
    """تصدير بيانات الحضور إلى Excel"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    import openpyxl
    from django.http import HttpResponse
    from datetime import datetime, timedelta
    
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = 'Attendance'
    
    # Headers
    headers = [
        'Employee ID', 'Employee Name', 'Date', 'Check In', 'Check Out',
        'Status', 'Worked Hours', 'Overtime Hours'
    ]
    
    for col_num, header in enumerate(headers, 1):
        worksheet.cell(row=1, column=col_num, value=header)
    
    # Data (last 30 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    attendance_records = Attendance.objects.filter(
        date__range=[start_date, end_date]
    ).select_related('employee')
    
    for row_num, attendance in enumerate(attendance_records, 2):
        worksheet.cell(row=row_num, column=1, value=attendance.employee.employee_id)
        worksheet.cell(row=row_num, column=2, value=f"{attendance.employee.first_name} {attendance.employee.last_name}")
        worksheet.cell(row=row_num, column=3, value=attendance.date)
        worksheet.cell(row=row_num, column=4, value=attendance.check_in_time)
        worksheet.cell(row=row_num, column=5, value=attendance.check_out_time)
        worksheet.cell(row=row_num, column=6, value=attendance.get_attendance_type_display())
        worksheet.cell(row=row_num, column=7, value=float(attendance.worked_hours or 0))
        worksheet.cell(row=row_num, column=8, value=float(attendance.overtime_hours or 0))
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=attendance_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    workbook.save(response)
    
    # Log activity
    create_audit_log(
        user=request.user,
        action_type='export',
        content_type_model=Attendance,
        object_id=None,
        description=_('Exported attendance data to Excel')
    )
    
    return response


@login_required
def export_payroll_excel(request):
    """تصدير بيانات الرواتب إلى Excel"""
    if not request.user.is_superuser and not request.user.has_perm('hr.can_view_hr'):
        messages.error(request, _('You do not have permission to access HR module.'))
        return redirect('core:dashboard')
    
    import openpyxl
    from django.http import HttpResponse
    from datetime import datetime
    
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = 'Payroll'
    
    # Headers
    headers = [
        'Employee ID', 'Employee Name', 'Period', 'Basic Salary', 'Allowances',
        'Overtime', 'Bonuses', 'Deductions', 'Social Security', 'Income Tax',
        'Gross Salary', 'Net Salary'
    ]
    
    for col_num, header in enumerate(headers, 1):
        worksheet.cell(row=1, column=col_num, value=header)
    
    # Data (last 3 months)
    payroll_entries = PayrollEntry.objects.select_related(
        'employee', 'payroll_period'
    ).order_by('-payroll_period__start_date')[:100]  # Last 100 entries
    
    for row_num, entry in enumerate(payroll_entries, 2):
        worksheet.cell(row=row_num, column=1, value=entry.employee.employee_id)
        worksheet.cell(row=row_num, column=2, value=f"{entry.employee.first_name} {entry.employee.last_name}")
        worksheet.cell(row=row_num, column=3, value=entry.payroll_period.period_name)
        worksheet.cell(row=row_num, column=4, value=float(entry.basic_salary))
        worksheet.cell(row=row_num, column=5, value=float(entry.allowances))
        worksheet.cell(row=row_num, column=6, value=float(entry.overtime_amount))
        worksheet.cell(row=row_num, column=7, value=float(entry.bonuses))
        worksheet.cell(row=row_num, column=8, value=float(entry.deductions))
        worksheet.cell(row=row_num, column=9, value=float(entry.social_security_deduction))
        worksheet.cell(row=row_num, column=10, value=float(entry.income_tax))
        worksheet.cell(row=row_num, column=11, value=float(entry.gross_salary))
        worksheet.cell(row=row_num, column=12, value=float(entry.net_salary))
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=payroll_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    workbook.save(response)
    
    # Log activity
    create_audit_log(
        user=request.user,
        action_type='export',
        content_type_model=PayrollEntry,
        object_id=None,
        description=_('Exported payroll data to Excel')
    )
    
    return response

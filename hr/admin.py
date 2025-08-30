from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Department, Position, Employee, Contract, Attendance, 
    LeaveType, LeaveRequest, PayrollPeriod, PayrollEntry, EmployeeDocument
)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'manager', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code']
    ordering = ['name']

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'code', 'department', 'min_salary', 'max_salary', 'is_active']
    list_filter = ['department', 'is_active', 'created_at']
    search_fields = ['title', 'code', 'department__name']
    ordering = ['department__name', 'title']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'full_name', 'department', 'position', 'status', 'hire_date']
    list_filter = ['department', 'position', 'status', 'employment_type', 'gender']
    search_fields = ['employee_id', 'first_name', 'last_name', 'email', 'national_id']
    ordering = ['first_name', 'last_name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'employee', 'contract_type', 'start_date', 'end_date', 'status']
    list_filter = ['contract_type', 'status', 'start_date']
    search_fields = ['contract_number', 'employee__first_name', 'employee__last_name']
    ordering = ['-start_date']

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'check_in_time', 'check_out_time', 'attendance_type', 'worked_hours']
    list_filter = ['attendance_type', 'date', 'is_manual_entry']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_id']
    ordering = ['-date', 'employee__first_name']

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'days_per_year', 'is_paid', 'requires_approval', 'is_active']
    list_filter = ['is_paid', 'requires_approval', 'is_active']
    search_fields = ['name', 'code']
    ordering = ['name']

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'days_count', 'status']
    list_filter = ['leave_type', 'status', 'start_date']
    search_fields = ['employee__first_name', 'employee__last_name', 'reason']
    ordering = ['-created_at']

@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_processed', 'processed_date']
    list_filter = ['is_processed', 'start_date']
    search_fields = ['name']
    ordering = ['-start_date']

@admin.register(PayrollEntry)
class PayrollEntryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'payroll_period', 'gross_salary', 'total_deductions', 'net_salary', 'is_paid']
    list_filter = ['payroll_period', 'is_paid', 'payment_date']
    search_fields = ['employee__first_name', 'employee__last_name']
    ordering = ['-payroll_period__start_date', 'employee__first_name']

@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'document_type', 'title', 'upload_date', 'uploaded_by']
    list_filter = ['document_type', 'upload_date']
    search_fields = ['employee__first_name', 'employee__last_name', 'title']
    ordering = ['-upload_date']

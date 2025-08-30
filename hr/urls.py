from django.urls import path
from . import views

app_name = 'hr'

urlpatterns = [
    # Dashboard
    path('', views.hr_dashboard, name='dashboard'),
    
    # Employee URLs
    path('employees/', views.EmployeeListView.as_view(), name='employee_list'),
    path('employees/<int:pk>/', views.EmployeeDetailView.as_view(), name='employee_detail'),
    path('employees/create/', views.EmployeeCreateView.as_view(), name='employee_create'),
    path('employees/<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='employee_edit'),
    path('employees/<int:pk>/delete/', views.EmployeeDeleteView.as_view(), name='employee_delete'),
    
    # Department URLs
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('departments/<int:pk>/', views.DepartmentDetailView.as_view(), name='department_detail'),
    path('departments/create/', views.DepartmentCreateView.as_view(), name='department_create'),
    path('departments/<int:pk>/edit/', views.DepartmentUpdateView.as_view(), name='department_edit'),
    path('departments/<int:pk>/delete/', views.DepartmentDeleteView.as_view(), name='department_delete'),
    
    # Position URLs
    path('positions/', views.PositionListView.as_view(), name='position_list'),
    path('positions/<int:pk>/', views.PositionDetailView.as_view(), name='position_detail'),
    path('positions/create/', views.PositionCreateView.as_view(), name='position_create'),
    path('positions/<int:pk>/edit/', views.PositionUpdateView.as_view(), name='position_edit'),
    path('positions/<int:pk>/delete/', views.PositionDeleteView.as_view(), name='position_delete'),
    
    # Contract URLs
    path('contracts/', views.ContractListView.as_view(), name='contract_list'),
    path('contracts/<int:pk>/', views.ContractDetailView.as_view(), name='contract_detail'),
    path('contracts/create/', views.ContractCreateView.as_view(), name='contract_create'),
    path('contracts/<int:pk>/edit/', views.ContractUpdateView.as_view(), name='contract_edit'),
    path('contracts/<int:pk>/delete/', views.ContractDeleteView.as_view(), name='contract_delete'),
    
    # Attendance URLs
    path('attendance/', views.AttendanceListView.as_view(), name='attendance_list'),
    path('attendance/<int:pk>/', views.AttendanceDetailView.as_view(), name='attendance_detail'),
    path('attendance/create/', views.AttendanceCreateView.as_view(), name='attendance_create'),
    path('attendance/<int:pk>/edit/', views.AttendanceUpdateView.as_view(), name='attendance_edit'),
    path('attendance/<int:pk>/delete/', views.AttendanceDeleteView.as_view(), name='attendance_delete'),
    path('attendance/upload/', views.attendance_upload, name='attendance_upload'),
    path('attendance/report/', views.attendance_report, name='attendance_report'),
    
    # Leave URLs
    path('leaves/', views.LeaveRequestListView.as_view(), name='leave_request_list'),
    path('leaves/<int:pk>/', views.LeaveRequestDetailView.as_view(), name='leave_request_detail'),
    path('leaves/create/', views.LeaveRequestCreateView.as_view(), name='leave_request_create'),
    path('leaves/<int:pk>/edit/', views.LeaveRequestUpdateView.as_view(), name='leave_request_edit'),
    path('leaves/<int:pk>/delete/', views.LeaveRequestDeleteView.as_view(), name='leave_request_delete'),
    path('leaves/<int:pk>/approve/', views.approve_leave_request, name='approve_leave_request'),
    path('leaves/balance/', views.leave_balance_report, name='leave_balance_report'),
    
    # Leave Types URLs
    path('leave-types/', views.LeaveTypeListView.as_view(), name='leave_type_list'),
    path('leave-types/<int:pk>/', views.LeaveTypeDetailView.as_view(), name='leave_type_detail'),
    path('leave-types/create/', views.LeaveTypeCreateView.as_view(), name='leave_type_create'),
    path('leave-types/<int:pk>/edit/', views.LeaveTypeUpdateView.as_view(), name='leave_type_edit'),
    path('leave-types/<int:pk>/delete/', views.LeaveTypeDeleteView.as_view(), name='leave_type_delete'),
    
    # Payroll URLs
    path('payroll/', views.PayrollPeriodListView.as_view(), name='payroll_period_list'),
    path('payroll/<int:pk>/', views.PayrollPeriodDetailView.as_view(), name='payroll_period_detail'),
    path('payroll/create/', views.PayrollPeriodCreateView.as_view(), name='payroll_period_create'),
    path('payroll/<int:pk>/edit/', views.PayrollPeriodUpdateView.as_view(), name='payroll_period_edit'),
    path('payroll/<int:pk>/delete/', views.PayrollPeriodDeleteView.as_view(), name='payroll_period_delete'),
    path('payroll/<int:pk>/process/', views.process_payroll, name='process_payroll'),
    path('payroll/<int:pk>/journal/', views.create_payroll_journal_entries, name='create_payroll_journal_entries'),
    path('payroll/<int:pk>/report/', views.payroll_report, name='payroll_report'),
    
    # Payroll Entry URLs
    path('payroll-entries/', views.PayrollEntryListView.as_view(), name='payroll_entry_list'),
    path('payroll-entries/<int:pk>/', views.PayrollEntryDetailView.as_view(), name='payroll_entry_detail'),
    path('payroll-entries/create/', views.PayrollEntryCreateView.as_view(), name='payroll_entry_create'),
    path('payroll-entries/<int:pk>/edit/', views.PayrollEntryUpdateView.as_view(), name='payroll_entry_edit'),
    path('payroll-entries/<int:pk>/delete/', views.PayrollEntryDeleteView.as_view(), name='payroll_entry_delete'),
    
    # Employee Document URLs
    path('documents/', views.EmployeeDocumentListView.as_view(), name='employee_document_list'),
    path('documents/<int:pk>/', views.EmployeeDocumentDetailView.as_view(), name='employee_document_detail'),
    path('documents/create/', views.EmployeeDocumentCreateView.as_view(), name='employee_document_create'),
    path('documents/<int:pk>/edit/', views.EmployeeDocumentUpdateView.as_view(), name='employee_document_edit'),
    path('documents/<int:pk>/delete/', views.EmployeeDocumentDeleteView.as_view(), name='employee_document_delete'),
    path('documents/expiring/', views.expiring_documents, name='expiring_documents'),
    
    # Reports URLs
    path('reports/', views.hr_reports, name='hr_reports'),
    
    # Employee Reports
    path('reports/employees/', views.employee_report, name='employee_report'),
    path('reports/employees/department/', views.department_report, name='department_report'),
    path('reports/employees/new-hires/', views.new_hires_report, name='new_hires_report'),
    
    # Attendance Reports
    path('reports/attendance/', views.attendance_report, name='attendance_report'),
    path('reports/attendance/late/', views.late_arrivals_report, name='late_arrivals_report'),
    path('reports/attendance/overtime/', views.overtime_report, name='overtime_report'),
    
    # Leave Reports
    path('reports/leave/summary/', views.leave_summary_report, name='leave_summary_report'),
    path('reports/leave/balance/', views.leave_balance_report, name='leave_balance_report'),
    path('reports/leave/upcoming/', views.upcoming_leaves_report, name='upcoming_leaves_report'),
    
    # Payroll Reports
    path('reports/payroll/summary/', views.payroll_summary_report, name='payroll_summary_report'),
    path('reports/payroll/breakdown/', views.salary_breakdown_report, name='salary_breakdown_report'),
    path('reports/payroll/comparison/', views.payroll_comparison_report, name='payroll_comparison_report'),
    
    # Contract Reports
    path('reports/contracts/expiry/', views.contract_expiry_report, name='contract_expiry_report'),
    path('reports/contracts/types/', views.contract_types_report, name='contract_types_report'),
    path('reports/contracts/probation/', views.probation_report, name='probation_report'),
    
    # Performance Reports
    path('reports/performance/headcount/', views.headcount_report, name='headcount_report'),
    path('reports/performance/turnover/', views.turnover_report, name='turnover_report'),
    path('reports/performance/anniversary/', views.anniversary_report, name='anniversary_report'),
    
    # Export URLs
    path('reports/export/employees/', views.export_employees_excel, name='export_employees_excel'),
    path('reports/export/attendance/', views.export_attendance_excel, name='export_attendance_excel'),
    path('reports/export/payroll/', views.export_payroll_excel, name='export_payroll_excel'),
    
    # API URLs for AJAX
    path('api/positions-by-department/<int:department_id>/', views.get_positions_by_department, name='get_positions_by_department'),
    path('api/employee-info/<int:employee_id>/', views.get_employee_info, name='get_employee_info'),
    path('api/leave-balance/<int:employee_id>/', views.get_employee_leave_balance, name='get_employee_leave_balance'),
]

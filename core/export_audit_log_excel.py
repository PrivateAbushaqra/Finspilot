import io
import xlsxwriter
from django.http import HttpResponse
from .models import AuditLog

def export_audit_log_to_excel(queryset):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Audit Log')

    # Write headers
    headers = ['الوقت', 'المستخدم', 'نوع العملية', 'نوع المحتوى', 'الوصف', 'عنوان IP']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    # Write data
    for row, log in enumerate(queryset, start=1):
        worksheet.write(row, 0, log.timestamp.strftime('%Y-%m-%d %H:%M:%S'))
        worksheet.write(row, 1, log.user.get_full_name() or log.user.username)
        worksheet.write(row, 2, log.get_action_type_display() if hasattr(log, 'get_action_type_display') else log.action_type)
        worksheet.write(row, 3, log.content_type)
        worksheet.write(row, 4, log.description)
        worksheet.write(row, 5, log.ip_address)

    workbook.close()
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=audit_log.xlsx'
    return response

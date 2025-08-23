from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _

from accounts.models import AccountTransaction
from customers.models import CustomerSupplier
from core.signals import log_view_activity, log_export_activity


def _parse_date(value, default):
    try:
        # Expecting YYYY-MM-DD from input[type=date]
        parts = [int(x) for x in str(value).split('-')]
        if len(parts) == 3:
            return date(parts[0], parts[1], parts[2])
    except Exception:
        pass
    return default


@login_required
def customer_statement(request):
    """
    Customer Statement report: select customer and date range, view transactions with opening/closing balances.
    Supports export to CSV/XLSX (XLSX best-effort; falls back to CSV if libs missing).
    """
    # Permission gate: allow superuser or user_type admin/superadmin implicitly; else require explicit permission
    user = request.user
    has_perm = (
        getattr(user, 'is_superuser', False) or
        getattr(user, 'user_type', None) in ['superadmin', 'admin'] or
        user.has_perm('reports.can_view_customer_statement')
    )
    if not has_perm:
        raise PermissionDenied

    customers = CustomerSupplier.objects.filter(type__in=['customer', 'both'], is_active=True).order_by('name')

    # Defaults: last 30 days
    today = date.today()
    default_start = today - timedelta(days=30)
    default_end = today

    customer_id = request.GET.get('customer')
    start_raw = request.GET.get('start_date')
    end_raw = request.GET.get('end_date')
    export = request.GET.get('export')  # csv or xlsx

    start_date = _parse_date(start_raw, default_start)
    end_date = _parse_date(end_raw, default_end)

    selected_customer = None
    statement_rows = []
    opening_balance = Decimal('0.000')
    totals_debit = Decimal('0.000')
    totals_credit = Decimal('0.000')
    closing_balance = Decimal('0.000')

    if customer_id:
        selected_customer = customers.filter(pk=customer_id).first()

    view_logged = False

    if selected_customer:
        # Opening balance = net of all transactions before start_date
        before_qs = AccountTransaction.objects.filter(
            customer_supplier=selected_customer,
            date__lt=start_date,
        )
        before_debit = before_qs.filter(direction='debit').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        before_credit = before_qs.filter(direction='credit').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        opening_balance = (before_debit - before_credit).quantize(Decimal('0.001'))

        # Transactions in period
        period_qs = AccountTransaction.objects.filter(
            customer_supplier=selected_customer,
            date__gte=start_date,
            date__lte=end_date,
        ).order_by('date', 'created_at', 'id')

        running = opening_balance
        for t in period_qs:
            debit = t.amount if t.direction == 'debit' else Decimal('0')
            credit = t.amount if t.direction == 'credit' else Decimal('0')
            running = (running + debit - credit).quantize(Decimal('0.001'))
            statement_rows.append({
                'date': t.date,
                'number': t.transaction_number,
                'type': t.get_transaction_type_display(),
                'description': t.description or '',
                'debit': debit,
                'credit': credit,
                'running_balance': running,
            })

        totals_debit = period_qs.filter(direction='debit').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        totals_credit = period_qs.filter(direction='credit').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        closing_balance = (opening_balance + totals_debit - totals_credit).quantize(Decimal('0.001'))

        # Audit log for viewing a report
        try:
            desc = _("Viewing customer statement for %(customer)s from %(start)s to %(end)s") % {
                'customer': selected_customer.name,
                'start': start_date,
                'end': end_date,
            }
            class ReportObj:
                id = 0
                pk = 0
                def __str__(self):
                    return str(_('Customer Statement'))
            log_view_activity(request, 'view', ReportObj(), desc)
            view_logged = True
        except Exception:
            pass

        # Handle export
        if export and export.lower() in ('csv', 'xlsx'):
            filename_base = f"customer_statement_{selected_customer.sequence_number or selected_customer.pk}_{start_date}_{end_date}"
            if export.lower() == 'xlsx':
                # Best-effort XLSX using openpyxl; fallback to CSV
                try:
                    import io
                    from openpyxl import Workbook
                    wb = Workbook()
                    ws = wb.active
                    ws.title = str(_('Statement'))
                    headers = [
                        _('Date'), _('Number'), _('Type'), _('Description'), _('Debit'), _('Credit'), _('Running Balance')
                    ]
                    ws.append(headers)
                    # Opening row
                    ws.append([str(start_date), '-', _('Opening Balance'), '', '', '', float(opening_balance)])
                    for r in statement_rows:
                        ws.append([
                            str(r['date']), r['number'], r['type'], r['description'], float(r['debit']), float(r['credit']), float(r['running_balance'])
                        ])
                    # Totals and closing
                    ws.append(['', '', _('Totals'), '', float(totals_debit), float(totals_credit), ''])
                    ws.append(['', '', _('Closing Balance'), '', '', '', float(closing_balance)])
                    bio = io.BytesIO()
                    wb.save(bio)
                    bio.seek(0)
                    response = HttpResponse(bio.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = f'attachment; filename={filename_base}.xlsx'
                    try:
                        log_export_activity(request, str(_('Customer Statement')), f'{filename_base}.xlsx', 'XLSX')
                    except Exception:
                        pass
                    return response
                except Exception:
                    # Fallback to CSV
                    export = 'csv'

            if export.lower() == 'csv':
                import csv
                response = HttpResponse(content_type='text/csv; charset=utf-8')
                response.write('\ufeff')  # BOM for Excel + Arabic
                response['Content-Disposition'] = f'attachment; filename={filename_base}.csv'
                writer = csv.writer(response)
                writer.writerow([_('Customer Statement')])
                writer.writerow([_('Customer'), selected_customer.name])
                writer.writerow([_('From'), start_date, _('To'), end_date])
                writer.writerow([])
                writer.writerow([_('Date'), _('Number'), _('Type'), _('Description'), _('Debit'), _('Credit'), _('Running Balance')])
                writer.writerow([start_date, '-', _('Opening Balance'), '', '', '', opening_balance])
                for r in statement_rows:
                    writer.writerow([r['date'], r['number'], r['type'], r['description'], r['debit'], r['credit'], r['running_balance']])
                writer.writerow(['', '', _('Totals'), '', totals_debit, totals_credit, ''])
                writer.writerow(['', '', _('Closing Balance'), '', '', '', closing_balance])
                try:
                    log_export_activity(request, str(_('Customer Statement')), f'{filename_base}.csv', 'CSV')
                except Exception:
                    pass
                return response

    context = {
        'customers': customers,
        'selected_customer': selected_customer,
        'start_date': start_date,
        'end_date': end_date,
        'statement_rows': statement_rows,
        'opening_balance': opening_balance,
        'totals_debit': totals_debit,
        'totals_credit': totals_credit,
        'closing_balance': closing_balance,
    }

    if not view_logged:
        try:
            class ReportObj:
                id = 0
                pk = 0
                def __str__(self):
                    return str(_('Customer Statement'))
            log_view_activity(request, 'view', ReportObj(), str(_('Viewing customer statement page')))
        except Exception:
            pass

    return render(request, 'reports/customer_statement.html', context)

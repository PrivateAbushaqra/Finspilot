from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count
from django.db import models
from django.utils import timezone as django_timezone
from datetime import datetime, timedelta
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import csv
import io
import traceback

# محاولة استيراد openpyxl للتصدير بصيغة Excel
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

from .models import SystemNotification, CompanySettings, AuditLog
# سيتم استيراد النماذج عند الحاجة لتجنب الاستيراد الدائري


class DashboardView(LoginRequiredMixin, TemplateView):
    """الشاشة الرئيسية"""
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # تواريخ مختلفة للإحصائيات
        today = django_timezone.now().date()
        start_of_month = today.replace(day=1)
        start_of_quarter = datetime(today.year, ((today.month - 1) // 3) * 3 + 1, 1).date()
        start_of_half_year = datetime(today.year, 1 if today.month <= 6 else 7, 1).date()
        start_of_year = datetime(today.year, 1, 1).date()

        # إحصائيات المبيعات
        sales_stats = self.get_sales_statistics(today, start_of_month, start_of_quarter, start_of_half_year, start_of_year)
        context['sales_stats'] = sales_stats

        # إحصائيات المشتريات
        purchase_stats = self.get_purchase_statistics(today, start_of_month, start_of_quarter, start_of_half_year, start_of_year)
        context['purchase_stats'] = purchase_stats

        # أرصدة البنوك والصناديق
        try:
            from banks.models import BankAccount
            from cashboxes.models import Cashbox
            from receipts.models import PaymentReceipt
            from settings.models import Currency, CompanySettings
            
            # أرصدة البنوك (الرصيد الفعلي من المعاملات)
            bank_accounts = BankAccount.objects.filter(is_active=True)
            bank_balances = {}
            for account in bank_accounts:
                currency = account.currency  # CharField
                if currency not in bank_balances:
                    bank_balances[currency] = []
                # حساب الرصيد الفعلي من المعاملات
                actual_balance = account.calculate_actual_balance()
                bank_balances[currency].append({
                    'name': account.name,
                    'balance': actual_balance,
                    'account_number': account.account_number
                })
            
            # أرصدة الصناديق (الرصيد الفعلي من المعاملات)
            cashboxes = Cashbox.objects.filter(is_active=True)
            cashbox_balances = {}
            for cashbox in cashboxes:
                currency = cashbox.currency  # CharField
                if currency not in cashbox_balances:
                    cashbox_balances[currency] = []
                # حساب الرصيد الفعلي من المعاملات
                actual_balance = cashbox.calculate_actual_balance()
                cashbox_balances[currency].append({
                    'name': cashbox.name,
                    'balance': actual_balance,
                    'location': cashbox.location
                })
            
            # الشيكات المعلقة (لم يحن موعد استحقاقها ولم يتم تحصيلها)
            pending_checks = PaymentReceipt.objects.filter(
                payment_type='check',
                check_status='pending',
                check_due_date__gt=django_timezone.now().date(),
                is_active=True,
                is_reversed=False
            ).select_related('customer', 'check_cashbox', 'cashbox')
            
            # تجميع الشيكات حسب العملة
            pending_checks_by_currency = {}
            for check in pending_checks:
                # الحصول على العملة من الصندوق المرتبط بالشيك
                currency = 'SAR'  # افتراضي
                if check.check_cashbox:
                    currency = check.check_cashbox.currency
                elif check.cashbox:
                    currency = check.cashbox.currency
                
                if currency not in pending_checks_by_currency:
                    pending_checks_by_currency[currency] = {
                        'total_amount': 0,
                        'count': 0,
                        'checks': []
                    }
                
                # التأكد من أن المبلغ أكبر من صفر
                if check.amount > 0:
                    pending_checks_by_currency[currency]['total_amount'] += check.amount
                    pending_checks_by_currency[currency]['count'] += 1
                    pending_checks_by_currency[currency]['checks'].append({
                        'receipt_number': check.receipt_number,
                        'customer_name': check.customer.name,
                        'amount': check.amount,
                        'check_number': check.check_number,
                        'due_date': check.check_due_date
                    })
            
            # العملة الأساسية من إعدادات الشركة
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                base_currency_code = company_settings.base_currency.code
            else:
                base_currency = Currency.get_base_currency()
                base_currency_code = base_currency.code if base_currency else 'SAR'
            
            context['bank_balances'] = bank_balances
            context['cashbox_balances'] = cashbox_balances
            context['pending_checks_by_currency'] = pending_checks_by_currency
            context['base_currency_code'] = base_currency_code
            
        except (ImportError, Exception) as e:
            context['bank_balances'] = {}
            context['cashbox_balances'] = {}
            context['pending_checks_by_currency'] = {}
            context['base_currency_code'] = 'SAR'

        # الإشعارات غير المقروءة
        unread_notifications = SystemNotification.objects.filter(is_read=False)
        if not self.request.user.is_superuser:
            unread_notifications = unread_notifications.filter(user=self.request.user)
        context['unread_notifications_count'] = unread_notifications.count()

        return context

    def get_sales_statistics(self, today, start_of_month, start_of_quarter, start_of_half_year, start_of_year):
        """حساب إحصائيات المبيعات"""
        try:
            from sales.models import SalesInvoice
            
            stats = {}
            
            # إحصائيات اليوم
            today_sales = SalesInvoice.objects.filter(date=today)
            stats['today'] = {
                'count': today_sales.count(),
                'total': today_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            }
            
            # إحصائيات الشهر
            month_sales = SalesInvoice.objects.filter(date__gte=start_of_month)
            stats['month'] = {
                'count': month_sales.count(),
                'total': month_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            }
            
            # إحصائيات الربع
            quarter_sales = SalesInvoice.objects.filter(date__gte=start_of_quarter)
            stats['quarter'] = {
                'count': quarter_sales.count(),
                'total': quarter_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            }
            
            # إحصائيات نصف السنة
            half_year_sales = SalesInvoice.objects.filter(date__gte=start_of_half_year)
            stats['half_year'] = {
                'count': half_year_sales.count(),
                'total': half_year_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            }
            
            # إحصائيات السنة
            year_sales = SalesInvoice.objects.filter(date__gte=start_of_year)
            stats['year'] = {
                'count': year_sales.count(),
                'total': year_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            }
            
            return stats
            
        except ImportError:
            # في حالة عدم وجود تطبيق المبيعات
            return {
                'today': {'count': 0, 'total': 0},
                'month': {'count': 0, 'total': 0},
                'quarter': {'count': 0, 'total': 0},
                'half_year': {'count': 0, 'total': 0},
                'year': {'count': 0, 'total': 0},
            }

    def get_purchase_statistics(self, today, start_of_month, start_of_quarter, start_of_half_year, start_of_year):
        """حساب إحصائيات المشتريات"""
        try:
            from purchases.models import PurchaseInvoice
            
            stats = {}
            
            # إحصائيات اليوم
            today_purchases = PurchaseInvoice.objects.filter(date=today)
            stats['today'] = {
                'count': today_purchases.count(),
                'total': today_purchases.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            }
            
            # إحصائيات الشهر
            month_purchases = PurchaseInvoice.objects.filter(date__gte=start_of_month)
            stats['month'] = {
                'count': month_purchases.count(),
                'total': month_purchases.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            }
            
            # إحصائيات الربع
            quarter_purchases = PurchaseInvoice.objects.filter(date__gte=start_of_quarter)
            stats['quarter'] = {
                'count': quarter_purchases.count(),
                'total': quarter_purchases.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            }
            
            # إحصائيات نصف السنة
            half_year_purchases = PurchaseInvoice.objects.filter(date__gte=start_of_half_year)
            stats['half_year'] = {
                'count': half_year_purchases.count(),
                'total': half_year_purchases.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            }
            
            # إحصائيات السنة
            year_purchases = PurchaseInvoice.objects.filter(date__gte=start_of_year)
            stats['year'] = {
                'count': year_purchases.count(),
                'total': year_purchases.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            }
            
            return stats
            
        except ImportError:
            # في حالة عدم وجود تطبيق المشتريات
            return {
                'today': {'count': 0, 'total': 0},
                'month': {'count': 0, 'total': 0},
                'quarter': {'count': 0, 'total': 0},
                'half_year': {'count': 0, 'total': 0},
                'year': {'count': 0, 'total': 0},
            }
        

class NotificationListView(LoginRequiredMixin, ListView):
    """قائمة الإشعارات"""
    model = SystemNotification
    template_name = 'core/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        queryset = SystemNotification.objects.all()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(user=self.request.user)
        return queryset.order_by('-created_at')


@login_required
def mark_notification_read(request, pk):
    """تحديد الإشعار كمقروء"""
    notification = get_object_or_404(SystemNotification, pk=pk)
    
    # التحقق من الصلاحيات
    if not request.user.is_superuser and notification.user != request.user:
        return JsonResponse({'error': 'ليس لديك صلاحية'}, status=403)
    
    notification.is_read = True
    notification.save()
    
    return JsonResponse({'success': True})


class TaxReportView(LoginRequiredMixin, TemplateView):
    """تقرير الضرائب للمبيعات والمشتريات ومردوداتهما"""
    template_name = 'core/tax_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # جمع جميع المستندات مع الضرائب
        tax_data = []
        
        # فواتير المبيعات
        try:
            from sales.models import SalesInvoice, SalesInvoiceItem
            sales_invoices = SalesInvoice.objects.all().select_related('customer')
            
            for invoice in sales_invoices:
                items = SalesInvoiceItem.objects.filter(invoice=invoice, tax_rate__gt=0)
                tax_breakdown = {}
                total_tax = 0
                
                for item in items:
                    tax_rate = float(item.tax_rate)
                    tax_amount = float(item.tax_amount)
                    
                    if tax_rate > 0 and tax_amount > 0:
                        if tax_rate not in tax_breakdown:
                            tax_breakdown[tax_rate] = 0
                        tax_breakdown[tax_rate] += tax_amount
                        total_tax += tax_amount
                
                if total_tax > 0:
                    tax_data.append({
                        'document_number': invoice.invoice_number,
                        'document_type': 'فاتورة مبيعات',
                        'customer_supplier': invoice.customer.name if invoice.customer else 'عميل نقدي',
                        'date': invoice.date,
                        'tax_breakdown': tax_breakdown,
                        'total_tax': total_tax,
                        'is_positive': True,  # المبيعات موجبة
                        'amount_before_tax': float(invoice.subtotal) if hasattr(invoice, 'subtotal') else (float(invoice.total_amount) - total_tax)
                    })
        except (ImportError, Exception) as e:
            pass
        
        # فواتير المشتريات
        try:
            from purchases.models import PurchaseInvoice, PurchaseInvoiceItem
            purchase_invoices = PurchaseInvoice.objects.all().select_related('supplier')
            
            for invoice in purchase_invoices:
                items = PurchaseInvoiceItem.objects.filter(invoice=invoice, tax_rate__gt=0)
                tax_breakdown = {}
                total_tax = 0
                
                for item in items:
                    tax_rate = float(item.tax_rate)
                    tax_amount = float(item.tax_amount)
                    
                    if tax_rate > 0 and tax_amount > 0:
                        if tax_rate not in tax_breakdown:
                            tax_breakdown[tax_rate] = 0
                        tax_breakdown[tax_rate] += tax_amount
                        total_tax += tax_amount
                
                if total_tax > 0:
                    tax_data.append({
                        'document_number': invoice.invoice_number,
                        'document_type': 'فاتورة مشتريات',
                        'customer_supplier': invoice.supplier.name if invoice.supplier else 'غير محدد',
                        'date': invoice.date,
                        'tax_breakdown': tax_breakdown,
                        'total_tax': -total_tax,  # المشتريات سالبة
                        'is_positive': False,
                        'amount_before_tax': float(invoice.subtotal) if hasattr(invoice, 'subtotal') else (float(invoice.total_amount) - total_tax)
                    })
        except (ImportError, Exception) as e:
            pass
        
        # مردودات المبيعات
        try:
            from sales.models import SalesReturn, SalesReturnItem
            sales_returns = SalesReturn.objects.all().select_related('customer')
            
            for return_invoice in sales_returns:
                items = SalesReturnItem.objects.filter(return_invoice=return_invoice, tax_rate__gt=0)
                tax_breakdown = {}
                total_tax = 0
                
                for item in items:
                    tax_rate = float(item.tax_rate)
                    tax_amount = float(item.tax_amount)
                    
                    if tax_rate > 0 and tax_amount > 0:
                        if tax_rate not in tax_breakdown:
                            tax_breakdown[tax_rate] = 0
                        tax_breakdown[tax_rate] += tax_amount
                        total_tax += tax_amount
                
                if total_tax > 0:
                    tax_data.append({
                        'document_number': return_invoice.return_number,
                        'document_type': 'مردود مبيعات',
                        'customer_supplier': return_invoice.customer.name if return_invoice.customer else 'غير محدد',
                        'date': return_invoice.date,
                        'tax_breakdown': tax_breakdown,
                        'total_tax': -total_tax,  # مردود المبيعات سالب
                        'is_positive': False,
                        'amount_before_tax': float(return_invoice.subtotal) if hasattr(return_invoice, 'subtotal') else (float(return_invoice.total) - total_tax)
                    })
        except (ImportError, Exception) as e:
            pass
        
        # مردودات المشتريات
        try:
            from purchases.models import PurchaseReturn, PurchaseReturnItem
            purchase_returns = PurchaseReturn.objects.all().select_related('original_invoice__supplier')
            
            for return_invoice in purchase_returns:
                items = PurchaseReturnItem.objects.filter(return_invoice=return_invoice, tax_rate__gt=0)
                tax_breakdown = {}
                total_tax = 0
                
                for item in items:
                    tax_rate = float(item.tax_rate)
                    tax_amount = float(item.tax_amount)
                    
                    if tax_rate > 0 and tax_amount > 0:
                        if tax_rate not in tax_breakdown:
                            tax_breakdown[tax_rate] = 0
                        tax_breakdown[tax_rate] += tax_amount
                        total_tax += tax_amount
                
                if total_tax > 0:
                    tax_data.append({
                        'document_number': return_invoice.return_number,
                        'document_type': 'مردود مشتريات',
                        'customer_supplier': return_invoice.supplier.name if hasattr(return_invoice, 'supplier') and return_invoice.supplier else 'غير محدد',
                        'date': return_invoice.date,
                        'tax_breakdown': tax_breakdown,
                        'total_tax': total_tax,  # مردود المشتريات موجب
                        'is_positive': True,
                        'amount_before_tax': float(return_invoice.subtotal) if hasattr(return_invoice, 'subtotal') else (float(return_invoice.total) - total_tax)
                    })
        except (ImportError, Exception) as e:
            pass
        
        # ترتيب البيانات حسب التاريخ (تصاعدي - الأقدم أولاً)
        tax_data.sort(key=lambda x: x['date'])
        
        # جمع جميع أسعار الضرائب المستخدمة
        all_tax_rates = set()
        for item in tax_data:
            all_tax_rates.update(item['tax_breakdown'].keys())
        all_tax_rates = sorted(list(all_tax_rates))
        
        # حساب إجماليات كل عمود ضريبة
        column_totals = {}
        for rate in all_tax_rates:
            column_totals[rate] = 0
            for item in tax_data:
                if rate in item['tax_breakdown']:
                    if item['is_positive']:
                        column_totals[rate] += item['tax_breakdown'][rate]
                    else:
                        column_totals[rate] -= item['tax_breakdown'][rate]
        
        # حساب الإجماليات
        total_positive = sum(item['total_tax'] for item in tax_data if item['is_positive'])
        total_negative = sum(item['total_tax'] for item in tax_data if not item['is_positive'])
        net_tax = total_positive + total_negative
        
        # حساب إجمالي عمود "إجمالي الضريبة"
        grand_total_tax = sum(item['total_tax'] for item in tax_data)
        
        # حساب إجمالي القيم قبل الضريبة
        total_amount_before_tax = sum(item['amount_before_tax'] for item in tax_data)
        
        context.update({
            'tax_data': tax_data,
            'all_tax_rates': all_tax_rates,
            'column_totals': column_totals,
            'total_positive': total_positive,
            'total_negative': total_negative,
            'net_tax': net_tax,
            'grand_total_tax': grand_total_tax,
            'total_amount_before_tax': total_amount_before_tax
        })
        
        return context


class ProfitLossReportView(LoginRequiredMixin, TemplateView):
    """تقرير الأرباح والخسائر الشامل"""
    template_name = 'core/profit_loss_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # استلام تواريخ الفلتر
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        # تحديد الفترة الافتراضية: الشهر الحالي
        if not start_date:
            today = django_timezone.now().date()
            start_date = today.replace(day=1).strftime('%Y-%m-%d')  # بداية الشهر الحالي
        if not end_date:
            end_date = django_timezone.now().date().strftime('%Y-%m-%d')   # اليوم الحالي
            
        # تحويل التواريخ لاستخدامها في الاستعلامات
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # حساب عدد الأيام
        days_count = (end_date_obj - start_date_obj).days + 1  # +1 لتضمين اليوم الأخير
        
        # إرسال البيانات للـ template
        context['start_date'] = start_date  # للعرض كنص
        context['end_date'] = end_date      # للعرض كنص
        context['start_date_obj'] = start_date_obj  # للـ timesince filter
        context['end_date_obj'] = end_date_obj      # للـ timesince filter
        context['days_count'] = days_count  # عدد الأيام
        
        # استيراد النماذج المطلوبة
        try:
            from sales.models import SalesInvoice, SalesReturn
            from purchases.models import PurchaseInvoice, PurchaseReturn
        except ImportError:
            context['error'] = _("حدث خطأ في استيراد النماذج المطلوبة")
            return context
            
        # 1. حساب الإيرادات
        
        # فواتير المبيعات
        sales_invoices = SalesInvoice.objects.filter(
            date__gte=start_date_obj,
            date__lte=end_date_obj
        )
        sales_revenue = sales_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        # مردودات المبيعات (تطرح من الإيرادات)
        sales_returns = SalesReturn.objects.filter(
            date__gte=start_date_obj,
            date__lte=end_date_obj
        )
        sales_returns_total = sales_returns.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        # صافي الإيرادات
        net_revenue = sales_revenue - sales_returns_total
        
        # 2. حساب التكاليف
        
        # فواتير المشتريات
        purchase_invoices = PurchaseInvoice.objects.filter(
            date__gte=start_date_obj,
            date__lte=end_date_obj
        )
        purchase_costs = purchase_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        # مردودات المشتريات (تطرح من التكاليف)
        purchase_returns = PurchaseReturn.objects.filter(
            date__gte=start_date_obj,
            date__lte=end_date_obj
        )
        purchase_returns_total = purchase_returns.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        # صافي التكاليف
        net_costs = purchase_costs - purchase_returns_total
        
        # 3. حسابات الربحية
        
        # الربح الإجمالي
        gross_profit = net_revenue - net_costs
        
        # هامش الربح الإجمالي (النسبة المئوية)
        gross_margin = (gross_profit / net_revenue * 100) if net_revenue > 0 else 0
        
        # إضافة البيانات للسياق
        context.update({
            # الإيرادات
            'sales_revenue': sales_revenue,
            'sales_returns_total': sales_returns_total,
            'net_revenue': net_revenue,
            
            # التكاليف
            'purchase_costs': purchase_costs,
            'purchase_returns_total': purchase_returns_total,
            'net_costs': net_costs,
            
            # الأرباح
            'gross_profit': gross_profit,
            'gross_margin': gross_margin,
            
            # بيانات إضافية
            'sales_count': sales_invoices.count(),
            'sales_returns_count': sales_returns.count(),
            'purchase_count': purchase_invoices.count(),
            'purchase_returns_count': purchase_returns.count(),
            
            # العملة
            'currency': self.get_base_currency(),
        })
        
        return context
        
    def get_base_currency(self):
        """الحصول على العملة الأساسية"""
        try:
            from settings.models import CompanySettings, Currency
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                return company_settings.base_currency
            return Currency.objects.filter(is_base=True).first() or Currency.objects.first()
        except Exception:
            return None


class AuditLogListView(LoginRequiredMixin, ListView):
    """عرض سجل الأنشطة"""
    model = None  # سيتم تحديده في get_queryset
    template_name = 'core/audit_log.html'
    context_object_name = 'audit_logs'
    paginate_by = 50
    
    def dispatch(self, request, *args, **kwargs):
        """التحقق من الصلاحيات"""
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        
        if not (getattr(request.user, 'is_admin', False) or request.user.has_perm('core.view_audit_log')):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied(_('ليس لديك صلاحية للوصول إلى سجل الأنشطة'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """الحصول على سجل الأنشطة مع الفلاتر"""
        from .models import AuditLog
        queryset = AuditLog.objects.select_related('user').order_by('-timestamp')
        
        # فلتر حسب المستخدم
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # فلتر حسب نوع العملية
        action_type = self.request.GET.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        # فلتر حسب نوع المحتوى
        content_type = self.request.GET.get('content_type')
        if content_type:
            queryset = queryset.filter(content_type__icontains=content_type)
        
        # فلتر حسب التاريخ
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(timestamp__date__gte=date_from)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(timestamp__date__lte=date_to)
            except ValueError:
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إضافة قائمة المستخدمين للفلتر
        from django.contrib.auth import get_user_model
        User = get_user_model()
        context['users'] = User.objects.filter(is_active=True).order_by('username')
        
        # إضافة أنواع العمليات
        from .models import AuditLog
        context['action_types'] = AuditLog.ACTION_TYPES
        
        # إضافة أنواع المحتوى المختلفة
        context['content_types'] = AuditLog.objects.values_list('content_type', flat=True).distinct()
        
        # إضافة فلاتر البحث الحالية
        context['current_filters'] = {
            'user': self.request.GET.get('user', ''),
            'action_type': self.request.GET.get('action_type', ''),
            'content_type': self.request.GET.get('content_type', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
        }
        
        return context


@require_http_methods(["POST"])
@login_required
def sync_balances_view(request):
    """مزامنة أرصدة البنوك والصناديق"""
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'غير مصرح لك بهذه العملية'})
    
    try:
        from banks.models import BankAccount
        from cashboxes.models import Cashbox
        
        banks_updated = 0
        cashboxes_updated = 0
        
        # مزامنة أرصدة البنوك
        bank_accounts = BankAccount.objects.filter(is_active=True)
        for account in bank_accounts:
            old_balance = account.balance
            new_balance = account.sync_balance()
            if old_balance != new_balance:
                banks_updated += 1
        
        # مزامنة أرصدة الصناديق
        cashboxes = Cashbox.objects.filter(is_active=True)
        for cashbox in cashboxes:
            old_balance = cashbox.balance
            new_balance = cashbox.sync_balance()
            if old_balance != new_balance:
                cashboxes_updated += 1
        
        return JsonResponse({
            'success': True,
            'banks_updated': banks_updated,
            'cashboxes_updated': cashboxes_updated
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def backup_export_view(request):
    """صفحة تصدير النسخة الاحتياطية الجديدة"""
    if not request.user.is_superuser:
        raise PermissionDenied("يجب أن تكون مدير نظام للوصول لهذه الصفحة")
    
    context = {
        'page_title': _('تصدير النسخة الاحتياطية'),
    }
    return render(request, 'core/backup_export.html', context)


@login_required
def export_backup_data(request):
    """تصدير البيانات بصيغ متعددة - JSON, Excel, CSV"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'يجب أن تكون مدير نظام'}, status=403)
    
    # الحصول على نوع التصدير المطلوب
    export_format = request.GET.get('format', 'json').lower()
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # إعداد البيانات للتصدير
        backup_data = {
            'export_info': {
                'version': '1.0',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'exported_by': request.user.username,
                'system': 'Triangle Accounting'
            },
            'data': {}
        }
        
        # تصدير المستخدمين
        users = User.objects.all()
        backup_data['data']['users'] = []
        for user in users:
            backup_data['data']['users'].append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S') if user.date_joined else None,
            })
        
        # تصدير العملات
        try:
            from settings.models import Currency
            currencies = Currency.objects.all()
            backup_data['data']['currencies'] = []
            for currency in currencies:
                backup_data['data']['currencies'].append({
                    'id': currency.id,
                    'code': currency.code,
                    'name': currency.name,
                    'symbol': currency.symbol,
                    'is_base_currency': currency.is_base_currency,
                    'exchange_rate': float(currency.exchange_rate) if currency.exchange_rate else 1.0,
                    'is_active': currency.is_active,
                    'decimal_places': getattr(currency, 'decimal_places', 2),
                })
        except (ImportError, AttributeError) as e:
            backup_data['data']['currencies'] = []
            print(f"تحذير: لا يمكن تصدير العملات: {str(e)}")
        
        # تصدير إعدادات الشركة
        try:
            from settings.models import CompanySettings
            company_settings = CompanySettings.objects.all()
            backup_data['data']['company_settings'] = []
            for setting in company_settings:
                backup_data['data']['company_settings'].append({
                    'id': setting.id,
                    'company_name': setting.company_name,
                    'company_name_en': getattr(setting, 'company_name_en', ''),
                    'tax_number': setting.tax_number,
                    'commercial_register': getattr(setting, 'commercial_register', ''),
                    'phone': setting.phone,
                    'email': setting.email,
                    'address': setting.address,
                    'city': getattr(setting, 'city', ''),
                    'country': getattr(setting, 'country', ''),
                })
        except (ImportError, AttributeError) as e:
            backup_data['data']['company_settings'] = []
            print(f"تحذير: لا يمكن تصدير إعدادات الشركة: {str(e)}")
        
        # إحصائيات التصدير
        total_records = (
            len(backup_data['data']['users']) + 
            len(backup_data['data']['currencies']) + 
            len(backup_data['data']['company_settings'])
        )
        
        backup_data['export_info']['total_records'] = total_records
        backup_data['export_info']['tables_exported'] = ['users', 'currencies', 'company_settings']
        
        # إنشاء اسم الملف
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # إنشاء الاستجابة حسب نوع التصدير
        if export_format == 'json':
            filename = f"triangle_backup_{timestamp}.json"
            json_content = json.dumps(backup_data, ensure_ascii=False, indent=2)
            
            response = HttpResponse(
                json_content,
                content_type='application/json; charset=utf-8'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
        elif export_format == 'excel' and OPENPYXL_AVAILABLE:
            filename = f"triangle_backup_{timestamp}.xlsx"
            response = create_excel_backup(backup_data, filename)
            
        elif export_format == 'csv':
            filename = f"triangle_backup_{timestamp}.csv"
            response = create_csv_backup(backup_data, filename)
            
        else:
            if export_format == 'excel' and not OPENPYXL_AVAILABLE:
                return JsonResponse({'error': 'مكتبة Excel غير متوفرة'}, status=400)
            else:
                return JsonResponse({'error': 'صيغة تصدير غير مدعومة'}, status=400)
        
        # تسجيل في السجل
        try:
            AuditLog.objects.create(
                user=request.user,
                action_type='export',
                content_type='Backup',
                description=f'تصدير نسخة احتياطية ({export_format.upper()}) - {total_records} سجل'
            )
        except:
            pass
        
        return response
        
    except Exception as e:
        return JsonResponse({'error': f'حدث خطأ: {str(e)}'}, status=500)


def create_excel_backup(backup_data, filename):
    """إنشاء ملف Excel للنسخة الاحتياطية"""
    wb = Workbook()
    wb.remove(wb.active)  # حذف الورقة الافتراضية
    
    # تنسيق الرؤوس
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    # ورقة المعلومات العامة
    info_ws = wb.create_sheet("معلومات التصدير")
    info_data = [
        ["المعلومة", "القيمة"],
        ["نسخة النظام", backup_data['export_info']['version']],
        ["تاريخ التصدير", backup_data['export_info']['timestamp']],
        ["المستخدم", backup_data['export_info']['exported_by']],
        ["النظام", backup_data['export_info']['system']],
        ["إجمالي السجلات", backup_data['export_info']['total_records']],
        ["الجداول", ', '.join(backup_data['export_info']['tables_exported'])],
    ]
    
    for row_num, row_data in enumerate(info_data, 1):
        for col_num, value in enumerate(row_data, 1):
            cell = info_ws.cell(row=row_num, column=col_num, value=value)
            if row_num == 1:  # رؤوس الأعمدة
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
    
    # ورقة المستخدمين
    if backup_data['data']['users']:
        users_ws = wb.create_sheet("المستخدمين")
        users_headers = ["الرقم", "اسم المستخدم", "البريد الإلكتروني", "الاسم الأول", "الاسم الأخير", "نشط", "موظف", "مدير", "تاريخ الانضمام"]
        
        # إضافة الرؤوس
        for col_num, header in enumerate(users_headers, 1):
            cell = users_ws.cell(row=1, column=col_num, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # إضافة البيانات
        for row_num, user in enumerate(backup_data['data']['users'], 2):
            users_ws.cell(row=row_num, column=1, value=user['id'])
            users_ws.cell(row=row_num, column=2, value=user['username'])
            users_ws.cell(row=row_num, column=3, value=user['email'])
            users_ws.cell(row=row_num, column=4, value=user['first_name'])
            users_ws.cell(row=row_num, column=5, value=user['last_name'])
            users_ws.cell(row=row_num, column=6, value="نعم" if user['is_active'] else "لا")
            users_ws.cell(row=row_num, column=7, value="نعم" if user['is_staff'] else "لا")
            users_ws.cell(row=row_num, column=8, value="نعم" if user['is_superuser'] else "لا")
            users_ws.cell(row=row_num, column=9, value=user['date_joined'])
    
    # ورقة العملات
    if backup_data['data']['currencies']:
        currencies_ws = wb.create_sheet("العملات")
        currencies_headers = ["الرقم", "الرمز", "الاسم", "الرمز المختصر", "عملة أساسية", "سعر الصرف", "نشط", "الخانات العشرية"]
        
        # إضافة الرؤوس
        for col_num, header in enumerate(currencies_headers, 1):
            cell = currencies_ws.cell(row=1, column=col_num, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # إضافة البيانات
        for row_num, currency in enumerate(backup_data['data']['currencies'], 2):
            currencies_ws.cell(row=row_num, column=1, value=currency['id'])
            currencies_ws.cell(row=row_num, column=2, value=currency['code'])
            currencies_ws.cell(row=row_num, column=3, value=currency['name'])
            currencies_ws.cell(row=row_num, column=4, value=currency['symbol'])
            currencies_ws.cell(row=row_num, column=5, value="نعم" if currency['is_base_currency'] else "لا")
            currencies_ws.cell(row=row_num, column=6, value=currency['exchange_rate'])
            currencies_ws.cell(row=row_num, column=7, value="نعم" if currency['is_active'] else "لا")
            currencies_ws.cell(row=row_num, column=8, value=currency['decimal_places'])
    
    # ورقة إعدادات الشركة
    if backup_data['data']['company_settings']:
        company_ws = wb.create_sheet("إعدادات الشركة")
        company_headers = ["الرقم", "اسم الشركة", "اسم الشركة (إنجليزي)", "الرقم الضريبي", "السجل التجاري", "الهاتف", "البريد الإلكتروني", "العنوان", "المدينة", "الدولة"]
        
        # إضافة الرؤوس
        for col_num, header in enumerate(company_headers, 1):
            cell = company_ws.cell(row=1, column=col_num, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # إضافة البيانات
        for row_num, setting in enumerate(backup_data['data']['company_settings'], 2):
            company_ws.cell(row=row_num, column=1, value=setting['id'])
            company_ws.cell(row=row_num, column=2, value=setting['company_name'])
            company_ws.cell(row=row_num, column=3, value=setting['company_name_en'])
            company_ws.cell(row=row_num, column=4, value=setting['tax_number'])
            company_ws.cell(row=row_num, column=5, value=setting['commercial_register'])
            company_ws.cell(row=row_num, column=6, value=setting['phone'])
            company_ws.cell(row=row_num, column=7, value=setting['email'])
            company_ws.cell(row=row_num, column=8, value=setting['address'])
            company_ws.cell(row=row_num, column=9, value=setting['city'])
            company_ws.cell(row=row_num, column=10, value=setting['country'])
    
    # حفظ الملف في الذاكرة
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


def create_csv_backup(backup_data, filename):
    """إنشاء ملف CSV للنسخة الاحتياطية"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # معلومات التصدير
    writer.writerow(["=== معلومات التصدير ==="])
    writer.writerow(["نسخة النظام", backup_data['export_info']['version']])
    writer.writerow(["تاريخ التصدير", backup_data['export_info']['timestamp']])
    writer.writerow(["المستخدم", backup_data['export_info']['exported_by']])
    writer.writerow(["النظام", backup_data['export_info']['system']])
    writer.writerow(["إجمالي السجلات", backup_data['export_info']['total_records']])
    writer.writerow([])
    
    # المستخدمين
    if backup_data['data']['users']:
        writer.writerow(["=== المستخدمين ==="])
        writer.writerow(["الرقم", "اسم المستخدم", "البريد الإلكتروني", "الاسم الأول", "الاسم الأخير", "نشط", "موظف", "مدير", "تاريخ الانضمام"])
        
        for user in backup_data['data']['users']:
            writer.writerow([
                user['id'], user['username'], user['email'], user['first_name'], user['last_name'],
                "نعم" if user['is_active'] else "لا",
                "نعم" if user['is_staff'] else "لا",
                "نعم" if user['is_superuser'] else "لا",
                user['date_joined']
            ])
        writer.writerow([])
    
    # العملات
    if backup_data['data']['currencies']:
        writer.writerow(["=== العملات ==="])
        writer.writerow(["الرقم", "الرمز", "الاسم", "الرمز المختصر", "عملة أساسية", "سعر الصرف", "نشط", "الخانات العشرية"])
        
        for currency in backup_data['data']['currencies']:
            writer.writerow([
                currency['id'], currency['code'], currency['name'], currency['symbol'],
                "نعم" if currency['is_base_currency'] else "لا",
                currency['exchange_rate'],
                "نعم" if currency['is_active'] else "لا",
                currency['decimal_places']
            ])
        writer.writerow([])
    
    # إعدادات الشركة
    if backup_data['data']['company_settings']:
        writer.writerow(["=== إعدادات الشركة ==="])
        writer.writerow(["الرقم", "اسم الشركة", "اسم الشركة (إنجليزي)", "الرقم الضريبي", "السجل التجاري", "الهاتف", "البريد الإلكتروني", "العنوان", "المدينة", "الدولة"])
        
        for setting in backup_data['data']['company_settings']:
            writer.writerow([
                setting['id'], setting['company_name'], setting['company_name_en'], setting['tax_number'],
                setting['commercial_register'], setting['phone'], setting['email'], setting['address'],
                setting['city'], setting['country']
            ])
    
    # إنشاء الاستجابة
    csv_content = output.getvalue()
    output.close()
    
    response = HttpResponse(
        csv_content.encode('utf-8-sig'),  # UTF-8 with BOM للدعم العربي
        content_type='text/csv; charset=utf-8'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
def import_backup_data(request):
    """استيراد البيانات من ملف النسخة الاحتياطية"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'يجب أن تكون مدير نظام'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'يجب استخدام POST'}, status=405)
    
    if 'backup_file' not in request.FILES:
        return JsonResponse({'error': 'لم يتم اختيار ملف'}, status=400)
    
    uploaded_file = request.FILES['backup_file']
    file_extension = uploaded_file.name.lower().split('.')[-1]
    
    try:
        result = {'imported_records': 0, 'errors': [], 'success': True}
        
        if file_extension == 'json':
            result = import_from_json(uploaded_file, request.user)
        elif file_extension == 'xlsx':
            result = import_from_excel(uploaded_file, request.user)
        elif file_extension == 'csv':
            result = import_from_csv(uploaded_file, request.user)
        else:
            return JsonResponse({'error': 'صيغة ملف غير مدعومة'}, status=400)
        
        # تسجيل في السجل
        try:
            AuditLog.objects.create(
                user=request.user,
                action_type='import',
                content_type='Backup',
                description=f'استيراد نسخة احتياطية ({file_extension.upper()}) - {result["imported_records"]} سجل'
            )
        except:
            pass
            
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'error': f'حدث خطأ: {str(e)}', 'success': False}, status=500)


def import_from_json(uploaded_file, user):
    """استيراد البيانات من ملف JSON"""
    try:
        file_content = uploaded_file.read().decode('utf-8')
        data = json.loads(file_content)
        
        imported_count = 0
        errors = []
        
        # التحقق من صحة البيانات
        if 'data' not in data:
            raise ValueError('ملف JSON غير صحيح - لا يحتوي على قسم البيانات')
        
        # استيراد العملات
        if 'currencies' in data['data']:
            try:
                from settings.models import Currency
                currencies_imported = 0
                for currency_data in data['data']['currencies']:
                    currency, created = Currency.objects.get_or_create(
                        code=currency_data['code'],
                        defaults={
                            'name': currency_data['name'],
                            'symbol': currency_data.get('symbol', ''),
                            'is_base_currency': currency_data.get('is_base_currency', False),
                            'exchange_rate': currency_data.get('exchange_rate', 1.0),
                            'is_active': currency_data.get('is_active', True),
                            'decimal_places': currency_data.get('decimal_places', 2),
                        }
                    )
                    if created:
                        currencies_imported += 1
                
                imported_count += currencies_imported
                    
            except Exception as e:
                errors.append(f"خطأ في استيراد العملات: {str(e)}")
        
        # استيراد إعدادات الشركة
        if 'company_settings' in data['data']:
            try:
                from settings.models import CompanySettings
                settings_imported = 0
                for setting_data in data['data']['company_settings']:
                    # تحديث أو إنشاء إعدادات الشركة
                    setting, created = CompanySettings.objects.update_or_create(
                        id=setting_data.get('id'),
                        defaults={
                            'company_name': setting_data.get('company_name', ''),
                            'tax_number': setting_data.get('tax_number', ''),
                            'phone': setting_data.get('phone', ''),
                            'email': setting_data.get('email', ''),
                            'address': setting_data.get('address', ''),
                        }
                    )
                    if created:
                        settings_imported += 1
                
                imported_count += settings_imported
                    
            except Exception as e:
                errors.append(f"خطأ في استيراد إعدادات الشركة: {str(e)}")
        
        return {
            'success': True,
            'imported_records': imported_count,
            'errors': errors,
            'message': f'تم استيراد {imported_count} سجل بنجاح'
        }
        
    except json.JSONDecodeError:
        return {'success': False, 'error': 'ملف JSON تالف أو غير صحيح'}
    except Exception as e:
        return {'success': False, 'error': f'خطأ في معالجة ملف JSON: {str(e)}'}


def import_from_excel(uploaded_file, user):
    """استيراد البيانات من ملف Excel"""
    if not OPENPYXL_AVAILABLE:
        return {'success': False, 'error': 'مكتبة Excel غير متوفرة'}
    
    try:
        from openpyxl import load_workbook
        wb = load_workbook(uploaded_file)
        
        imported_count = 0
        errors = []
        
        # استيراد العملات من ورقة "العملات"
        if 'العملات' in wb.sheetnames:
            try:
                from settings.models import Currency
                ws = wb['العملات']
                currencies_imported = 0
                
                # تخطي صف الرؤوس
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if row[1]:  # التحقق من وجود رمز العملة
                        currency, created = Currency.objects.get_or_create(
                            code=row[1],
                            defaults={
                                'name': row[2] or '',
                                'symbol': row[3] or '',
                                'is_base_currency': row[4] == 'نعم' if row[4] else False,
                                'exchange_rate': float(row[5]) if row[5] else 1.0,
                                'is_active': row[6] == 'نعم' if row[6] else True,
                                'decimal_places': int(row[7]) if row[7] else 2,
                            }
                        )
                        if created:
                            currencies_imported += 1
                
                imported_count += currencies_imported
                    
            except Exception as e:
                errors.append(f"خطأ في استيراد العملات من Excel: {str(e)}")
        
        return {
            'success': True,
            'imported_records': imported_count,
            'errors': errors,
            'message': f'تم استيراد {imported_count} سجل من Excel بنجاح'
        }
        
    except Exception as e:
        return {'success': False, 'error': f'خطأ في معالجة ملف Excel: {str(e)}'}


def import_from_csv(uploaded_file, user):
    """استيراد البيانات من ملف CSV"""
    try:
        file_content = uploaded_file.read().decode('utf-8-sig')
        lines = file_content.split('\n')
        
        imported_count = 0
        errors = []
        current_section = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith('=== العملات ==='):
                current_section = 'currencies'
                i += 1
                continue
            elif line.startswith('=== إعدادات الشركة ==='):
                current_section = 'company_settings'
                i += 1
                continue
            elif line.startswith('===') or not line:
                current_section = None
                i += 1
                continue
            
            if current_section and line:
                try:
                    if current_section == 'currencies':
                        # تخطي صف الرؤوس
                        if 'الرقم' in line:
                            i += 1
                            continue
                            
                        from settings.models import Currency
                        reader = csv.reader([line])
                        row = next(reader)
                        
                        if len(row) >= 8 and row[1]:
                            currency, created = Currency.objects.get_or_create(
                                code=row[1],
                                defaults={
                                    'name': row[2],
                                    'symbol': row[3],
                                    'is_base_currency': row[4] == 'نعم',
                                    'exchange_rate': float(row[5]) if row[5] else 1.0,
                                    'is_active': row[6] == 'نعم',
                                    'decimal_places': int(row[7]) if row[7] else 2,
                                }
                            )
                            if created:
                                imported_count += 1
                                
                except Exception as e:
                    errors.append(f"خطأ في السطر {i+1}: {str(e)}")
            
            i += 1
        
        return {
            'success': True,
            'imported_records': imported_count,
            'errors': errors,
            'message': f'تم استيراد {imported_count} سجل من CSV بنجاح'
        }
        
    except Exception as e:
        return {'success': False, 'error': f'خطأ في معالجة ملف CSV: {str(e)}'}


@login_required
@require_http_methods(["POST"])
def extend_session_api(request):
    """API لتمديد الجلسة"""
    try:
        # تحديث وقت آخر نشاط في الجلسة
        request.session['last_activity'] = django_timezone.now().isoformat()
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'message': 'تم تمديد الجلسة بنجاح',
            'timestamp': django_timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'خطأ في تمديد الجلسة: {str(e)}'
        }, status=500)

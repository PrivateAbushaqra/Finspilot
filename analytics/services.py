from django.db.models import Sum, Count, Avg, Q, F
from django.utils.translation import gettext as _
from decimal import Decimal
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta


class AnalyticsService:
    """Base analytics service with common utilities"""
    
    @staticmethod
    def parse_period(period_type, start_date=None, end_date=None, year=None, quarter=None, month=None):
        """
        Parse period based on type and return start and end dates
        """
        today = date.today()
        
        if period_type == 'custom' and start_date and end_date:
            return start_date, end_date
        elif period_type == 'monthly' and year and month:
            start = date(year, month, 1)
            if month == 12:
                end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(year, month + 1, 1) - timedelta(days=1)
            return start, end
        elif period_type == 'quarterly' and year and quarter:
            start_month = (quarter - 1) * 3 + 1
            start = date(year, start_month, 1)
            end_month = start_month + 2
            if end_month > 12:
                end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(year, end_month + 1, 1) - timedelta(days=1)
            return start, end
        elif period_type == 'yearly' and year:
            start = date(year, 1, 1)
            end = date(year, 12, 31)
            return start, end
        else:
            # Default to current month
            start = date(today.year, today.month, 1)
            if today.month == 12:
                end = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(today.year, today.month + 1, 1) - timedelta(days=1)
            return start, end
    
    @staticmethod
    def get_previous_period(start_date, end_date):
        """Calculate previous period dates for comparison"""
        delta = end_date - start_date
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - delta
        return prev_start, prev_end
    
    @staticmethod
    def calculate_growth_rate(current, previous):
        """Calculate growth rate percentage"""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 2)
    
    @staticmethod
    def safe_decimal(value):
        """Convert value to Decimal safely"""
        if value is None:
            return Decimal('0')
        try:
            return Decimal(str(value))
        except:
            return Decimal('0')


class SalesAnalyticsService(AnalyticsService):
    """Sales analytics service"""
    
    def __init__(self, start_date, end_date, user=None):
        self.start_date = start_date
        self.end_date = end_date
        self.user = user
    
    def get_sales_overview(self):
        """Get overall sales metrics"""
        from sales.models import SalesInvoice, SalesInvoiceItem, SalesReturn
        
        # Filter sales invoices
        invoices = SalesInvoice.objects.filter(
            date__range=[self.start_date, self.end_date]
        )
        
        # Filter by user if not admin (show only their own invoices)
        if self.user and not (self.user.is_superuser or self.user.user_type == 'admin'):
            invoices = invoices.filter(created_by=self.user)
        
        total_sales = invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        invoice_count = invoices.count()
        avg_invoice_value = total_sales / invoice_count if invoice_count > 0 else Decimal('0')
        
        # Returns impact
        returns = SalesReturn.objects.filter(
            date__range=[self.start_date, self.end_date]
        )
        total_returns = returns.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        net_sales = total_sales - total_returns
        
        # Previous period comparison
        prev_start, prev_end = self.get_previous_period(self.start_date, self.end_date)
        prev_invoices = SalesInvoice.objects.filter(
            date__range=[prev_start, prev_end]
        )
        if self.user and not (self.user.is_superuser or self.user.user_type == 'admin'):
            prev_invoices = prev_invoices.filter(created_by=self.user)
        
        prev_total = prev_invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        growth_rate = self.calculate_growth_rate(float(total_sales), float(prev_total))
        
        return {
            'total_sales': total_sales,
            'invoice_count': invoice_count,
            'avg_invoice_value': avg_invoice_value,
            'total_returns': total_returns,
            'net_sales': net_sales,
            'growth_rate': growth_rate,
            'previous_period_sales': prev_total,
        }
    
    def get_product_analytics(self):
        """Analyze sales by product"""
        from sales.models import SalesInvoiceItem
        
        items = SalesInvoiceItem.objects.filter(
            invoice__date__range=[self.start_date, self.end_date]
        )
        
        if self.user and not (self.user.is_superuser or self.user.user_type == 'admin'):
            items = items.filter(invoice__created_by=self.user)
        
        product_data = items.values('product__name', 'product__id').annotate(
            total_quantity=Sum('quantity'),
            total_amount=Sum(F('quantity') * F('unit_price')),
            order_count=Count('invoice', distinct=True)
        ).order_by('-total_amount')[:20]
        
        return list(product_data)
    
    def get_category_analytics(self):
        """Analyze sales by category"""
        from sales.models import SalesInvoiceItem
        
        items = SalesInvoiceItem.objects.filter(
            invoice__date__range=[self.start_date, self.end_date]
        )
        
        if self.user and not (self.user.is_superuser or self.user.user_type == 'admin'):
            items = items.filter(invoice__created_by=self.user)
        
        category_data = items.values('product__category__name').annotate(
            total_amount=Sum(F('quantity') * F('unit_price')),
            total_quantity=Sum('quantity'),
        ).order_by('-total_amount')
        
        return list(category_data)
    
    def get_customer_analytics(self):
        """Analyze sales by customer"""
        from sales.models import SalesInvoice
        
        invoices = SalesInvoice.objects.filter(
            date__range=[self.start_date, self.end_date]
        )
        
        if self.user and not (self.user.is_superuser or self.user.user_type == 'admin'):
            invoices = invoices.filter(created_by=self.user)
        
        customer_data = invoices.values('customer__name', 'customer__id').annotate(
            total_amount=Sum('total_amount'),
            invoice_count=Count('id')
        ).order_by('-total_amount')[:20]
        
        # Calculate average manually
        for item in customer_data:
            if item['invoice_count'] > 0:
                item['avg_invoice'] = float(item['total_amount']) / item['invoice_count']
            else:
                item['avg_invoice'] = 0
        
        return list(customer_data)
    
    def get_sales_representative_analytics(self):
        """Analyze sales by user (created_by)"""
        from sales.models import SalesInvoice
        
        invoices = SalesInvoice.objects.filter(
            date__range=[self.start_date, self.end_date]
        )
        
        # Filter by current user if not admin
        if self.user and not (self.user.is_superuser or self.user.user_type == 'admin'):
            invoices = invoices.filter(created_by=self.user)
        
        # Group by created_by user
        rep_data = invoices.values(
            'created_by__first_name',
            'created_by__last_name',
            'created_by__id'
        ).annotate(
            total_amount=Sum('total_amount'),
            invoice_count=Count('id')
        ).order_by('-total_amount')
        
        # Calculate average manually
        rep_list = list(rep_data)
        for item in rep_list:
            if item['invoice_count'] > 0:
                item['avg_invoice'] = float(item['total_amount']) / item['invoice_count']
            else:
                item['avg_invoice'] = 0
        
        return rep_list
    
    def generate_insights(self, overview_data, product_data, customer_data):
        """Generate AI insights based on sales data"""
        insights = []
        
        # Growth insight
        if overview_data['growth_rate'] > 10:
            insights.append({
                'type': 'positive',
                'message': _('Sales show strong growth of %(rate)s%% compared to previous period') % {
                    'rate': overview_data['growth_rate']
                }
            })
        elif overview_data['growth_rate'] < -10:
            insights.append({
                'type': 'warning',
                'message': _('Sales declined by %(rate)s%% compared to previous period') % {
                    'rate': abs(overview_data['growth_rate'])
                }
            })
        
        # Returns impact
        if overview_data['total_returns'] > 0:
            return_rate = (float(overview_data['total_returns']) / float(overview_data['total_sales'])) * 100
            if return_rate > 5:
                insights.append({
                    'type': 'warning',
                    'message': _('High return rate detected: %(rate).1f%% of sales') % {'rate': return_rate}
                })
        
        # Top product concentration
        if product_data and len(product_data) > 0:
            top_product_share = (float(product_data[0]['total_amount']) / float(overview_data['total_sales'])) * 100
            if top_product_share > 30:
                insights.append({
                    'type': 'info',
                    'message': _('Top product accounts for %(share).1f%% of total sales') % {'share': top_product_share}
                })
        
        # Customer concentration
        if customer_data and len(customer_data) > 0:
            top_customer_share = (float(customer_data[0]['total_amount']) / float(overview_data['total_sales'])) * 100
            if top_customer_share > 25:
                insights.append({
                    'type': 'warning',
                    'message': _('High dependency on top customer: %(share).1f%% of sales') % {'share': top_customer_share}
                })
        
        # Average invoice value trend
        if overview_data['avg_invoice_value'] < 100:
            insights.append({
                'type': 'info',
                'message': _('Low average invoice value may indicate retail-focused sales')
            })
        
        return insights


class PurchaseAnalyticsService(AnalyticsService):
    """Purchase analytics service"""
    
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
    
    def get_purchase_overview(self):
        """Get overall purchase metrics"""
        from purchases.models import PurchaseInvoice, PurchaseReturn
        
        invoices = PurchaseInvoice.objects.filter(
            date__range=[self.start_date, self.end_date]
        )
        
        total_purchases = invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        invoice_count = invoices.count()
        avg_invoice_value = total_purchases / invoice_count if invoice_count > 0 else Decimal('0')
        
        # Returns
        returns = PurchaseReturn.objects.filter(
            date__range=[self.start_date, self.end_date]
        )
        total_returns = returns.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        net_purchases = total_purchases - total_returns
        
        # Previous period
        prev_start, prev_end = self.get_previous_period(self.start_date, self.end_date)
        prev_invoices = PurchaseInvoice.objects.filter(
            date__range=[prev_start, prev_end]
        )
        prev_total = prev_invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        growth_rate = self.calculate_growth_rate(float(total_purchases), float(prev_total))
        
        return {
            'total_purchases': total_purchases,
            'invoice_count': invoice_count,
            'avg_invoice_value': avg_invoice_value,
            'total_returns': total_returns,
            'net_purchases': net_purchases,
            'growth_rate': growth_rate,
            'previous_period_purchases': prev_total,
        }
    
    def get_product_analytics(self):
        """Analyze purchases by product"""
        from purchases.models import PurchaseInvoiceItem
        
        items = PurchaseInvoiceItem.objects.filter(
            invoice__date__range=[self.start_date, self.end_date]
        )
        
        product_data = items.values('product__name', 'product__id').annotate(
            total_quantity=Sum('quantity'),
            total_amount=Sum(F('quantity') * F('unit_price')),
            order_count=Count('invoice', distinct=True)
        ).order_by('-total_amount')[:20]
        
        return list(product_data)
    
    def get_category_analytics(self):
        """Analyze purchases by category"""
        from purchases.models import PurchaseInvoiceItem
        
        items = PurchaseInvoiceItem.objects.filter(
            invoice__date__range=[self.start_date, self.end_date]
        )
        
        category_data = items.values('product__category__name').annotate(
            total_amount=Sum(F('quantity') * F('unit_price')),
            total_quantity=Sum('quantity'),
        ).order_by('-total_amount')
        
        return list(category_data)
    
    def get_supplier_analytics(self):
        """Analyze purchases by supplier"""
        from purchases.models import PurchaseInvoice
        
        invoices = PurchaseInvoice.objects.filter(
            date__range=[self.start_date, self.end_date]
        )
        
        supplier_data = invoices.values('supplier__name', 'supplier__id').annotate(
            total_amount=Sum('total_amount'),
            invoice_count=Count('id')
        ).order_by('-total_amount')[:20]
        
        # Calculate average manually
        supplier_list = list(supplier_data)
        for item in supplier_list:
            if item['invoice_count'] > 0:
                item['avg_invoice'] = float(item['total_amount']) / item['invoice_count']
            else:
                item['avg_invoice'] = 0
        
        return supplier_list
    
    def generate_insights(self, overview_data, supplier_data):
        """Generate AI insights for purchases"""
        insights = []
        
        # Growth insight
        if overview_data['growth_rate'] > 15:
            insights.append({
                'type': 'warning',
                'message': _('Purchases increased by %(rate)s%% - monitor inventory levels') % {
                    'rate': overview_data['growth_rate']
                }
            })
        elif overview_data['growth_rate'] < -15:
            insights.append({
                'type': 'info',
                'message': _('Purchases decreased by %(rate)s%% - verify supply chain') % {
                    'rate': abs(overview_data['growth_rate'])
                }
            })
        
        # Supplier concentration
        if supplier_data and len(supplier_data) > 0:
            top_supplier_share = (float(supplier_data[0]['total_amount']) / float(overview_data['total_purchases'])) * 100
            if top_supplier_share > 40:
                insights.append({
                    'type': 'warning',
                    'message': _('High dependency on single supplier: %(share).1f%% of purchases') % {'share': top_supplier_share}
                })
        
        return insights


class TaxAnalyticsService(AnalyticsService):
    """Tax analytics service"""
    
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
    
    def get_tax_overview(self):
        """Get overall tax metrics"""
        from sales.models import SalesInvoice, SalesReturn
        from purchases.models import PurchaseInvoice, PurchaseReturn
        
        # Sales tax
        sales_invoices = SalesInvoice.objects.filter(
            date__range=[self.start_date, self.end_date]
        )
        sales_tax = sales_invoices.aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
        
        # Sales returns tax
        sales_returns = SalesReturn.objects.filter(
            date__range=[self.start_date, self.end_date]
        )
        sales_return_tax = sales_returns.aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
        
        # Purchase tax
        purchase_invoices = PurchaseInvoice.objects.filter(
            date__range=[self.start_date, self.end_date]
        )
        purchase_tax = purchase_invoices.aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
        
        # Purchase returns tax
        purchase_returns = PurchaseReturn.objects.filter(
            date__range=[self.start_date, self.end_date]
        )
        purchase_return_tax = purchase_returns.aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
        
        # Net tax
        net_sales_tax = sales_tax - sales_return_tax
        net_purchase_tax = purchase_tax - purchase_return_tax
        net_tax_payable = net_sales_tax - net_purchase_tax
        
        return {
            'sales_tax': sales_tax,
            'sales_return_tax': sales_return_tax,
            'net_sales_tax': net_sales_tax,
            'purchase_tax': purchase_tax,
            'purchase_return_tax': purchase_return_tax,
            'net_purchase_tax': net_purchase_tax,
            'net_tax_payable': net_tax_payable,
        }
    
    def get_tax_by_document_type(self):
        """Get tax breakdown by document type"""
        overview = self.get_tax_overview()
        
        data = [
            {'type': 'Sales Invoices', 'amount': overview['sales_tax']},
            {'type': 'Sales Returns', 'amount': overview['sales_return_tax']},
            {'type': 'Purchase Invoices', 'amount': overview['purchase_tax']},
            {'type': 'Purchase Returns', 'amount': overview['purchase_return_tax']},
        ]
        
        return data
    
    def generate_insights(self, overview_data):
        """Generate tax insights"""
        insights = []
        
        # High tax burden
        if overview_data['net_tax_payable'] > 0:
            insights.append({
                'type': 'info',
                'message': _('Net tax payable: %(amount)s') % {
                    'amount': f"{overview_data['net_tax_payable']:,.2f}"
                }
            })
        
        # Tax credit available
        if overview_data['net_tax_payable'] < 0:
            insights.append({
                'type': 'positive',
                'message': _('Tax credit available: %(amount)s') % {
                    'amount': f"{abs(overview_data['net_tax_payable']):,.2f}"
                }
            })
        
        return insights


class CashFlowAnalyticsService(AnalyticsService):
    """Cash flow analytics service"""
    
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
    
    def get_cashflow_overview(self):
        """Get cash flow overview from banks and cashboxes"""
        from banks.models import BankTransaction
        from cashboxes.models import CashboxTransaction
        from receipts.models import PaymentReceipt
        from payments.models import PaymentVoucher
        
        # Bank transactions
        bank_inflows = BankTransaction.objects.filter(
            date__range=[self.start_date, self.end_date],
            transaction_type__in=['deposit', 'transfer_in']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        bank_outflows = BankTransaction.objects.filter(
            date__range=[self.start_date, self.end_date],
            transaction_type__in=['withdrawal', 'transfer_out']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Cashbox transactions
        cashbox_inflows = CashboxTransaction.objects.filter(
            date__range=[self.start_date, self.end_date],
            transaction_type__in=['deposit', 'transfer_in']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        cashbox_outflows = CashboxTransaction.objects.filter(
            date__range=[self.start_date, self.end_date],
            transaction_type__in=['withdrawal', 'transfer_out']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Receipt vouchers
        receipts = PaymentReceipt.objects.filter(
            date__range=[self.start_date, self.end_date]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Payment vouchers
        payments = PaymentVoucher.objects.filter(
            date__range=[self.start_date, self.end_date]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Calculate totals
        total_inflows = bank_inflows + cashbox_inflows + receipts
        total_outflows = bank_outflows + cashbox_outflows + payments
        net_cashflow = total_inflows - total_outflows
        
        # Calculate daily average
        days = (self.end_date - self.start_date).days + 1
        daily_avg_inflow = total_inflows / days if days > 0 else Decimal('0')
        daily_avg_outflow = total_outflows / days if days > 0 else Decimal('0')
        
        return {
            'total_inflows': total_inflows,
            'total_outflows': total_outflows,
            'net_cashflow': net_cashflow,
            'bank_inflows': bank_inflows,
            'bank_outflows': bank_outflows,
            'cashbox_inflows': cashbox_inflows,
            'cashbox_outflows': cashbox_outflows,
            'receipts': receipts,
            'payments': payments,
            'daily_avg_inflow': daily_avg_inflow,
            'daily_avg_outflow': daily_avg_outflow,
        }
    
    def get_bank_account_analytics(self):
        """Analyze cash flow by bank account"""
        from banks.models import BankTransaction
        
        transactions = BankTransaction.objects.filter(
            date__range=[self.start_date, self.end_date]
        )
        
        account_data = {}
        for trans in transactions:
            account_name = trans.bank_account.account_name
            if account_name not in account_data:
                account_data[account_name] = {'inflows': Decimal('0'), 'outflows': Decimal('0')}
            
            if trans.transaction_type in ['deposit', 'transfer_in']:
                account_data[account_name]['inflows'] += trans.amount
            else:
                account_data[account_name]['outflows'] += trans.amount
        
        result = []
        for name, data in account_data.items():
            result.append({
                'account_name': name,
                'inflows': data['inflows'],
                'outflows': data['outflows'],
                'net': data['inflows'] - data['outflows']
            })
        
        return result
    
    def get_cashbox_analytics(self):
        """Analyze cash flow by cashbox"""
        from cashboxes.models import CashboxTransaction
        
        transactions = CashboxTransaction.objects.filter(
            date__range=[self.start_date, self.end_date]
        )
        
        cashbox_data = {}
        for trans in transactions:
            cashbox_name = trans.cashbox.name
            if cashbox_name not in cashbox_data:
                cashbox_data[cashbox_name] = {'inflows': Decimal('0'), 'outflows': Decimal('0')}
            
            if trans.transaction_type in ['deposit', 'transfer_in']:
                cashbox_data[cashbox_name]['inflows'] += trans.amount
            else:
                cashbox_data[cashbox_name]['outflows'] += trans.amount
        
        result = []
        for name, data in cashbox_data.items():
            result.append({
                'cashbox_name': name,
                'inflows': data['inflows'],
                'outflows': data['outflows'],
                'net': data['inflows'] - data['outflows']
            })
        
        return result
    
    def generate_insights(self, overview_data):
        """Generate cash flow insights"""
        insights = []
        
        # Cash flow health
        if overview_data['net_cashflow'] < 0:
            insights.append({
                'type': 'warning',
                'message': _('Negative cash flow detected: %(amount)s deficit') % {
                    'amount': f"{abs(overview_data['net_cashflow']):,.2f}"
                }
            })
        elif overview_data['net_cashflow'] > 0:
            insights.append({
                'type': 'positive',
                'message': _('Positive cash flow: %(amount)s surplus') % {
                    'amount': f"{overview_data['net_cashflow']:,.2f}"
                }
            })
        
        # Outflow vs inflow ratio
        if overview_data['total_inflows'] > 0:
            outflow_ratio = (float(overview_data['total_outflows']) / float(overview_data['total_inflows'])) * 100
            if outflow_ratio > 90:
                insights.append({
                    'type': 'warning',
                    'message': _('High cash burn rate: Outflows are %(ratio).1f%% of inflows') % {'ratio': outflow_ratio}
                })
        
        return insights

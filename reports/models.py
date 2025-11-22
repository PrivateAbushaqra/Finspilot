from django.db import models
from django.utils.translation import gettext_lazy as _


class ReportAccessControl(models.Model):
	"""Simple model to hold custom report permissions."""
	created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

	class Meta:
		verbose_name = _('Report Access Control')
		verbose_name_plural = _('Report Access Controls')
		default_permissions = []  # No default permissions
		permissions = [
			('can_view_sales_reports', _('Can View Sales Reports')),
			('can_view_sales_by_representative_report', _('Can View Sales By Representative Report')),
			('can_view_purchase_reports', _('Can View Purchase Reports')),
			('can_view_tax_report', _('Can View Tax Report')),
			('can_view_profit_loss_report', _('Can View Profit and Loss Report')),
			('can_view_customer_statement', _('Can View Customer Statement')),
			('can_view_trial_balance', _('Can View Trial Balance')),
			('can_view_balance_sheet', _('Can View Balance Sheet')),
			('can_view_income_statement', _('Can View Income Statement')),
			('can_view_cash_flow_statement', _('Can View Cash Flow Statement')),
			('can_view_aging_report', _('Can View Aging Report')),
			('can_view_stock_balance_report', _('Can View Stock Balance Report')),
			('can_view_financial_ratios', _('Can View Financial Ratios')),
			('can_view_documents_report', _('Can View Documents Report')),
		]

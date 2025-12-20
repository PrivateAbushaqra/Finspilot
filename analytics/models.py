from django.db import models
from django.utils.translation import gettext_lazy as _


class AnalyticsPermissions(models.Model):
    """Model to hold AI Financial Intelligence permissions"""
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Analytics Permissions')
        verbose_name_plural = _('Analytics Permissions')
        default_permissions = []
        permissions = [
            ('view_ai_dashboard', _('Can View AI Dashboard')),
            ('view_sales_analytics', _('Can View Sales Analytics')),
            ('view_purchase_analytics', _('Can View Purchase Analytics')),
            ('view_tax_analytics', _('Can View Tax Analytics')),
            ('view_cashflow_analytics', _('Can View Cash Flow Analytics')),
            ('export_analytics_reports', _('Can Export Analytics Reports')),
        ]

    def __str__(self):
        return 'Analytics Permissions'

from django.db import models
from django.utils.translation import gettext_lazy as _


class ReportAccessControl(models.Model):
	"""Simple model to hold custom report permissions."""
	created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

	class Meta:
		verbose_name = _('Report Access Control')
		verbose_name_plural = _('Report Access Controls')
		permissions = [
			('can_view_customer_statement', _('View Customer Statement')),
		]

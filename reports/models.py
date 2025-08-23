from django.db import models
from django.utils.translation import gettext_lazy as _


class ReportAccessControl(models.Model):
	"""نموذج بسيط لحمل صلاحيات التقارير المخصصة."""
	created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

	class Meta:
		verbose_name = _('تحكم وصول التقارير')
		verbose_name_plural = _('تحكم وصول التقارير')
		permissions = [
			('can_view_customer_statement', _('عرض كشف حساب العملاء')),
		]

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reports'
    verbose_name = _('التقارير')

    def ready(self):
        # Auto-grant the custom report permission to admin and superadmin groups if they exist
        try:
            from django.db.models.signals import post_migrate
            from django.contrib.auth.models import Group, Permission
            from django.apps import apps

            def assign_perm(sender, **kwargs):
                try:
                    perm = Permission.objects.filter(codename='can_view_customer_statement', content_type__app_label='reports').first()
                    if not perm:
                        return
                    for name in ['admin', 'superadmin', 'Admin', 'Super Admin']:
                        grp = Group.objects.filter(name=name).first()
                        if grp and not grp.permissions.filter(id=perm.id).exists():
                            grp.permissions.add(perm)
                except Exception:
                    pass

            post_migrate.connect(assign_perm, sender=apps.get_app_config('reports'))
        except Exception:
            pass

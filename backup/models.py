from django.db import models
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

class BackupManager(models.Model):
    """نموذج إدارة النسخ الاحتياطي لإنشاء الصلاحيات المطلوبة"""
    
    class Meta:
        managed = False  # هذا النموذج لن ينشئ جدول في قاعدة البيانات
        permissions = [
            ('can_restore_backup', _('Can restore backup')),
            ('can_delete_advanced_data', _('Can delete advanced data tables')),
            ('delete_backup', _('Can delete backup files')),
        ]
        verbose_name = _('Backup Manager')
        verbose_name_plural = _('Backup Managers')
        default_permissions = ()  # لا نريد الصلاحيات الافتراضية

    def __str__(self):
        return "Backup Manager"

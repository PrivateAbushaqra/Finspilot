from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

class Document(models.Model):
    title = models.CharField(max_length=255, verbose_name="عنوان المستند")
    file = models.FileField(upload_to='documents/', verbose_name="الملف")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="رفع بواسطة")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الرفع")

    # Generic relation for linking to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "مستند"
        verbose_name_plural = "المستندات"
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

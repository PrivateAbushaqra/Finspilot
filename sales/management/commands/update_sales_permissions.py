from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django.utils.translation import activate
from sales.models import SalesInvoice, SalesReturn, SalesCreditNote


class Command(BaseCommand):
    help = 'تحديث أسماء صلاحيات المبيعات'

    def handle(self, *args, **options):
        # تفعيل اللغة العربية
        activate('ar')
        
        # حذف الصلاحيات القديمة وإعادة إنشائها
        models = [SalesInvoice, SalesReturn, SalesCreditNote]
        
        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            
            # حذف جميع الصلاحيات القديمة
            Permission.objects.filter(content_type=content_type).delete()
            self.stdout.write(f'تم حذف صلاحيات {model._meta.verbose_name}')
            
            # إعادة إنشاء الصلاحيات من Meta.permissions
            if hasattr(model._meta, 'permissions'):
                for codename, name in model._meta.permissions:
                    # name هو lazy string، نحتاج إلى تحويله إلى نص عادي
                    permission_name = str(name)
                    Permission.objects.create(
                        codename=codename,
                        name=permission_name,
                        content_type=content_type
                    )
                    self.stdout.write(f'  ✓ {codename}: {permission_name}')
        
        self.stdout.write(self.style.SUCCESS('تم تحديث جميع الصلاحيات بنجاح'))

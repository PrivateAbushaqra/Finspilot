"""
أمر إداري لتصحيح أسماء صلاحيات المنتجات في قاعدة البيانات
يقوم بتحديث أسماء الصلاحيات من العربية إلى الإنجليزية لتتوافق مع models.py
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _


class Command(BaseCommand):
    help = 'Fix product permissions names in database to match models.py'

    def handle(self, *args, **options):
        """تنفيذ الأمر"""
        
        # جلب ContentType للمنتجات والفئات
        try:
            category_ct = ContentType.objects.get(app_label='products', model='category')
        except ContentType.DoesNotExist:
            self.stdout.write(self.style.ERROR('ContentType for products.category not found'))
            return
        
        # تعريف الصلاحيات الصحيحة كما هي في models.py
        correct_permissions = {
            'can_view_products': 'Can View Products',
            'can_add_products': 'Can Add Products',
            'can_edit_products': 'Can Edit Products',
            'can_delete_products': 'Can Delete Products',
            'can_view_product_categories': 'Can View Product Categories',
            'can_add_product_categories': 'Can Add Product Categories',
            'can_edit_product_categories': 'Can Edit Product Categories',
            'can_delete_product_categories': 'Can Delete Product Categories',
        }
        
        updated_count = 0
        
        # تحديث كل صلاحية
        for codename, correct_name in correct_permissions.items():
            try:
                permission = Permission.objects.get(
                    content_type=category_ct,
                    codename=codename
                )
                
                if permission.name != correct_name:
                    old_name = permission.name
                    permission.name = correct_name
                    permission.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Updated permission "{codename}": "{old_name}" -> "{correct_name}"'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Permission "{codename}" already correct: "{correct_name}"'
                        )
                    )
                    
            except Permission.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f'Permission "{codename}" not found in database'
                    )
                )
        
        if updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully updated {updated_count} permission(s)'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    '\nAll permissions are already correct'
                )
            )

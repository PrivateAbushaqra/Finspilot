import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

# Find all permissions with codename containing 'edit_products'
edit_products_perms = Permission.objects.filter(codename__icontains='edit_products')

print('Permissions with "edit_products" in codename:')
for perm in edit_products_perms:
    print(f'ID: {perm.id}, Codename: {perm.codename}, Name: {perm.name}')
    print(f'  Content Type: {perm.content_type.app_label}.{perm.content_type.model}')
    print()

# Check if there are any permissions in cashboxes app that shouldn't be there
cashboxes_ct = ContentType.objects.get(app_label='cashboxes', model='cashbox')
cashboxes_perms = Permission.objects.filter(content_type=cashboxes_ct)

print('All permissions for cashboxes app:')
for perm in cashboxes_perms:
    print(f'  {perm.codename}: {perm.name}')

print()

# Check products permissions
products_ct = ContentType.objects.get(app_label='products', model='product')
products_perms = Permission.objects.filter(content_type=products_ct)

print('All permissions for products.product:')
for perm in products_perms:
    print(f'  {perm.codename}: {perm.name}')

print()

# Check categories permissions
try:
    categories_ct = ContentType.objects.get(app_label='products', model='category')
    categories_perms = Permission.objects.filter(content_type=categories_ct)
    
    print('All permissions for products.category:')
    for perm in categories_perms:
        print(f'  {perm.codename}: {perm.name}')
except:
    print('No categories content type found')

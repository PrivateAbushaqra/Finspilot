"""
Script to restore original category descriptions
This undoes the incorrect changes made by the previous script
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from products.models import Category

def restore_descriptions():
    """Restore original descriptions"""
    
    # Restore based on category IDs
    restorations = {
        1: 'الكل Interactive Screen 100',  # Original description for "ٍشاشات تفاعلية"
        2: 'All ulephone Items',  # Original description for "ulephone"
        3: 'All Accessories',  # Original description for "أكسسوارات"
    }
    
    restored_count = 0
    for cat_id, original_desc in restorations.items():
        try:
            category = Category.objects.get(id=cat_id)
            category.description = original_desc
            category.save()
            restored_count += 1
            print(f'Restored: {category.name}')
            print(f'  New description: {original_desc}')
            print()
        except Category.DoesNotExist:
            print(f'Category with ID {cat_id} not found')
    
    print(f'\nTotal categories restored: {restored_count}')

if __name__ == '__main__':
    print('Restoring original category descriptions...\n')
    restore_descriptions()
    print('\nDone!')

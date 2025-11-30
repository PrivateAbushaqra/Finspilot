"""
Script to fix mixed language descriptions in Category model
This script will translate English descriptions to Arabic
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from products.models import Category

# Translation mapping
translations = {
    'All': 'كل',
    'Interactive Screen': 'شاشات تفاعلية',
    'ulephone': 'هواتف',
    'Accessories': 'إكسسوارات',
    'Items': 'منتجات',
    'الكل': 'كل',
}

def fix_descriptions():
    """Fix category descriptions by removing mixed language content"""
    categories = Category.objects.all()
    fixed_count = 0
    
    for category in categories:
        if category.description:
            original = category.description
            description = category.description
            
            # Check if description contains English mixed with Arabic
            # Remove English words from Arabic descriptions
            if any(char in description for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'):
                # If description starts with Arabic word followed by English
                if description.strip().startswith('الكل'):
                    # Keep only the Arabic part or translate the whole thing
                    description = description.replace('الكل', 'كل')
                    # Remove English words
                    words = description.split()
                    arabic_words = [word for word in words if not any(char in word for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')]
                    description = ' '.join(arabic_words) if arabic_words else ''
                
                # If still contains English, try full translation
                if any(char in description for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'):
                    for en, ar in translations.items():
                        description = description.replace(en, ar)
                
                # Final cleanup - remove remaining English words
                words = description.split()
                clean_words = []
                for word in words:
                    # Keep word only if it's Arabic
                    if not any(char in word for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'):
                        clean_words.append(word)
                
                description = ' '.join(clean_words).strip()
                
                if description != original:
                    category.description = description
                    category.save()
                    fixed_count += 1
                    print(f'Fixed: {category.name}')
                    print(f'  Original: {original}')
                    print(f'  New: {description}')
                    print()
    
    print(f'\nTotal categories fixed: {fixed_count}')

if __name__ == '__main__':
    print('Starting to fix category descriptions...\n')
    fix_descriptions()
    print('\nDone!')

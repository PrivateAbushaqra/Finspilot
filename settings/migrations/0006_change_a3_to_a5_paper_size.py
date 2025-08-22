# Generated manually to update paper size from A3 to A5

from django.db import migrations

def update_a3_to_a5(apps, schema_editor):
    """تحديث جميع السجلات من A3 إلى A5"""
    DocumentPrintSettings = apps.get_model('settings', 'DocumentPrintSettings')
    DocumentPrintSettings.objects.filter(paper_size='A3').update(paper_size='A5')

def update_a5_to_a3(apps, schema_editor):
    """استعادة من A5 إلى A3"""
    DocumentPrintSettings = apps.get_model('settings', 'DocumentPrintSettings')
    DocumentPrintSettings.objects.filter(paper_size='A5').update(paper_size='A3')

class Migration(migrations.Migration):

    dependencies = [
        ('settings', '0005_add_document_print_settings'),
    ]

    operations = [
        migrations.RunPython(update_a3_to_a5, update_a5_to_a3),
    ]

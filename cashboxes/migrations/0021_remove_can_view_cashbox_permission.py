# Generated migration to remove can_view_cashbox permission
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cashboxes', '0020_alter_cashbox_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cashbox',
            options={'ordering': ['name'], 'verbose_name': 'Cash Box', 'verbose_name_plural': 'Cash Boxes'},
        ),
    ]

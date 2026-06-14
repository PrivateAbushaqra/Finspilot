from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('accounts', '0007_alter_accounttransaction_options_and_more'), 
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='dashboard_sections',
            field=models.TextField(blank=True, null=True),
        ),
    ]
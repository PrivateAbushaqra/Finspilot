# Generated migration to remove unused default permissions

from django.db import migrations


def remove_default_permissions(apps, schema_editor):
    """
    Remove default Django permissions (add, change, delete, view) for ReportAccessControl model.
    These permissions are not used since the model only exists to hold custom permissions.
    """
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    
    try:
        # Get the ContentType for ReportAccessControl
        ct = ContentType.objects.get(app_label='reports', model='reportaccesscontrol')
        
        # Delete the default permissions
        default_codenames = ['add_reportaccesscontrol', 'change_reportaccesscontrol', 
                           'delete_reportaccesscontrol', 'view_reportaccesscontrol']
        
        deleted_count = Permission.objects.filter(
            content_type=ct,
            codename__in=default_codenames
        ).delete()[0]
        
        if deleted_count > 0:
            print(f"✓ Removed {deleted_count} unused default permissions for ReportAccessControl")
    except ContentType.DoesNotExist:
        print("ContentType for ReportAccessControl not found, skipping...")


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0003_alter_reportaccesscontrol_options'),
    ]

    operations = [
        migrations.RunPython(remove_default_permissions, reverse_code=migrations.RunPython.noop),
    ]

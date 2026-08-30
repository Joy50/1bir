from django.db import migrations


def promote_root_battalions_to_units(apps, schema_editor):
    Organization = apps.get_model("common", "Organization")
    Organization.objects.filter(
        parent_organization__isnull=True,
        unit_kind="battalion",
    ).update(unit_kind="unit")


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0018_organization_type_hierarchy"),
    ]

    operations = [
        migrations.RunPython(
            promote_root_battalions_to_units,
            migrations.RunPython.noop,
        ),
    ]

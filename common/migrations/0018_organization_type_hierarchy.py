from django.db import migrations, models


def remap_organization_types(apps, schema_editor):
    Organization = apps.get_model("common", "Organization")
    mapping = {
        "subunit": "platoon",
        "other": "unit",
    }
    for org in Organization.objects.select_related("parent_organization"):
        new_kind = mapping.get(org.unit_kind)
        if new_kind is None:
            continue
        if org.unit_kind == "other" and org.parent_organization_id:
            parent_kind = org.parent_organization.unit_kind
            new_kind = {
                "unit": "battalion",
                "battalion": "company",
                "company": "platoon",
                "platoon": "section",
                "subunit": "platoon",
            }.get(parent_kind, "platoon")
        org.unit_kind = new_kind
        org.save(update_fields=["unit_kind"])


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0017_organization_kind_and_history_dates"),
    ]

    operations = [
        migrations.RunPython(remap_organization_types, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="organization",
            name="unit_kind",
            field=models.CharField(
                choices=[
                    ("unit", "Unit"),
                    ("battalion", "Battalion"),
                    ("company", "Company"),
                    ("platoon", "Platoon"),
                    ("section", "Section"),
                ],
                default="unit",
                help_text="Unit → Battalion → Company → Platoon → Section.",
                max_length=20,
                verbose_name="organization type",
            ),
        ),
    ]

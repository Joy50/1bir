from django.db import migrations, models


def set_unit_kinds(apps, schema_editor):
    Organization = apps.get_model("common", "Organization")
    for org in Organization.objects.select_related("parent_organization"):
        if org.parent_organization_id is None:
            org.unit_kind = "battalion"
        elif (
            org.parent_organization_id
            and org.parent_organization.parent_organization_id is None
        ):
            org.unit_kind = "company"
        else:
            org.unit_kind = "subunit"
        org.save(update_fields=["unit_kind"])


def blank_unique_ids_to_null(apps, schema_editor):
    Person = apps.get_model("common", "Person")
    Person.objects.filter(passport_number="").update(passport_number=None)
    Person.objects.filter(service_id_card_number="").update(service_id_card_number=None)


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0016_rank_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="unit_kind",
            field=models.CharField(
                choices=[
                    ("battalion", "Battalion"),
                    ("company", "Company"),
                    ("subunit", "Subunit"),
                    ("other", "Other"),
                ],
                default="other",
                max_length=20,
            ),
        ),
        migrations.RunPython(set_unit_kinds, migrations.RunPython.noop),
        migrations.RunPython(blank_unique_ids_to_null, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="organization",
            constraint=models.UniqueConstraint(
                fields=("organization_name", "parent_organization"),
                name="unique_org_name_per_parent",
            ),
        ),
        migrations.AddConstraint(
            model_name="organization",
            constraint=models.UniqueConstraint(
                condition=models.Q(parent_organization__isnull=True),
                fields=("organization_name",),
                name="unique_root_organization_name",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="servicehistory",
            name="service_history_valid_dates",
        ),
        migrations.AddConstraint(
            model_name="servicehistory",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("end_date__isnull", True),
                    ("end_date__gte", models.F("start_date")),
                    _connector="OR",
                ),
                name="service_history_valid_dates",
            ),
        ),
    ]

import django.db.models.deletion
from django.db import migrations, models


def assign_null_cycle_plans(apps, schema_editor):
    Organization = apps.get_model("common", "Organization")
    Plan = apps.get_model("training", "UnitTrainingCyclePlan")
    battalion = Organization.objects.filter(parent_organization__isnull=True).first()
    if battalion is None:
        battalion = Organization.objects.create(
            organization_name="1 BIR",
            unit_kind="battalion",
        )
    Plan.objects.filter(organization__isnull=True).update(organization=battalion)


def coerce_qual_years(apps, schema_editor):
    IndividualQual = apps.get_model("training", "IndividualQual")
    for row in IndividualQual.objects.all():
        value = str(row.year or "").strip()
        if value.isdigit():
            continue
        row.year = "2026"
        row.save(update_fields=["year"])


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0017_organization_kind_and_history_dates"),
        ("training", "0014_participationinsportstraining_cycle_and_more"),
    ]

    operations = [
        migrations.RunPython(assign_null_cycle_plans, migrations.RunPython.noop),
        migrations.RunPython(coerce_qual_years, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="unittrainingcycleplan",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="unit_training_cycle_plans",
                to="common.organization",
            ),
        ),
        migrations.AlterField(
            model_name="individualqual",
            name="year",
            field=models.PositiveIntegerField(),
        ),
    ]

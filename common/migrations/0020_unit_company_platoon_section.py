from django.db import migrations, models


def flatten_to_unit_company_tree(apps, schema_editor):
    Organization = apps.get_model("common", "Organization")
    Person = apps.get_model("common", "Person")

    Organization.objects.filter(
        parent_organization__isnull=True,
        unit_kind="battalion",
    ).update(unit_kind="unit")

    units = list(Organization.objects.filter(unit_kind="unit").order_by("pk"))
    if not units:
        unit = Organization.objects.create(
            organization_name="1 BIR",
            unit_kind="unit",
        )
    else:
        unit = next(
            (item for item in units if item.organization_name == "1 BIR"),
            units[0],
        )
        for extra in units:
            if extra.pk == unit.pk:
                continue
            for child in Organization.objects.filter(parent_organization=extra):
                existing = Organization.objects.filter(
                    organization_name=child.organization_name,
                    parent_organization=unit,
                ).exclude(pk=child.pk)
                if existing.exists():
                    child.organization_name = f"{extra.organization_name} - {child.organization_name}"
                child.parent_organization_id = unit.pk
                child.save(update_fields=["parent_organization", "organization_name"])
            extra.parent_organization_id = unit.pk
            extra.unit_kind = "company"
            extra.save(update_fields=["parent_organization", "unit_kind"])

    for battalion in Organization.objects.filter(unit_kind="battalion"):
        for child in Organization.objects.filter(
            parent_organization=battalion,
            unit_kind="company",
        ):
            existing = Organization.objects.filter(
                organization_name=child.organization_name,
                parent_organization=unit,
            ).exclude(pk=child.pk)
            if existing.exists():
                child.organization_name = (
                    f"{battalion.organization_name} - {child.organization_name}"
                )
            child.parent_organization_id = unit.pk
            child.save(update_fields=["parent_organization", "organization_name"])
        battalion.unit_kind = "company"
        if battalion.parent_organization_id is None:
            battalion.parent_organization_id = unit.pk
        battalion.save(update_fields=["unit_kind", "parent_organization"])

    hq, created = Organization.objects.get_or_create(
        organization_name="HQ Company",
        parent_organization=unit,
        defaults={"unit_kind": "company"},
    )
    if not created and hq.unit_kind != "company":
        hq.unit_kind = "company"
        hq.save(update_fields=["unit_kind"])

    Person.objects.filter(organization__unit_kind="unit").update(organization_id=hq.pk)


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0019_root_organizations_are_units"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="authorized_strength",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Company establishment (PE) by parade column. Unused on other types.",
            ),
        ),
        migrations.RunPython(flatten_to_unit_company_tree, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="organization",
            name="unit_kind",
            field=models.CharField(
                choices=[
                    ("unit", "Unit"),
                    ("company", "Company"),
                    ("platoon", "Platoon"),
                    ("section", "Section"),
                ],
                default="unit",
                help_text="Unit → Company → Platoon → Section.",
                max_length=20,
                verbose_name="organization type",
            ),
        ),
        migrations.AddConstraint(
            model_name="organization",
            constraint=models.UniqueConstraint(
                condition=models.Q(unit_kind="unit"),
                fields=("unit_kind",),
                name="unique_unit_organization",
            ),
        ),
    ]

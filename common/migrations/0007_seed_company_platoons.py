from django.db import migrations


COMPANIES = ("A Company", "B Company", "C Company", "D Company", "HQ Company")
PLATOONS = ("Pl-1", "Pl-2", "Pl-3", "Sp Pl", "Coy HQ")


def seed_company_platoons(apps, schema_editor):
    Organization = apps.get_model("common", "Organization")
    battalion, _created = Organization.objects.get_or_create(
        organization_name="1 BIR",
        parent_organization=None,
    )
    for company_name in COMPANIES:
        company, _created = Organization.objects.get_or_create(
            organization_name=company_name,
            parent_organization=battalion,
        )
        for platoon_name in PLATOONS:
            Organization.objects.get_or_create(
                organization_name=platoon_name,
                parent_organization=company,
            )


class Migration(migrations.Migration):

    dependencies = [("common", "0006_initial")]

    operations = [
        migrations.RunPython(seed_company_platoons, migrations.RunPython.noop),
    ]

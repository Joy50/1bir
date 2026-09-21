from django.db import migrations, models


def copy_legacy_addresses(apps, schema_editor):
    Person = apps.get_model("common", "Person")
    for person in Person.objects.all().iterator():
        if person.present_address and not person.present_full_address:
            person.present_full_address = person.present_address
        if person.permanent_address and not person.permanent_full_address:
            person.permanent_full_address = person.permanent_address
        person.save(
            update_fields=["present_full_address", "permanent_full_address"]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0019_root_organizations_are_units"),
    ]

    operations = [
        migrations.AddField(
            model_name="person",
            name="present_district",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="person",
            name="present_sub_district_union",
            field=models.CharField(
                blank=True,
                max_length=120,
                verbose_name="present sub district/union",
            ),
        ),
        migrations.AddField(
            model_name="person",
            name="present_thana",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="person",
            name="present_full_address",
            field=models.TextField(blank=True, verbose_name="present full address"),
        ),
        migrations.AddField(
            model_name="person",
            name="permanent_district",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="person",
            name="permanent_sub_district_union",
            field=models.CharField(
                blank=True,
                max_length=120,
                verbose_name="permanent sub district/union",
            ),
        ),
        migrations.AddField(
            model_name="person",
            name="permanent_thana",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="person",
            name="permanent_full_address",
            field=models.TextField(blank=True, verbose_name="permanent full address"),
        ),
        migrations.RunPython(copy_legacy_addresses, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="person",
            name="present_address",
        ),
        migrations.RemoveField(
            model_name="person",
            name="permanent_address",
        ),
    ]

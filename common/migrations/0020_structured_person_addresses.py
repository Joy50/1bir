from django.db import migrations, models


def copy_legacy_addresses(apps, schema_editor):
    Person = apps.get_model("common", "Person")
    for person in Person.objects.all().iterator():
        updates = {}
        if person.present_address and not person.present_area_road_house:
            updates["present_area_road_house"] = person.present_address
        if person.permanent_address and not person.permanent_area_road_house:
            updates["permanent_area_road_house"] = person.permanent_address
        if updates:
            for field, value in updates.items():
                setattr(person, field, value)
            person.save(update_fields=list(updates.keys()))


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
            name="present_upazila",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="person",
            name="present_thana",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="person",
            name="present_area_road_house",
            field=models.TextField(blank=True, verbose_name="present area/road/house"),
        ),
        migrations.AddField(
            model_name="person",
            name="permanent_district",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="person",
            name="permanent_upazila",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="person",
            name="permanent_thana",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="person",
            name="permanent_area_road_house",
            field=models.TextField(blank=True, verbose_name="permanent area/road/house"),
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

from django.db import migrations, models


REFERENCE_POSTS = (
    ("RP Post - 1", "unit", 2, 3),
    ("RP Post - 2", "unit", 2, 3),
    ("A Coy Line", "unit", 2, 3),
    ("B Coy Line", "unit", 2, 3),
    ("C Coy Line", "unit", 2, 3),
    ("Sig Store", "unit", 0, 3),
    ("Trg Grd", "unit", 2, 6),
    ("Office Area", "unit", 0, 2),
    ("RP Ptl", "unit", 2, 0),
    ("Qtr Gd", "unit", 10, 0),
    ("Chairman Bari", "station", 2, 6),
    ("Shena Shopping Complex", "station", 2, 6),
    ("Birangon", "station", 2, 6),
    ("Old CSD", "station", 0, 6),
)


def seed_reference_posts(apps, schema_editor):
    DutyPost = apps.get_model("duty", "DutyPost")
    for name, duty_type, day, night in REFERENCE_POSTS:
        DutyPost.objects.get_or_create(
            name=name,
            defaults={
                "duty_type": duty_type,
                "day_strength": day,
                "night_strength": night,
                "latitude": 21.432400,
                "longitude": 92.100800,
                "description": "",
                "is_active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [("duty", "0002_parade_state")]

    operations = [
        migrations.AddField(
            model_name="dutypost",
            name="duty_type",
            field=models.CharField(
                choices=[("unit", "Unit Duty"), ("station", "Station Duty")],
                default="unit",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="dutypost",
            name="day_strength",
            field=models.PositiveIntegerField(default=0, verbose_name="Day"),
        ),
        migrations.AddField(
            model_name="dutypost",
            name="night_strength",
            field=models.PositiveIntegerField(default=0, verbose_name="Night"),
        ),
        migrations.RunPython(seed_reference_posts, migrations.RunPython.noop),
    ]

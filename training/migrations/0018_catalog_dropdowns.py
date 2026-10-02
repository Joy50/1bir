from django.db import migrations, models


def seed_catalog(apps, schema_editor):
    from training.catalog import CADRE_LEVELS, CADRE_NAMES, COURSE_LEVELS, COURSE_NAMES

    Level = apps.get_model("training", "IndividualCourseLevel")
    CourseName = apps.get_model("training", "IndividualCourseName")
    for level_name, names in (
        *[(level, CADRE_NAMES) for level in CADRE_LEVELS],
        *[(level, COURSE_NAMES) for level in COURSE_LEVELS],
    ):
        level, _created = Level.objects.get_or_create(name=level_name)
        for name in names:
            CourseName.objects.get_or_create(level=level, name=name)


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0017_leave_slot_open_casual"),
    ]

    operations = [
        migrations.AlterField(
            model_name="individualqualcourse",
            name="result",
            field=models.CharField(
                blank=True,
                choices=[("A", "A"), ("B+", "B+"), ("B", "B"), ("Pass", "Pass")],
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="participationinsportstraining",
            name="name_of_comp",
            field=models.CharField(
                choices=[
                    ("Kabadi", "Kabadi"),
                    ("Azan Cricket", "Azan Cricket"),
                    ("Hockey", "Hockey"),
                    ("Aquatic", "Aquatic"),
                    ("Volleyball", "Volleyball"),
                    ("Boxing", "Boxing"),
                    ("Football", "Football"),
                    ("Basketball", "Basketball"),
                    ("Trg Aid Display", "Trg Aid Display"),
                    ("Bayonet Ftg", "Bayonet Ftg"),
                    ("Firing", "Firing"),
                    ("Quiz", "Quiz"),
                    ("Drill", "Drill"),
                    ("CAS Trophy Firing", "CAS Trophy Firing"),
                    ("Aslt Course", "Aslt Course"),
                ],
                max_length=255,
                verbose_name="Competition",
            ),
        ),
        migrations.AlterField(
            model_name="participationinsportstraining",
            name="significant_achievement",
            field=models.CharField(
                blank=True,
                choices=[
                    ("GOLD MEDAL", "GOLD MEDAL"),
                    ("SILVER MEDAL", "SILVER MEDAL"),
                    ("BRONZE MEDAL", "BRONZE MEDAL"),
                ],
                max_length=255,
                verbose_name="Achievement",
            ),
        ),
        migrations.RunPython(seed_catalog, migrations.RunPython.noop),
    ]

import django.db.models.deletion
from django.db import migrations, models


def copy_existing_qualifications(apps, schema_editor):
    """Move each qualification's existing course/result to the child table."""
    IndividualQual = apps.get_model("training", "IndividualQual")
    IndividualQualCourse = apps.get_model("training", "IndividualQualCourse")

    rows = IndividualQual.objects.exclude(course_name_id=None).values_list(
        "id", "course_name_id", "result"
    )
    IndividualQualCourse.objects.bulk_create(
        IndividualQualCourse(
            qualification_id=qualification_id,
            course_name_id=course_name_id,
            result=result,
        )
        for qualification_id, course_name_id, result in rows.iterator()
    )


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0006_individualqual_result"),
    ]

    operations = [
        migrations.CreateModel(
            name="IndividualQualCourse",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("result", models.CharField(blank=True, max_length=255)),
                (
                    "course_name",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="qualification_entries",
                        to="training.individualcoursename",
                    ),
                ),
                (
                    "qualification",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="courses",
                        to="training.individualqual",
                    ),
                ),
            ],
            options={
                "verbose_name": "Qualification Course",
                "verbose_name_plural": "Qualification Courses",
                "ordering": ["course_name__level__name", "course_name__name"],
            },
        ),
        migrations.RunPython(
            copy_existing_qualifications,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveConstraint(
            model_name="individualqual",
            name="unique_person_course_year",
        ),
        migrations.RemoveField(model_name="individualqual", name="course_name"),
        migrations.RemoveField(model_name="individualqual", name="result"),
        migrations.AlterModelOptions(
            name="individualqual",
            options={
                "ordering": ["-year"],
                "verbose_name": "Individual Qualification",
                "verbose_name_plural": "Individual Qualifications",
            },
        ),
        migrations.AddConstraint(
            model_name="individualqual",
            constraint=models.UniqueConstraint(
                fields=("solider", "year"), name="unique_person_qual_year"
            ),
        ),
        migrations.AddConstraint(
            model_name="individualqualcourse",
            constraint=models.UniqueConstraint(
                fields=("qualification", "course_name"), name="unique_qual_course"
            ),
        ),
    ]

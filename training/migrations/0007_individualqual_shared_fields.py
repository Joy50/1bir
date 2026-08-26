import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0006_individualqual_result"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
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
                        "ordering": [
                            "course_name__level__name",
                            "course_name__name",
                        ],
                    },
                ),
                migrations.RemoveConstraint(
                    model_name="individualqual",
                    name="unique_person_course_year",
                ),
                migrations.RemoveField(
                    model_name="individualqual",
                    name="course_name",
                ),
                migrations.RemoveField(
                    model_name="individualqual",
                    name="result",
                ),
                migrations.AddField(
                    model_name="individualcoursename",
                    name="result",
                    field=models.CharField(max_length=255),
                ),
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
                        fields=("solider", "year"),
                        name="unique_person_qual_year",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="individualqualcourse",
                    constraint=models.UniqueConstraint(
                        fields=("qualification", "course_name"),
                        name="unique_qual_course",
                    ),
                ),
            ],
        ),
    ]

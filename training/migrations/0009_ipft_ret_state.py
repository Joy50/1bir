import django.db.models.deletion
from django.db import migrations, models


def claim_ipft_table(apps, schema_editor):
    tables = set(schema_editor.connection.introspection.table_names())
    if "training_ipft" in tables:
        return
    if "ipft_ipft" in tables:
        with schema_editor.connection.cursor() as cursor:
            cursor.execute('ALTER TABLE "ipft_ipft" RENAME TO "training_ipft"')
        return
    from training.models import IPFT

    schema_editor.create_model(IPFT)


def unclaim_ipft_table(apps, schema_editor):
    tables = set(schema_editor.connection.introspection.table_names())
    if "training_ipft" in tables and "ipft_ipft" not in tables:
        with schema_editor.connection.cursor() as cursor:
            cursor.execute('ALTER TABLE "training_ipft" RENAME TO "ipft_ipft"')


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0004_remove_individualcoursename_unique_course_name_per_level_and_more"),
        ("training", "0008_qualcourse_result"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="IPFT",
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
                            "type_of_ipft",
                            models.CharField(
                                choices=[
                                    ("1st Bi-annual", "1st Bi-annual"),
                                    ("2nd Bi-annual", "2nd Bi-annual"),
                                ],
                                max_length=255,
                                verbose_name="Type of IPFT",
                            ),
                        ),
                        (
                            "chance",
                            models.CharField(
                                choices=[
                                    ("1st Chance", "1st Chance"),
                                    ("2nd Chance", "2nd Chance"),
                                    ("3rd Chance", "3rd Chance"),
                                    ("4th Chance", "4th Chance"),
                                    ("5th Chance", "5th Chance"),
                                ],
                                max_length=255,
                            ),
                        ),
                        ("date", models.DateField()),
                        (
                            "result",
                            models.CharField(
                                blank=True,
                                choices=[("Pass", "Pass"), ("Fail", "Fail")],
                                max_length=255,
                            ),
                        ),
                        (
                            "solider",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="ipft_records",
                                to="common.person",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "IPFT",
                        "verbose_name_plural": "IPFT Records",
                        "ordering": ["-date", "type_of_ipft", "chance"],
                    },
                ),
            ],
            database_operations=[
                migrations.RunPython(claim_ipft_table, unclaim_ipft_table),
            ],
        ),
        migrations.CreateModel(
            name="RETTrainingType",
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
                ("name", models.CharField(max_length=255, unique=True)),
            ],
            options={
                "verbose_name": "RET Training Type",
                "verbose_name_plural": "RET Training Types",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="RETState",
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
                ("date_performed", models.DateField()),
                (
                    "result",
                    models.CharField(
                        blank=True,
                        choices=[("Pass", "Pass"), ("Fail", "Fail")],
                        max_length=255,
                    ),
                ),
                (
                    "ret_trg_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ret_states",
                        to="training.rettrainingtype",
                        verbose_name="RET training type",
                    ),
                ),
                (
                    "solider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ret_states",
                        to="common.person",
                    ),
                ),
            ],
            options={
                "verbose_name": "RET State",
                "verbose_name_plural": "RET States",
                "ordering": ["-date_performed", "ret_trg_type__name"],
            },
        ),
    ]

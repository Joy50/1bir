import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0004_remove_individualcoursename_unique_course_name_per_level_and_more"),
        ("training", "0009_ipft_ret_state"),
    ]

    operations = [
        migrations.CreateModel(
            name="GPFiring",
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
                    "type_of_gp",
                    models.CharField(
                        choices=[
                            ("Gp Firing - 100m", "Gp Firing - 100m"),
                            ("Gp Firing - 300m", "Gp Firing - 300m"),
                        ],
                        max_length=255,
                        verbose_name="Type of GP",
                    ),
                ),
                (
                    "attempt",
                    models.CharField(
                        choices=[
                            ("Prac-1", "Prac-1"),
                            ("Prac-2", "Prac-2"),
                            ("Prac-3", "Prac-3"),
                            ("Prac-4", "Prac-4"),
                        ],
                        max_length=255,
                    ),
                ),
                ("date_of_firing", models.DateField()),
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
                        related_name="gp_firings",
                        to="common.person",
                    ),
                ),
            ],
            options={
                "verbose_name": "GP Firing",
                "verbose_name_plural": "GP Firings",
                "ordering": ["-date_of_firing", "type_of_gp", "attempt"],
            },
        ),
        migrations.CreateModel(
            name="SOSNFiring",
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
                    "type_of_gp",
                    models.CharField(
                        choices=[
                            ("SOSN Firing - 100m", "SOSN Firing - 100m"),
                            ("SOSN Firing - 300m", "SOSN Firing - 300m"),
                        ],
                        max_length=255,
                        verbose_name="Type of SOSN",
                    ),
                ),
                (
                    "attempt",
                    models.CharField(
                        choices=[
                            ("Prac-1", "Prac-1"),
                            ("Prac-2", "Prac-2"),
                            ("Prac-3", "Prac-3"),
                            ("Prac-4", "Prac-4"),
                        ],
                        max_length=255,
                    ),
                ),
                ("date_of_firing", models.DateField()),
                ("gp", models.CharField(blank=True, max_length=255)),
                ("hit", models.CharField(blank=True, max_length=255)),
                ("total_marks", models.CharField(blank=True, max_length=255)),
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
                        related_name="sosn_firings",
                        to="common.person",
                    ),
                ),
            ],
            options={
                "verbose_name": "SOSN Firing",
                "verbose_name_plural": "SOSN Firings",
                "ordering": ["-date_of_firing", "type_of_gp", "attempt"],
            },
        ),
        migrations.CreateModel(
            name="CASTrophy",
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
                ("date_of_firing", models.DateField()),
                ("gp", models.CharField(blank=True, max_length=255)),
                ("hit", models.CharField(blank=True, max_length=255)),
                ("total_marks", models.CharField(blank=True, max_length=255)),
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
                        related_name="cas_trophies",
                        to="common.person",
                    ),
                ),
            ],
            options={
                "verbose_name": "CAS Trophy Firing",
                "verbose_name_plural": "CAS Trophy Firings",
                "ordering": ["-date_of_firing"],
            },
        ),
        migrations.CreateModel(
            name="GrenadeFiring",
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
                    "attempt",
                    models.CharField(
                        choices=[
                            ("Prac-1", "Prac-1"),
                            ("Prac-2", "Prac-2"),
                            ("Prac-3", "Prac-3"),
                            ("Prac-4", "Prac-4"),
                        ],
                        max_length=255,
                    ),
                ),
                ("date_of_firing", models.DateField()),
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
                        related_name="grenade_firings",
                        to="common.person",
                    ),
                ),
            ],
            options={
                "verbose_name": "Grenade Firing",
                "verbose_name_plural": "Grenade Firings",
                "ordering": ["-date_of_firing", "attempt"],
            },
        ),
    ]

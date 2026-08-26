from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Rank",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rank_name", models.CharField(max_length=100, unique=True)),
            ],
            options={"ordering": ["rank_name"]},
        ),
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("organization_name", models.CharField(max_length=100)),
                ("parent_organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="child_organizations", to="common.organization")),
            ],
            options={"ordering": ["organization_name"]},
        ),
        migrations.CreateModel(
            name="CivilEducationLevel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("level_name", models.CharField(max_length=100, unique=True)),
            ],
            options={"ordering": ["level_name"]},
        ),
        migrations.CreateModel(
            name="Person",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("army_number", models.CharField(max_length=20, unique=True)),
                ("photo", models.ImageField(blank=True, null=True, upload_to="soldier_photos/")),
                ("dob", models.DateField()),
                ("doe", models.DateField()),
                ("present_age", models.PositiveIntegerField(blank=True, editable=False, null=True)),
                ("present_service_years", models.PositiveIntegerField(blank=True, editable=False, null=True)),
                ("al1_13", models.CharField(blank=True, choices=[("Yes", "Yes"), ("No", "No")], max_length=3, null=True)),
                ("dor", models.DateField(blank=True, null=True)),
                ("discipline", models.TextField(blank=True, null=True)),
                ("punishment", models.TextField(blank=True, null=True)),
                ("mission", models.BooleanField(default=False)),
                ("qualification_for_next_rank", models.BooleanField(default=False)),
                ("passport_number", models.CharField(blank=True, max_length=20, null=True, unique=True)),
                ("service_id_card_number", models.CharField(blank=True, max_length=20, null=True, unique=True)),
                ("present_address", models.TextField(blank=True, null=True)),
                ("permanent_address", models.TextField(blank=True, null=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="persons", to="common.organization")),
                ("rank", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="persons", to="common.rank")),
            ],
            options={"ordering": ["army_number"]},
        ),
        migrations.AddConstraint(
            model_name="person",
            constraint=models.CheckConstraint(condition=models.Q(("doe__gt", models.F("dob"))), name="person_doe_after_dob"),
        ),
        migrations.CreateModel(
            name="ServiceHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="common.organization")),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="service_histories", to="common.person")),
                ("rank", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="common.rank")),
            ],
            options={"ordering": ["-start_date"]},
        ),
        migrations.CreateModel(
            name="CivilEducation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("institution_name", models.CharField(max_length=100)),
                ("from_date", models.DateField()),
                ("to_date", models.DateField(blank=True, null=True)),
                ("grade", models.CharField(blank=True, max_length=100, null=True)),
                ("level", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="common.civileducationlevel")),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="civil_educations", to="common.person")),
            ],
            options={"ordering": ["-from_date"]},
        ),
        migrations.CreateModel(
            name="MedicalCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(max_length=100)),
                ("from_date", models.DateField()),
                ("to_date", models.DateField(blank=True, null=True)),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="medical_categories", to="common.person")),
            ],
            options={"ordering": ["-from_date"]},
        ),
        migrations.CreateModel(
            name="AnnualPerformanceReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveIntegerField()),
                ("report", models.TextField(blank=True, null=True)),
                ("score", models.PositiveIntegerField(blank=True, null=True)),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="annual_performance_reports", to="common.person")),
            ],
            options={"ordering": ["-year"]},
        ),
        migrations.AddConstraint(
            model_name="annualperformancereport",
            constraint=models.UniqueConstraint(fields=("person", "year"), name="unique_person_apr_year"),
        ),
        migrations.CreateModel(
            name="AppointmentHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("appointment_name", models.CharField(max_length=100)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="common.organization")),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="appointment_histories", to="common.person")),
            ],
            options={"ordering": ["-start_date"]},
        ),
        migrations.CreateModel(
            name="MobileNumber",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type_of_number", models.CharField(choices=[("personal", "Personal"), ("nok", "Next of kin")], max_length=20)),
                ("mobile_number", models.CharField(max_length=15)),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mobile_numbers", to="common.person")),
            ],
        ),
    ]

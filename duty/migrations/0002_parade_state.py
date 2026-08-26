import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("common", "0006_initial"),
        ("duty", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ParadeState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("report_date", models.DateField(unique=True)),
                ("authorized_strength", models.JSONField(blank=True, default=dict)),
                ("attachment", models.FileField(blank=True, upload_to="parade_state/")),
                ("remarks", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="parade_states_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-report_date"]},
        ),
        migrations.CreateModel(
            name="ParadeStateCompany",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("posted_strength", models.JSONField(blank=True, default=dict)),
                ("absent_strength", models.JSONField(blank=True, default=dict)),
                ("absence_details", models.JSONField(blank=True, default=dict)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="parade_state_entries", to="common.organization")),
                ("parade_state", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="company_states", to="duty.paradestate")),
            ],
            options={"ordering": ["organization__organization_name"]},
        ),
        migrations.AddConstraint(
            model_name="paradestatecompany",
            constraint=models.UniqueConstraint(fields=("parade_state", "organization"), name="unique_parade_state_company"),
        ),
    ]

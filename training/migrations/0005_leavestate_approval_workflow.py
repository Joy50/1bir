import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import F


def seed_existing_leave_status(apps, schema_editor):
    LeaveState = apps.get_model("training", "LeaveState")
    LeaveState.objects.filter(approved_by_id__isnull=False).update(
        status="approved",
        applied_by_id=F("approved_by_id"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0004_alter_participationinmajcom_options_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="leavestate",
            name="applied_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="applied_leaves",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="leavestate",
            name="applied_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name="leavestate",
            name="decided_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="leavestate",
            name="remarks",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="leavestate",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="leavestate",
            name="approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="approved_leaves",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="leavestate",
            name="total_no_days",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Total approved days of this leave type taken by the soldier.",
            ),
        ),
        migrations.RunPython(seed_existing_leave_status, migrations.RunPython.noop),
    ]

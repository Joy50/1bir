from django.db import migrations, models


def close_extra_open_tours(apps, schema_editor):
    DutyTour = apps.get_model("duty", "DutyTour")
    opens = list(DutyTour.objects.filter(status="open").order_by("number", "pk"))
    for tour in opens[1:]:
        tour.status = "reported"
        tour.save(update_fields=["status"])


class Migration(migrations.Migration):

    dependencies = [
        ("duty", "0005_duty_assignment_shift"),
    ]

    operations = [
        migrations.RunPython(close_extra_open_tours, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="dutytour",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="open"),
                fields=("status",),
                name="unique_open_duty_tour",
            ),
        ),
    ]

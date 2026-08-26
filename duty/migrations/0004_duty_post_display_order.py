from django.db import migrations, models


ORDERED_NAMES = (
    "RP Post - 1", "RP Post - 2", "A Coy Line", "B Coy Line", "C Coy Line",
    "Sig Store", "Trg Grd", "Office Area", "RP Ptl", "Qtr Gd",
    "Chairman Bari", "Shena Shopping Complex", "Birangon", "Old CSD",
)


def set_reference_order(apps, schema_editor):
    DutyPost = apps.get_model("duty", "DutyPost")
    for order, name in enumerate(ORDERED_NAMES, start=1):
        DutyPost.objects.filter(name=name).update(display_order=order)


class Migration(migrations.Migration):

    dependencies = [("duty", "0003_duty_post_types_and_strength")]

    operations = [
        migrations.AddField(
            model_name="dutypost",
            name="display_order",
            field=models.PositiveSmallIntegerField(default=100),
        ),
        migrations.AlterModelOptions(
            name="dutypost",
            options={"ordering": ["duty_type", "display_order", "name"]},
        ),
        migrations.RunPython(set_reference_order, migrations.RunPython.noop),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("duty", "0007_parade_absence_document"),
    ]

    operations = [
        migrations.AddField(
            model_name="paradestatecompany",
            name="authorized_strength",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]

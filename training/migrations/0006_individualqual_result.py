from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0005_leavestate_approval_workflow"),
    ]

    operations = [
        migrations.AddField(
            model_name="individualqual",
            name="result",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]

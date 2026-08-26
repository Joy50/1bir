from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0007_individualqual_shared_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="individualqualcourse",
            name="result",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.RemoveField(
            model_name="individualcoursename",
            name="result",
        ),
    ]

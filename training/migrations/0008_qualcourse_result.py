from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0007_individualqual_shared_fields"),
    ]

    # The result field is created and populated safely in migration 0007.
    operations = []

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0002_user_organizations"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Admin"),
                    ("co", "CO"),
                    ("officer", "Officer"),
                    ("clerk", "Clerk"),
                ],
                default="clerk",
                max_length=20,
            ),
        ),
    ]

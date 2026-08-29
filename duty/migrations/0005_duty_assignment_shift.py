from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("duty", "0004_duty_post_display_order")]

    operations = [
        migrations.AddField(
            model_name="dutyassignment",
            name="shift",
            field=models.CharField(
                choices=[("day", "Day"), ("night", "Night")],
                default="day",
                max_length=10,
            ),
        ),
    ]

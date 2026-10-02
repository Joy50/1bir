from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0020_unit_company_platoon_section"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="unit_kind",
            field=models.CharField(
                choices=[
                    ("unit", "Unit"),
                    ("company", "Company"),
                    ("platoon", "Platoon"),
                    ("section", "Section"),
                    ("ere", "ERE"),
                ],
                default="unit",
                help_text="Unit → Company → Platoon → Section. ERE organizations sit under the Unit.",
                max_length=20,
                verbose_name="organization type",
            ),
        ),
    ]

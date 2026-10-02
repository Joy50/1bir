import re

from django.db import migrations, models


def clamp_choice(value):
    if value is None:
        return None
    if 1 <= value <= 12:
        return value
    return None


def parse_height(raw):
    text = (raw or "").strip().lower()
    if not text:
        return None, None
    text = text.replace("′", "'").replace("″", '"').replace("’", "'")
    match = re.search(r"(\d+)\s*(?:'|ft|feet)\s*(\d+)?", text)
    if match:
        feet = int(match.group(1))
        inches = int(match.group(2)) if match.group(2) else None
        return clamp_choice(feet), clamp_choice(inches) if inches else None
    match = re.search(r"(\d+)\s*(?:cm|cent)", text)
    if match:
        total = round(int(match.group(1)) / 2.54)
        feet, inches = divmod(total, 12)
        return clamp_choice(feet), clamp_choice(inches)
    match = re.search(r"(\d+)\s*(?:in|inch)", text)
    if match:
        total = int(match.group(1))
        feet, inches = divmod(total, 12)
        return clamp_choice(feet), clamp_choice(inches)
    match = re.search(r"(\d+)", text)
    if not match:
        return None, None
    value = int(match.group(1))
    if value > 100:
        total = round(value / 2.54)
        feet, inches = divmod(total, 12)
        return clamp_choice(feet), clamp_choice(inches)
    if value > 12:
        feet, inches = divmod(value, 12)
        return clamp_choice(feet), clamp_choice(inches)
    return clamp_choice(value), None


def copy_height(apps, schema_editor):
    Person = apps.get_model("common", "Person")
    for person in Person.objects.all().iterator():
        feet, inches = parse_height(getattr(person, "height", "") or "")
        updates = {}
        if feet is not None:
            updates["height_feet"] = feet
        if inches is not None:
            updates["height_inches"] = inches
        if updates:
            Person.objects.filter(pk=person.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0023_family_relation_name_mobile"),
    ]

    operations = [
        migrations.AddField(
            model_name="person",
            name="height_feet",
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[(value, str(value)) for value in range(1, 13)],
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="person",
            name="height_inches",
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[(value, str(value)) for value in range(1, 13)],
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="person",
            name="on_strength",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="servicehistory",
            name="trade",
            field=models.CharField(
                blank=True,
                choices=[("COOK", "COOK"), ("CLK", "CLK"), ("GD", "GD")],
                max_length=8,
            ),
        ),
        migrations.RunPython(copy_height, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="person",
            name="height",
        ),
    ]

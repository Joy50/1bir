from django.db import migrations, models


RELATION_ALIASES = {
    "father": "father",
    "mother": "mother",
    "mather": "mother",
    "wife": "wife",
    "husband": "husband",
    "son": "son",
    "daughter": "daughter",
    "brother": "brother",
    "sister": "sister",
    "spouse": "wife",
    "spouse / children": "wife",
    "parents": "father",
}


def copy_relation_name(apps, schema_editor):
    Family = apps.get_model("common", "Family")
    for member in Family.objects.all():
        raw = (getattr(member, "relation_name", None) or "").strip()
        mapped = RELATION_ALIASES.get(raw.lower())
        member.relation = mapped or "father"
        if mapped:
            member.name = (member.remarks or "").strip() or raw or "—"
        else:
            member.name = raw or "—"
        member.save(update_fields=["relation", "name"])


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0022_ere_organization"),
    ]

    operations = [
        migrations.AddField(
            model_name="family",
            name="mobile_number",
            field=models.CharField(blank=True, max_length=15),
        ),
        migrations.AddField(
            model_name="family",
            name="name",
            field=models.CharField(default="—", max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="family",
            name="relation",
            field=models.CharField(
                choices=[
                    ("father", "Father"),
                    ("mother", "Mother"),
                    ("wife", "Wife"),
                    ("husband", "Husband"),
                    ("son", "Son"),
                    ("daughter", "Daughter"),
                    ("brother", "Brother"),
                    ("sister", "Sister"),
                ],
                default="father",
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(copy_relation_name, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="family",
            name="relation_name",
        ),
        migrations.AlterModelOptions(
            name="family",
            options={
                "ordering": ["relation", "name", "id"],
                "verbose_name": "Family member",
                "verbose_name_plural": "Family members",
            },
        ),
    ]

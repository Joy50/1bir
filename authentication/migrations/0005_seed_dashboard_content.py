from django.db import migrations


def seed_dashboard(apps, schema_editor):
    UnitProfile = apps.get_model("authentication", "UnitProfile")
    UnitHighlight = apps.get_model("authentication", "UnitHighlight")
    UnitAchievement = apps.get_model("authentication", "UnitAchievement")

    UnitProfile.objects.get_or_create(
        pk=1,
        defaults={
            "unit_name": "1 Bangladesh Infantry Regiment",
            "short_name": "1 BIR",
            "motto": "The Gallant One",
            "location": "Ramu Cantonment, Cox's Bazar",
            "about": (
                "1 Bangladesh Infantry Regiment — The Gallant One — is stationed at "
                "Ramu Cantonment. This page records the battalion identity, "
                "Commanding Officers, and unit achievements."
            ),
        },
    )

    if not UnitHighlight.objects.exists():
        UnitHighlight.objects.bulk_create(
            [
                UnitHighlight(
                    title="Honour",
                    body="The battalion upholds the honour of the Bangladesh Infantry Regiment.",
                    icon="bi-award",
                    display_order=10,
                ),
                UnitHighlight(
                    title="Discipline",
                    body="Standards of drill, turnout, and conduct are maintained without compromise.",
                    icon="bi-shield-check",
                    display_order=20,
                ),
                UnitHighlight(
                    title="Readiness",
                    body="The unit remains prepared for operations, training, and ceremonial duty.",
                    icon="bi-lightning-charge",
                    display_order=30,
                ),
                UnitHighlight(
                    title="The family",
                    body="Every soldier of 1 BIR is part of one battalion family.",
                    icon="bi-people",
                    display_order=40,
                ),
            ]
        )

    if not UnitAchievement.objects.exists():
        UnitAchievement.objects.bulk_create(
            [
                UnitAchievement(
                    title="The Gallant One",
                    year="",
                    description=(
                        "The battalion identity of 1 Bangladesh Infantry Regiment, "
                        "stationed at Ramu Cantonment."
                    ),
                    display_order=10,
                ),
            ]
        )


def unseed_dashboard(apps, schema_editor):
    UnitProfile = apps.get_model("authentication", "UnitProfile")
    UnitHighlight = apps.get_model("authentication", "UnitHighlight")
    UnitAchievement = apps.get_model("authentication", "UnitAchievement")
    UnitAchievement.objects.filter(title="The Gallant One").delete()
    UnitHighlight.objects.filter(
        title__in=["Honour", "Discipline", "Readiness", "The family"]
    ).delete()
    UnitProfile.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0004_dashboardslide_halloffameco_unitachievement_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_dashboard, unseed_dashboard),
    ]

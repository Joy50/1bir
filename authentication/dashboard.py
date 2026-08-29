from .models import (
    DashboardSlide,
    HallOfFameCO,
    UnitAchievement,
    UnitHighlight,
    UnitProfile,
)


def get_dashboard_payload():
    current_co = (
        HallOfFameCO.objects.filter(is_published=True, is_current=True).first()
        or HallOfFameCO.objects.filter(
            is_published=True, tenure_end__isnull=True
        ).first()
    )
    return {
        "unit_profile": UnitProfile.load(),
        "dashboard_slides": list(
            DashboardSlide.objects.filter(is_published=True)
        ),
        "current_co": current_co,
        "hall_of_fame": list(HallOfFameCO.objects.filter(is_published=True)),
        "achievements": list(UnitAchievement.objects.filter(is_published=True)),
        "highlights": list(UnitHighlight.objects.filter(is_published=True)),
    }

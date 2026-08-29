from authentication.models import User

from .models import AnnualPerformanceReport, Person, Rank


def get_admin_statistics():
    return {
        "persons": Person.objects.count(),
        "ranks": Rank.objects.count(),
        "reports": AnnualPerformanceReport.objects.count(),
        "users": User.objects.count(),
    }

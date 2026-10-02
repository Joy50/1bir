from collections import Counter

from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from common.scoping import get_company_of

from .models import LeaveState, ParticipationInMajCom, YearlyPlan

CYCLES = [cycle for cycle, _label in YearlyPlan.CYCLE_CHOICES]
CYCLE_FIELDS = [
    ("cycle_1st", "1st Cycle"),
    ("cycle_2nd", "2nd Cycle"),
    ("cycle_3rd", "3rd Cycle"),
    ("cycle_4th", "4th Cycle"),
]
OPTION_LABELS = dict(YearlyPlan.OPTION_CHOICES)
OPTION_SLUGS = {
    "PLve": "plve",
    "GP Trg": "gptrg",
    "Course": "course",
    "Admin": "admin",
}


def leave_board_url(soldier, year=None):
    year = year or timezone.localdate().year
    company = get_company_of(getattr(soldier, "organization", None))
    url = reverse("training:leave_list")
    if company:
        return f"{url}?company={company.pk}&year={year}"
    return f"{url}?year={year}"


def is_privilege_or_casual_slot(slot):
    return slot == LeaveState.SLOT_P_LEAVE or LeaveState.is_casual_slot(slot)


def attach_cycle_plans(soldiers, year):
    plans_by_soldier = {}
    if soldiers:
        plans = YearlyPlan.objects.filter(
            solider_id__in=[soldier.pk for soldier in soldiers],
            year=year,
        )
        for plan in plans:
            plans_by_soldier.setdefault(plan.solider_id, {})[plan.cycle] = plan.option

    for soldier in soldiers:
        mapping = plans_by_soldier.get(soldier.pk, {})
        soldier.cycle_plan = [
            {
                "cycle": cycle,
                "option": mapping.get(cycle),
                "option_label": OPTION_LABELS.get(mapping.get(cycle), "—"),
                "option_slug": OPTION_SLUGS.get(mapping.get(cycle), "empty"),
            }
            for cycle in CYCLES
        ]
        soldier.plan_complete = all(mapping.get(cycle) for cycle in CYCLES)


def get_yearly_plan_statistics(soldiers, year):
    total = soldiers.count()
    plans = YearlyPlan.objects.filter(solider__in=soldiers, year=year)
    planned = plans.values("solider_id").distinct().count()
    cycle_counts = Counter(plans.values_list("solider_id", flat=True))
    complete = sum(1 for count in cycle_counts.values() if count >= len(CYCLES))

    option_totals = {option: 0 for option in OPTION_LABELS}
    for row in plans.values("option").annotate(total=Count("id")):
        option_totals[row["option"]] = row["total"]

    slot_total = sum(option_totals.values())
    by_option = []
    for option, label in OPTION_LABELS.items():
        count = option_totals[option]
        by_option.append(
            {
                "option": option,
                "label": label,
                "total": count,
                "percent": round((count * 100 / slot_total), 1) if slot_total else 0,
            }
        )

    return {
        "year": year,
        "total": total,
        "planned": planned,
        "unplanned": max(total - planned, 0),
        "complete": complete,
        "by_option": by_option,
        "charts": {
            "coverage_labels": ["Planned", "Not planned"],
            "coverage_values": [planned, max(total - planned, 0)],
            "option_labels": [row["label"] for row in by_option],
            "option_values": [row["total"] for row in by_option],
        },
    }


MAJCOM_FIELDS = [
    ("gp_trg", "GP Trg"),
    ("st", "ST"),
    ("wt", "WT"),
    ("fi", "FI"),
    ("ihwf", "IHWF"),
    ("ff", "FF"),
]


def attach_majcom(soldiers, year):
    records = {}
    if soldiers:
        records = {
            row.solider_id: row
            for row in ParticipationInMajCom.objects.filter(
                solider_id__in=[soldier.pk for soldier in soldiers],
                year=year,
            )
        }

    for soldier in soldiers:
        record = records.get(soldier.pk)
        soldier.majcom = record
        soldier.majcom_values = [
            {
                "field": field_name,
                "label": label,
                "value": getattr(record, field_name, "") or "—",
            }
            for field_name, label in MAJCOM_FIELDS
        ]
        soldier.majcom_complete = bool(record) and all(
            getattr(record, field_name)
            for field_name, _label in MAJCOM_FIELDS
        )


def get_majcom_statistics(soldiers, year):
    total = soldiers.count()
    records = ParticipationInMajCom.objects.filter(solider__in=soldiers, year=year)
    recorded = records.count()
    complete = 0
    field_totals = {field_name: 0 for field_name, _label in MAJCOM_FIELDS}

    for record in records:
        filled = True
        for field_name, _label in MAJCOM_FIELDS:
            if getattr(record, field_name):
                field_totals[field_name] += 1
            else:
                filled = False
        if filled:
            complete += 1

    by_field = [
        {
            "field": field_name,
            "label": label,
            "total": field_totals[field_name],
            "percent": round((field_totals[field_name] * 100 / total), 1)
            if total
            else 0,
        }
        for field_name, label in MAJCOM_FIELDS
    ]

    return {
        "year": year,
        "total": total,
        "recorded": recorded,
        "unrecorded": max(total - recorded, 0),
        "complete": complete,
        "by_field": by_field,
        "charts": {
            "coverage_labels": ["Recorded", "Not recorded"],
            "coverage_values": [recorded, max(total - recorded, 0)],
            "field_labels": [row["label"] for row in by_field],
            "field_values": [row["total"] for row in by_field],
        },
    }

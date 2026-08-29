from collections import defaultdict

from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from common.models import Organization, Person
from common.scoping import get_accessible_organization_ids, organization_lookup, rollup_to_parade_organization
from training.models import LeaveState

from .models import (
    PARADE_ABSENCE_COLUMNS,
    PARADE_AUTHORIZED_DEFAULTS,
    PARADE_RANK_COLUMNS,
    DutyAssignment,
    DutyPost,
    DutyTour,
    ParadeState,
    ParadeStateCompany,
)

# Ramu Cantonment, Cox's Bazar
RAMU_LAT = 21.4324
RAMU_LNG = 92.1008
MAP_DEFAULT_ZOOM = 15


def parade_rank_key(rank_name):
    """Map the rank/trade names in personnel records to parade-state columns."""
    import re

    value = re.sub(r"[^A-Z0-9]", "", (rank_name or "").upper())
    exact = {
        "MWO": "mwo", "SWO": "swo", "WO": "wo", "SGT": "sgt",
        "CPL": "cpl", "LCPL": "lcpl", "SNK": "snk", "SAINIK": "snk",
        "CLK": "clk", "CLERK": "clk", "CKU": "ck_u", "COOKU": "ck_u",
        "CKM": "ck_m", "COOKM": "ck_m", "NCE": "nc_e", "NCU": "nc_u",
        "TDN": "tdn", "ATT": "att", "RCO": "rco",
    }
    if value in exact:
        return exact[value]
    officer_terms = ("GEN", "COL", "MAJ", "CAPT", "LT", "LIEUTENANT", "OFFR", "OFFICER")
    if any(term in value for term in officer_terms):
        return "offr"
    return "snk"


def parade_absence_key(leave):
    if LeaveState.is_casual_slot(leave.slot):
        return "c_l"
    mapped = LeaveState.SLOT_ABSENCE_KEYS.get(leave.slot)
    if mapped:
        return mapped
    name = (leave.leave_type.name or "").lower()
    mappings = {
        "privilege": "p_l", "casual": "c_l", "joining": "j_l", "medical": "m_l",
        "course": "course", "cadre": "cadre", "command": "comd",
        "attachment": "att", "hospital": "hosp", "demobilization": "demob",
        "field mission": "fdmn", "teknaf": "teknaf", "osl": "osl",
    }
    for needle, key in mappings.items():
        if needle in name:
            return key
    return "c_l"


@transaction.atomic
def generate_parade_state(user, report_date=None, refresh=False):
    """Build or refresh a daily parade state from personnel and leave data."""
    report_date = report_date or timezone.localdate()
    state = ParadeState.objects.filter(report_date=report_date).first()
    if state and not refresh:
        return state
    if state is None:
        state = ParadeState.objects.create(
            report_date=report_date,
            created_by=user,
            authorized_strength=PARADE_AUTHORIZED_DEFAULTS,
        )
    elif not state.authorized_strength:
        state.authorized_strength = PARADE_AUTHORIZED_DEFAULTS
        state.save(update_fields=["authorized_strength", "updated_at"])

    rank_keys = [key for key, _label in PARADE_RANK_COLUMNS]
    absence_keys = [key for key, _label in PARADE_ABSENCE_COLUMNS]
    posted = defaultdict(lambda: {key: 0 for key in rank_keys})
    absent = defaultdict(lambda: {key: 0 for key in rank_keys})
    details = defaultdict(lambda: {key: 0 for key in absence_keys})

    people = list(Person.objects.select_related("rank", "organization"))
    orgs_by_id = organization_lookup()
    for person in people:
        bucket = rollup_to_parade_organization(person.organization, orgs_by_id)
        if bucket is None:
            continue
        posted[bucket.pk][parade_rank_key(person.rank.rank_name)] += 1

    active_leaves = LeaveState.objects.filter(
        status=LeaveState.STATUS_APPROVED,
        from_date__lte=report_date,
        to_date__gte=report_date,
    ).select_related("solider__rank", "solider__organization", "leave_type")
    counted_people = set()
    for leave in active_leaves:
        person = leave.solider
        if person.pk in counted_people:
            continue
        counted_people.add(person.pk)
        bucket = rollup_to_parade_organization(person.organization, orgs_by_id)
        if bucket is None:
            continue
        organization_id = bucket.pk
        absent[organization_id][parade_rank_key(person.rank.rank_name)] += 1
        details[organization_id][parade_absence_key(leave)] += 1

    organization_ids = set(posted.keys()) | set(absent.keys())
    organization_ids.update(
        Organization.objects.filter(
            unit_kind__in=(
                Organization.KIND_UNIT,
                Organization.KIND_BATTALION,
                Organization.KIND_COMPANY,
            )
        ).values_list("pk", flat=True)
    )
    state.company_states.exclude(organization_id__in=organization_ids).delete()
    for organization_id in organization_ids:
        ParadeStateCompany.objects.update_or_create(
            parade_state=state,
            organization_id=organization_id,
            defaults={
                "posted_strength": posted[organization_id],
                "absent_strength": absent[organization_id],
                "absence_details": details[organization_id],
            },
        )
    return state


def get_open_tour():
    return DutyTour.objects.filter(status=DutyTour.STATUS_OPEN).first()


@transaction.atomic
def get_or_create_open_tour():
    tour = (
        DutyTour.objects.select_for_update()
        .filter(status=DutyTour.STATUS_OPEN)
        .first()
    )
    if tour:
        return tour
    last_number = (
        DutyTour.objects.select_for_update()
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    return DutyTour.objects.create(number=(last_number or 0) + 1)


def scoped_soldiers(user):
    queryset = Person.objects.select_related("rank", "organization").order_by(
        "army_number"
    )
    allowed_ids = get_accessible_organization_ids(user)
    if allowed_ids is not None:
        queryset = queryset.filter(organization_id__in=allowed_ids)
    return queryset


def soldiers_on_leave(soldier_ids=None):
    today = timezone.localdate()
    queryset = LeaveState.objects.filter(
        status=LeaveState.STATUS_APPROVED,
        from_date__lte=today,
        to_date__gte=today,
    )
    if soldier_ids is not None:
        queryset = queryset.filter(solider_id__in=soldier_ids)
    return set(queryset.values_list("solider_id", flat=True))


def tour_progress(user):
    tour = get_open_tour()
    soldiers = list(scoped_soldiers(user))
    on_leave = soldiers_on_leave([soldier.pk for soldier in soldiers])
    expected = [soldier for soldier in soldiers if soldier.pk not in on_leave]
    assignments = []
    if tour:
        assignments = list(
            tour.assignments.select_related("soldier", "soldier__rank", "post")
            .exclude(status=DutyAssignment.STATUS_CANCELLED)
        )
    by_soldier = {row.soldier_id: row for row in assignments}
    still_due = []
    on_duty = []
    finished = []
    for soldier in expected:
        row = by_soldier.get(soldier.pk)
        if row is None:
            still_due.append(soldier)
        elif row.status == DutyAssignment.STATUS_ON_DUTY:
            on_duty.append(row)
        elif row.status == DutyAssignment.STATUS_COMPLETED:
            finished.append(row)
    can_report = bool(tour and expected and not still_due and not on_duty)
    return {
        "tour": tour,
        "expected": expected,
        "still_due": still_due,
        "on_duty": on_duty,
        "finished": finished,
        "on_leave_count": len(on_leave),
        "can_report": can_report,
    }


def suggested_soldiers(user, limit=12):
    progress = tour_progress(user)
    occupied_posts = {row.post_id for row in progress["on_duty"]}
    due = progress["still_due"]
    last_completed = DutyAssignment.objects.filter(
        soldier_id=OuterRef("pk"),
        status=DutyAssignment.STATUS_COMPLETED,
    ).order_by("-completed_at")
    completed_at = {
        row.pk: row.last_completed
        for row in Person.objects.filter(pk__in=[soldier.pk for soldier in due]).annotate(
            last_completed=Subquery(last_completed.values("completed_at")[:1])
        )
    }
    suggestions = [
        {
            "soldier": soldier,
            "last_completed": completed_at.get(soldier.pk),
            "reason": "Not yet detailed in this tour",
        }
        for soldier in due
    ]
    suggestions.sort(
        key=lambda item: (
            item["last_completed"] is not None,
            item["last_completed"] or timezone.now(),
        )
    )
    if limit is not None:
        suggestions = suggestions[:limit]
    return suggestions, occupied_posts, progress


def available_posts():
    return DutyPost.objects.filter(is_active=True)


def map_markers(user):
    progress = tour_progress(user)
    on_duty_by_post = {row.post_id: row for row in progress["on_duty"]}
    markers = []
    for post in DutyPost.objects.filter(is_active=True):
        assignment = on_duty_by_post.get(post.pk)
        markers.append(
            {
                "id": post.pk,
                "name": post.name,
                "lat": float(post.latitude),
                "lng": float(post.longitude),
                "description": post.description,
                "organization": str(post.organization) if post.organization_id else "",
                "soldier": assignment.soldier.name if assignment else "",
                "army_number": assignment.soldier.army_number if assignment else "",
                "rank": str(assignment.soldier.rank) if assignment else "",
                "status": "On duty" if assignment else "Vacant",
            }
        )
    return markers, progress

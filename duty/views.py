import calendar
import json
from datetime import date, timedelta

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from authentication.views import (
    AdminRequiredMixin,
    CoRequiredMixin,
    DutyAssignMixin,
    OfficerActionMixin,
    PortalContextMixin,
)
<<<<<<< HEAD
from common.activity import log_addition, log_change, log_deletion
from common.models import Organization, Person, ServiceHistory
from common.http import safe_redirect_target
from common.scoping import (
    collect_descendant_ids,
    get_accessible_companies,
    get_accessible_organization_ids,
    get_accessible_organizations,
    get_parade_organizations,
)
from common.views import SoldierAccessMixin

from .forms import DutyAssignForm, DutyPostForm, ParadeAbsenceDocumentForm, SoldierPostingForm
=======
from common.activity import log_addition, log_change
from common.models import Organization, Person, ServiceHistory
from common.scoping import (
    collect_descendant_ids,
    get_accessible_organization_ids,
    get_accessible_organizations,
)
from common.views import SoldierAccessMixin

from .forms import DutyAssignForm, DutyPostForm, SoldierPostingForm
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf
from .models import (
    PARADE_ABSENCE_COLUMNS,
    PARADE_AUTHORIZED_DEFAULTS,
    PARADE_RANK_COLUMNS,
    DutyAssignment,
    DutyPost,
    DutyTour,
<<<<<<< HEAD
    ParadeAbsenceDocument,
    ParadeState,
=======
    ParadeState,
    ParadeStateCompany,
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf
    SoldierPosting,
)
from authentication.portal import get_portal_context
from .services import (
    MAP_DEFAULT_ZOOM,
    RAMU_LAT,
    RAMU_LNG,
    get_or_create_open_tour,
    generate_parade_state,
    map_markers,
    scoped_soldiers,
    suggested_soldiers,
    tour_progress,
)


class DutyHomeView(SoldierAccessMixin, TemplateView):
    template_name = "duty/home.html"

    def get_form_kwargs(self):
        return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["progress"] = tour_progress(self.request.user)
        pending = SoldierPosting.objects.filter(
            status=SoldierPosting.STATUS_PENDING
        ).select_related("soldier", "from_organization", "to_organization", "posted_by")
        allowed_ids = get_accessible_organization_ids(self.request.user)
        if allowed_ids is not None:
            pending = pending.filter(to_organization_id__in=allowed_ids)
        context["pending_postings"] = pending
<<<<<<< HEAD
        organizations = get_accessible_companies(self.request.user)
=======
        organizations = self.get_allowed_organizations().filter(
            parent_organization__organization_name="1 BIR",
            organization_name__in=[
                "A Company", "B Company", "C Company", "D Company", "HQ Company",
            ],
        ).order_by("organization_name")
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf
        selected_id = self.request.GET.get("company", "")
        selected_organization = None
        if selected_id.isdigit():
            selected_organization = organizations.filter(pk=int(selected_id)).first()

        posts = DutyPost.objects.filter(is_active=True).select_related("organization")
        if selected_organization:
            posts = posts.filter(
                Q(organization=selected_organization) | Q(organization__isnull=True)
            )
        posts = list(posts.order_by("duty_type", "display_order", "name"))

        assignments = DutyAssignment.objects.filter(
            status=DutyAssignment.STATUS_ON_DUTY,
            post_id__in=[post.pk for post in posts],
        )
        if selected_organization:
            assignments = assignments.filter(
                soldier__organization_id__in=collect_descendant_ids(selected_organization)
            )
        else:
            accessible_ids = self.get_allowed_organization_ids()
            if accessible_ids is not None:
                assignments = assignments.filter(
                    soldier__organization_id__in=accessible_ids
                )
        live_counts = {
            post.pk: {"day": 0, "night": 0} for post in posts
        }
        for assignment in assignments.only("post_id", "shift"):
            if assignment.post_id in live_counts:
                live_counts[assignment.post_id][assignment.shift] += 1

        serial = 1
        duty_sections = []
        day_total = 0
        night_total = 0
        for duty_type, label in DutyPost.TYPE_CHOICES:
            rows = []
            for post in posts:
                if post.duty_type != duty_type:
                    continue
                counts = live_counts[post.pk]
                rows.append({
                    "serial": serial,
                    "post": post,
                    "day": counts[DutyAssignment.SHIFT_DAY],
                    "night": counts[DutyAssignment.SHIFT_NIGHT],
                    "total": counts[DutyAssignment.SHIFT_DAY] + counts[DutyAssignment.SHIFT_NIGHT],
                })
                day_total += counts[DutyAssignment.SHIFT_DAY]
                night_total += counts[DutyAssignment.SHIFT_NIGHT]
                serial += 1
            duty_sections.append({"key": duty_type, "label": label, "rows": rows})

        calendar_weeks = []
        calendar_month = None
        previous_month = None
        next_month = None
        selected_calendar_day = None
        selected_day_rows = []
        if selected_organization:
            today = timezone.localdate()
            month_value = self.request.GET.get("month", "")
            try:
                year, month = (int(part) for part in month_value.split("-", 1))
                calendar_month = date(year, month, 1)
            except (TypeError, ValueError):
                calendar_month = today.replace(day=1)

            if calendar_month.month == 1:
                previous_month = date(calendar_month.year - 1, 12, 1)
            else:
                previous_month = date(calendar_month.year, calendar_month.month - 1, 1)
            if calendar_month.month == 12:
                next_month = date(calendar_month.year + 1, 1, 1)
            else:
                next_month = date(calendar_month.year, calendar_month.month + 1, 1)
            month_end = next_month - timedelta(days=1)

            company_ids = collect_descendant_ids(selected_organization)
            month_assignments = DutyAssignment.objects.filter(
                soldier__organization_id__in=company_ids,
                assigned_at__date__lte=month_end,
            ).exclude(status=DutyAssignment.STATUS_CANCELLED).filter(
                Q(completed_at__isnull=True) | Q(completed_at__date__gte=calendar_month)
            ).select_related("soldier", "soldier__rank", "soldier__organization", "post")

            assignments_by_day = {}
            for assignment in month_assignments:
                start_day = max(
                    timezone.localtime(assignment.assigned_at).date(),
                    calendar_month,
                )
                end_day = min(
                    timezone.localtime(assignment.completed_at).date()
                    if assignment.completed_at else today,
                    month_end,
                )
                current_day = start_day
                while current_day <= end_day:
                    assignments_by_day.setdefault(current_day, []).append(assignment)
                    current_day += timedelta(days=1)

            month_calendar = calendar.Calendar(firstweekday=0)
            for week in month_calendar.monthdatescalendar(
                calendar_month.year, calendar_month.month
            ):
                calendar_weeks.append([
                    {
                        "date": day,
                        "in_month": day.month == calendar_month.month,
                        "is_today": day == today,
                        "assignments": assignments_by_day.get(day, []),
                    }
                    for day in week
                ])

            selected_day_value = self.request.GET.get("day", "")
            try:
                candidate_day = date.fromisoformat(selected_day_value)
                if candidate_day.year == calendar_month.year and candidate_day.month == calendar_month.month:
                    selected_calendar_day = candidate_day
            except (TypeError, ValueError):
                selected_calendar_day = None

            if selected_calendar_day:
                by_soldier = {}
                for assignment in assignments_by_day.get(selected_calendar_day, []):
                    row = by_soldier.setdefault(assignment.soldier_id, {
                        "soldier": assignment.soldier,
                        "platoon": (
                            "Coy HQ"
                            if assignment.soldier.organization_id == selected_organization.pk
                            else assignment.soldier.organization.organization_name
                        ),
                        "day": 0,
                        "night": 0,
                    })
                    row[assignment.shift] += 1
                selected_day_rows = list(by_soldier.values())
                selected_day_rows.sort(key=lambda row: row["soldier"].army_number)
                for index, row in enumerate(selected_day_rows, start=1):
                    row["serial"] = index
                    row["total"] = row["day"] + row["night"]
        context.update({
            "organizations": organizations,
            "selected_organization": selected_organization,
            "selected_company_id": str(selected_organization.pk) if selected_organization else "",
            "duty_sections": duty_sections,
            "duty_day_total": day_total,
            "duty_night_total": night_total,
            "duty_total": day_total + night_total,
            "calendar_weeks": calendar_weeks,
            "calendar_month": calendar_month,
            "previous_month": previous_month,
            "next_month": next_month,
            "selected_calendar_day": selected_calendar_day,
            "selected_day_rows": selected_day_rows,
            "selected_day_day_total": sum(row["day"] for row in selected_day_rows),
            "selected_day_night_total": sum(row["night"] for row in selected_day_rows),
        })
        return context


class DutyPostListView(PortalContextMixin, AdminRequiredMixin, ListView):
    model = DutyPost
    template_name = "duty/post_list.html"
    context_object_name = "posts"


class DutyPostCreateView(PortalContextMixin, AdminRequiredMixin, CreateView):
    model = DutyPost
    form_class = DutyPostForm
    template_name = "duty/post_form.html"
    success_url = reverse_lazy("duty:post_list")

    def get_initial(self):
        initial = super().get_initial()
        initial.setdefault("latitude", RAMU_LAT)
        initial.setdefault("longitude", RAMU_LNG)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["map_lat"] = RAMU_LAT
        context["map_lng"] = RAMU_LNG
        context["map_zoom"] = MAP_DEFAULT_ZOOM
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_addition(self.request.user, self.object, "Duty post created.")
        messages.success(self.request, f"Duty post '{self.object.name}' added.")
        return response


class DutyPostUpdateView(PortalContextMixin, AdminRequiredMixin, UpdateView):
    model = DutyPost
    form_class = DutyPostForm
    template_name = "duty/post_form.html"
    success_url = reverse_lazy("duty:post_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["map_lat"] = float(self.object.latitude) if self.object.latitude else RAMU_LAT
        context["map_lng"] = float(self.object.longitude) if self.object.longitude else RAMU_LNG
        context["map_zoom"] = MAP_DEFAULT_ZOOM
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_change(self.request.user, self.object, "Duty post updated.")
        messages.success(self.request, f"Duty post '{self.object.name}' updated.")
        return response


class SoldierPostingListView(SoldierAccessMixin, ListView):
    model = SoldierPosting
    template_name = "duty/posting_list.html"
    context_object_name = "postings"
    paginate_by = None

    def get_queryset(self):
        queryset = SoldierPosting.objects.select_related(
            "soldier",
            "soldier__rank",
            "from_organization",
            "to_organization",
            "posted_by",
            "accepted_by",
        )
        allowed_ids = self.get_allowed_organization_ids()
        if allowed_ids is not None and not self.request.user.can_command:
            queryset = queryset.filter(
                Q(to_organization_id__in=allowed_ids)
                | Q(from_organization_id__in=allowed_ids)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
<<<<<<< HEAD
        companies = get_accessible_companies(self.request.user)
=======
        companies = self.get_allowed_organizations().filter(
            parent_organization__organization_name="1 BIR",
            organization_name__in=[
                "A Company", "B Company", "C Company", "D Company", "HQ Company",
            ],
        ).order_by("organization_name")
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf
        company_value = self.request.GET.get("company", "")
        selected_company = None
        if company_value.isdigit():
            selected_company = companies.filter(pk=int(company_value)).first()
        if selected_company is None:
            selected_company = companies.first()

        soldier_rows = []
        if selected_company:
            soldiers = Person.objects.filter(
                organization_id__in=collect_descendant_ids(selected_company)
            ).select_related("rank", "organization", "organization__parent_organization").order_by(
                "army_number"
            )
            pending_by_soldier = {
                posting.soldier_id: posting
                for posting in SoldierPosting.objects.filter(
                    soldier__in=soldiers,
                    status=SoldierPosting.STATUS_PENDING,
                ).select_related("to_organization")
            }
            for soldier in soldiers:
                histories = list(ServiceHistory.objects.filter(
                    person=soldier
                ).select_related("organization").order_by("-start_date", "-pk"))
                current_history = next(
                    (history for history in histories if history.end_date is None),
                    None,
                )
                previous_history = next(
                    (history for history in histories if history.end_date is not None),
                    None,
                )
                history_duration = ""
                if previous_history and previous_history.end_date:
                    days = (previous_history.end_date - previous_history.start_date).days
                    years, remaining = divmod(max(days, 0), 365)
                    months = remaining // 30
                    history_duration = " ".join(
                        part for part in (
                            f"{years}y" if years else "",
                            f"{months}m" if months else "",
                        ) if part
                    ) or f"{max(days, 0)}d"
                soldier_rows.append({
                    "soldier": soldier,
                    "platoon": (
                        "Coy HQ" if soldier.organization_id == selected_company.pk
                        else soldier.organization.organization_name
                    ),
                    "current_unit": selected_company,
                    "current_att_ere": (
                        "" if soldier.organization_id == selected_company.pk
                        else soldier.organization.organization_name
                    ),
                    "current_history": current_history,
                    "previous_history": previous_history,
                    "history_duration": history_duration,
                    "pending": pending_by_soldier.get(soldier.pk),
                })

        context.update({
            "companies": companies,
            "selected_company": selected_company,
            "soldier_rows": soldier_rows,
        })
        context["can_post"] = self.request.user.can_command
        context["can_accept"] = self.request.user.can_accept_posting
        return context


class SoldierPostingCreateView(PortalContextMixin, CoRequiredMixin, CreateView):
    model = SoldierPosting
    form_class = SoldierPostingForm
    template_name = "duty/posting_form.html"
    success_url = reverse_lazy("duty:posting_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["soldier_queryset"] = scoped_soldiers(self.request.user)
        kwargs["organization_queryset"] = Organization.objects.all()
        return kwargs

    def form_valid(self, form):
        posting = form.save(commit=False)
        posting.from_organization = posting.soldier.organization
        posting.posted_by = self.request.user
        posting.status = SoldierPosting.STATUS_PENDING
        posting.save()
        self.object = posting
        log_addition(
            self.request.user,
            posting,
            f"Posted {posting.soldier} to {posting.to_organization}.",
        )
        messages.success(
            self.request,
            f"{posting.soldier.name} posted to {posting.to_organization}. "
            "An officer must accept him before the move takes effect.",
        )
        return redirect(self.success_url)


class SoldierPostingDecideView(PortalContextMixin, OfficerActionMixin, View):
    def post(self, request, *args, **kwargs):
        queryset = SoldierPosting.objects.select_related("soldier", "to_organization")
        allowed_ids = get_accessible_organization_ids(request.user)
        if allowed_ids is not None:
            queryset = queryset.filter(to_organization_id__in=allowed_ids)
        posting = get_object_or_404(queryset, pk=kwargs["pk"])
        if posting.status != SoldierPosting.STATUS_PENDING:
            messages.error(request, "This posting has already been decided.")
            return redirect("duty:posting_list")

        action = request.POST.get("action", "accept")
        with transaction.atomic():
            posting.decided_at = timezone.now()
            if action == "reject":
                posting.status = SoldierPosting.STATUS_REJECTED
                posting.accepted_by = None
                posting.remarks = request.POST.get("remarks", "").strip() or posting.remarks
                posting.save()
                message = f"Posting of {posting.soldier.name} rejected."
            else:
                soldier = posting.soldier
                today = timezone.localdate()
<<<<<<< HEAD
                open_history = ServiceHistory.objects.filter(
                    person=soldier,
                    end_date__isnull=True,
                ).order_by("-start_date", "-pk").first()
                if open_history and open_history.start_date == today:
                    open_history.organization = posting.to_organization
                    open_history.rank = soldier.rank
                    open_history.save(update_fields=["organization", "rank"])
                else:
                    ServiceHistory.objects.filter(
                        person=soldier,
                        end_date__isnull=True,
                    ).update(end_date=today)
                    ServiceHistory.objects.create(
                        person=soldier,
                        organization=posting.to_organization,
                        rank=soldier.rank,
                        start_date=today,
                    )
=======
                ServiceHistory.objects.filter(
                    person=soldier,
                    end_date__isnull=True,
                ).update(end_date=today)
                ServiceHistory.objects.create(
                    person=soldier,
                    organization=posting.to_organization,
                    rank=soldier.rank,
                    start_date=today,
                )
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf
                soldier.organization = posting.to_organization
                soldier.save(update_fields=["organization"])
                posting.status = SoldierPosting.STATUS_ACCEPTED
                posting.accepted_by = request.user
                posting.save()
                message = (
                    f"{soldier.name} accepted into {posting.to_organization}."
                )

        log_change(request.user, posting.soldier, message)
        messages.success(request, message)
        return redirect("duty:posting_list")


class DutyAssignView(DutyAssignMixin, SoldierAccessMixin, CreateView):
    model = DutyAssignment
    form_class = DutyAssignForm
    template_name = "duty/assign.html"
    success_url = reverse_lazy("duty:assign")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop("organization_queryset", None)
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        suggestions, _occupied, progress = suggested_soldiers(self.request.user)
        context["suggestions"] = suggestions
        context["progress"] = progress
        form = context["form"]
        context["can_assign_now"] = (
            form.fields["soldier"].queryset.exists()
            and form.fields["post"].queryset.exists()
        )
        return context

    def form_valid(self, form):
        assignment = form.save(commit=False)
        assignment.tour = get_or_create_open_tour()
        assignment.assigned_by = self.request.user
        assignment.status = DutyAssignment.STATUS_ON_DUTY
        assignment.save()
        log_addition(
            self.request.user,
            assignment,
            f"{assignment.soldier} assigned to {assignment.post}.",
        )
        messages.success(
            self.request,
            f"{assignment.soldier.name} is now on duty at {assignment.post}.",
        )
        return redirect(self.success_url)


class DutyCompleteView(PortalContextMixin, DutyAssignMixin, View):
    def post(self, request, *args, **kwargs):
<<<<<<< HEAD
        queryset = DutyAssignment.objects.select_related("soldier", "post")
        allowed_ids = get_accessible_organization_ids(request.user)
        if allowed_ids is not None:
            queryset = queryset.filter(soldier__organization_id__in=allowed_ids)
        assignment = get_object_or_404(
            queryset,
=======
        assignment = get_object_or_404(
            DutyAssignment.objects.select_related("soldier", "post"),
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf
            pk=kwargs["pk"],
            status=DutyAssignment.STATUS_ON_DUTY,
        )
        assignment.status = DutyAssignment.STATUS_COMPLETED
        assignment.completed_at = timezone.now()
        assignment.save(update_fields=["status", "completed_at"])
        log_change(
            request.user,
            assignment.soldier,
            f"Duty completed at {assignment.post}.",
        )
        messages.success(
            request,
            f"{assignment.soldier.name} completed duty at {assignment.post}.",
        )
<<<<<<< HEAD
        return redirect(safe_redirect_target(request, "duty:assign"))
=======
        return redirect(request.POST.get("next") or "duty:assign")
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf


class DutyMapView(PortalContextMixin, CoRequiredMixin, TemplateView):
    template_name = "duty/map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        markers, progress = map_markers(self.request.user)
        context["markers_json"] = json.dumps(markers)
        context["progress"] = progress
        context["markers"] = markers
        context["map_lat"] = RAMU_LAT
        context["map_lng"] = RAMU_LNG
        context["map_zoom"] = MAP_DEFAULT_ZOOM
        return context


class DutyTourReportView(PortalContextMixin, CoRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        progress = tour_progress(request.user)
        tour = progress["tour"]
        if not tour:
            messages.error(request, "There is no open duty tour to report.")
            return redirect("duty:map")
        if not progress["can_report"]:
            messages.error(
                request,
                "A tour cannot be reported until every available soldier has finished duty.",
            )
            return redirect("duty:map")
        tour.status = DutyTour.STATUS_REPORTED
        tour.reported_at = timezone.now()
        tour.reported_by = request.user
        tour.save(update_fields=["status", "reported_at", "reported_by"])
        messages.success(
            request,
            f"Duty tour {tour.number} reported. The next tour can now begin.",
        )
        return redirect("duty:map")


class ParadeStateListView(SoldierAccessMixin, View):
    def get(self, request, *args, **kwargs):
<<<<<<< HEAD
        today = timezone.localdate()
        state = ParadeState.objects.filter(report_date=today).first()
        if state is None:
            state = generate_parade_state(request.user, today)
        return redirect("duty:parade_state_edit", pk=state.pk)

    def post(self, request, *args, **kwargs):
        state = generate_parade_state(
            request.user,
            timezone.localdate(),
            refresh=True,
        )
=======
        state = generate_parade_state(request.user)
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf
        return redirect("duty:parade_state_edit", pk=state.pk)


class ParadeStateEditView(SoldierAccessMixin, View):
    template_name = "duty/parade_state_form.html"

    def get_object(self):
        pk = self.kwargs.get("pk")
        if not pk:
            return None
        return get_object_or_404(ParadeState, pk=pk)

    def get_organizations(self):
<<<<<<< HEAD
        return get_parade_organizations(self.request.user)
=======
        return get_accessible_organizations(self.request.user)
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf

    @staticmethod
    def number(value):
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    def matrix_context(self, parade_state, posted=None):
        entries = {}
        if parade_state:
            entries = {
                entry.organization_id: entry
                for entry in parade_state.company_states.filter(
                    organization__in=self.get_organizations()
                )
            }

        rows = []
        rank_totals = {
            key: {"posted": 0, "absent": 0, "present": 0}
            for key, _label in PARADE_RANK_COLUMNS
        }
        absence_totals = {key: 0 for key, _label in PARADE_ABSENCE_COLUMNS}
        for organization in self.get_organizations():
            entry = entries.get(organization.pk)
            posted_values = entry.posted_strength if entry else {}
            absent_values = entry.absent_strength if entry else {}
            detail_values = entry.absence_details if entry else {}
            rank_cells = []
            for key, label in PARADE_RANK_COLUMNS:
                field_posted = f"posted_{organization.pk}_{key}"
                field_absent = f"absent_{organization.pk}_{key}"
                posted_count = self.number(
                    posted.get(field_posted) if posted is not None else posted_values.get(key)
                )
                absent_count = self.number(
                    posted.get(field_absent) if posted is not None else absent_values.get(key)
                )
                present_count = max(0, posted_count - absent_count)
                rank_cells.append({
                    "key": key, "label": label,
                    "posted_name": field_posted, "posted": posted_count,
                    "absent_name": field_absent, "absent": absent_count,
                    "present": present_count,
                })
                rank_totals[key]["posted"] += posted_count
                rank_totals[key]["absent"] += absent_count
                rank_totals[key]["present"] += present_count

            detail_cells = []
            for key, label in PARADE_ABSENCE_COLUMNS:
                field_name = f"detail_{organization.pk}_{key}"
                count = self.number(
                    posted.get(field_name) if posted is not None else detail_values.get(key)
                )
                detail_cells.append({"key": key, "label": label, "name": field_name, "value": count})
                absence_totals[key] += count
            rows.append({
                "organization": organization,
                "rank_cells": rank_cells,
                "detail_cells": detail_cells,
                "posted_total": sum(cell["posted"] for cell in rank_cells),
                "absent_total": sum(cell["absent"] for cell in rank_cells),
                "present_total": sum(cell["present"] for cell in rank_cells),
                "detail_total": sum(cell["value"] for cell in detail_cells),
            })

        authorized = (
            parade_state.authorized_strength
            if parade_state
            else PARADE_AUTHORIZED_DEFAULTS
        )
        auth_cells = []
        for key, label in PARADE_RANK_COLUMNS:
            name = f"authorized_{key}"
            value = self.number(posted.get(name) if posted is not None else authorized.get(key))
            auth_cells.append({"key": key, "label": label, "name": name, "value": value})
        return {
            "rank_columns": PARADE_RANK_COLUMNS,
            "absence_columns": PARADE_ABSENCE_COLUMNS,
            "auth_cells": auth_cells,
            "authorized_total": sum(cell["value"] for cell in auth_cells),
            "rows": rows,
            "posted_grand_total": sum(row["posted_total"] for row in rows),
            "absent_grand_total": sum(row["absent_total"] for row in rows),
            "present_grand_total": sum(row["present_total"] for row in rows),
            "detail_grand_total": sum(row["detail_total"] for row in rows),
            "rank_total_cells": [
                {"key": key, "label": label, **rank_totals[key]}
                for key, label in PARADE_RANK_COLUMNS
            ],
            "absence_total_cells": [
                {"key": key, "label": label, "value": absence_totals[key]}
                for key, label in PARADE_ABSENCE_COLUMNS
            ],
        }

<<<<<<< HEAD
    def render_page(self, parade_state, absence_form=None):
        context = get_portal_context(self.request)
        context.update(self.matrix_context(parade_state))
        context.update(
            {
                "parade_state": parade_state,
                "absence_form": absence_form
                or ParadeAbsenceDocumentForm(
                    initial_date=parade_state.report_date if parade_state else None
                ),
                "absence_documents": (
                    parade_state.absence_documents.select_related("uploaded_by")
                    if parade_state
                    else []
                ),
            }
        )
=======
    def render_page(self, parade_state):
        context = get_portal_context(self.request)
        context.update(self.matrix_context(parade_state))
        context.update({"parade_state": parade_state})
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf
        from django.shortcuts import render
        return render(self.request, self.template_name, context)

    def get(self, request, *args, **kwargs):
<<<<<<< HEAD
        return self.render_page(self.get_object())

    def post(self, request, *args, **kwargs):
        parade_state = self.get_object()
        if request.POST.get("refresh"):
            parade_state = generate_parade_state(
                request.user,
                parade_state.report_date,
                refresh=True,
            )
            return redirect("duty:parade_state_edit", pk=parade_state.pk)

        if request.POST.get("delete_absence"):
            document = get_object_or_404(
                ParadeAbsenceDocument,
                pk=request.POST.get("delete_absence"),
                parade_state=parade_state,
            )
            title = document.title
            log_deletion(request.user, document, "Absence document removed.")
            document.document.delete(save=False)
            document.delete()
            messages.success(request, f'Removed "{title}".')
            return redirect("duty:parade_state_edit", pk=parade_state.pk)

        form = ParadeAbsenceDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.parade_state = parade_state
            document.uploaded_by = request.user
            document.save()
            log_addition(request.user, document, "Absence document uploaded.")
            messages.success(request, f'Uploaded "{document.title}".')
            return redirect("duty:parade_state_edit", pk=parade_state.pk)
        return self.render_page(parade_state, absence_form=form)
=======
        parade_state = self.get_object()
        parade_state = generate_parade_state(request.user, parade_state.report_date)
        return self.render_page(parade_state)
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf

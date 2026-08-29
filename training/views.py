from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import OuterRef, Q, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import FormView, ListView, TemplateView, View

from authentication.views import PortalContextMixin
from common.activity import log_change
from common.models import MedicalCategory, Organization, Person, Rank, ServiceHistory
from common.http import safe_redirect_target
from common.scoping import (
    collect_descendant_ids,
    descendant_ids_by_organization,
    get_accessible_companies,
    get_battalion,
)
from common.views import SoldierAccessMixin

from .forms import (
    AssaultCourseFormSet,
    CASTrophyFormSet,
    GPFiringFormSet,
    GrenadeFiringFormSet,
    IndividualQualForm,
    IPFTFormSet,
    LeaveApplyForm,
    ParticipationInMajComForm,
    QualCourseFormSetFactory,
    SOSNFiringFormSet,
    SoldierYearlyPlanForm,
    SpeedMarchFormSet,
    SportsTrainingFormSet,
    UnitTrainingCyclePlanFormSet,
)
from .models import (
    AssaultCourse,
    CASTrophy,
    FIRING_RESULT_FAIL,
    FIRING_RESULT_PASS,
    GrenadeFiring,
    GPFiring,
    IndividualCourseName,
    IndividualQual,
    IndividualQualCourse,
    IPFT,
    LeaveState,
    ParticipationInMajCom,
    ParticipationInSportsTraining,
    SOSNFiring,
    SpeedMarch,
    UnitTrainingCyclePlan,
    YearlyPlan,
)
from .services import (
    CYCLE_FIELDS,
    CYCLES,
    MAJCOM_FIELDS,
    attach_cycle_plans,
    attach_majcom,
    get_majcom_statistics,
    get_yearly_plan_statistics,
    is_privilege_or_casual_slot,
    leave_board_url,
)


class SoldierYearBoardMixin(SoldierAccessMixin):

    model = Person
    context_object_name = "soldiers"
    paginate_by = 10
    year_source_model = None

    def get_selected_year(self):
        year = self.request.GET.get("year", "").strip()
        current_year = timezone.localdate().year

        if year.isdigit() and 1900 <= int(year) <= 2100:
            return int(year)

        return current_year

    def get_base_queryset(self):
        latest_history = ServiceHistory.objects.filter(
            person_id=OuterRef("pk")
        ).order_by("-start_date", "-pk")

        queryset = Person.objects.select_related(
            "rank",
            "organization",
        ).annotate(
            latest_rank_name=Subquery(
                latest_history.values("rank__rank_name")[:1]
            ),
        ).order_by("army_number")

        allowed_ids = self.get_allowed_organization_ids()
        if allowed_ids is not None:
            queryset = queryset.filter(organization_id__in=allowed_ids)

        return queryset

    def get_queryset(self):
        queryset = self.get_base_queryset()
        search = self.request.GET.get("q", "").strip()
        organization_id = self.request.GET.get("organization", "").strip()
        allowed_ids = self.get_allowed_organization_ids()

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(army_number__icontains=search)
            )

        if organization_id.isdigit():
            org_id = int(organization_id)
            if allowed_ids is None or org_id in allowed_ids:
                queryset = queryset.filter(organization_id=org_id)

        return queryset

    def get_year_choices(self):
        current_year = timezone.localdate().year
        years = set(range(current_year - 2, current_year + 3))

        if self.year_source_model is not None:
            years.update(
                self.year_source_model.objects.values_list("year", flat=True)
            )

        return sorted(years, reverse=True)

    def get_board_context(self, context):
        year = self.get_selected_year()
        soldiers = list(context["soldiers"])
        allowed_orgs = self.get_allowed_organizations()

        context["soldiers"] = soldiers
        context["selected_year"] = year
        context["year_choices"] = self.get_year_choices()
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["organization_filter"] = self.request.GET.get(
            "organization",
            "",
        ).strip()
        context["organizations"] = allowed_orgs
        context["has_company"] = allowed_orgs.exists()
        return soldiers, year, context

    def get_filter_context(self, context):
        soldiers = list(context["soldiers"])
        allowed_orgs = self.get_allowed_organizations()
        context["soldiers"] = soldiers
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["organization_filter"] = self.request.GET.get(
            "organization",
            "",
        ).strip()
        context["organizations"] = allowed_orgs
        context["has_company"] = allowed_orgs.exists()
        return soldiers, context


class SoldierYearEditMixin(SoldierAccessMixin):

    def dispatch(self, request, *args, **kwargs):
        self.soldier = self.get_soldier()
        self.year = self.get_year()
        return super().dispatch(request, *args, **kwargs)

    def get_soldier(self):
        queryset = Person.objects.select_related("rank", "organization")
        allowed_ids = self.get_allowed_organization_ids()

        if allowed_ids is not None:
            queryset = queryset.filter(organization_id__in=allowed_ids)

        soldier = get_object_or_404(queryset, pk=self.kwargs["pk"])

        if allowed_ids is not None and soldier.organization_id not in allowed_ids:
            raise Http404("Soldier not found.")

        return soldier

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop("organization_queryset", None)
        return kwargs

    def get_year(self):
        year = self.request.GET.get("year") or self.request.POST.get("year", "")
        year = str(year).strip()
        current_year = timezone.localdate().year

        if year.isdigit() and 1900 <= int(year) <= 2100:
            return int(year)

        return current_year


class YearlyPlanListView(SoldierAccessMixin, TemplateView):

    template_name = "training/yearly_plan_list.html"

    def get_selected_year(self):
        value = self.request.GET.get("year", "").strip()
        if value.isdigit() and 1900 <= int(value) <= 2100:
            return int(value)
        return timezone.localdate().year

    def get_selected_organization(self):
        value = self.request.GET.get("organization", "").strip()
        if not value.isdigit():
            return None
        organizations = self.get_allowed_organizations()
        return organizations.filter(pk=int(value)).first()

    def get_plan_organization(self):
        return self.get_selected_organization() or get_battalion(self.request.user)

    def get_rows(self, year, organization):
        if organization is None:
            return UnitTrainingCyclePlan.objects.none()
        return UnitTrainingCyclePlan.objects.filter(
            year=year,
            organization=organization,
        ).order_by("cycle")

    def ensure_rows(self, year, organization):
        if organization is None:
            return UnitTrainingCyclePlan.objects.none()
        for cycle, _label in UnitTrainingCyclePlan.CYCLE_CHOICES:
            UnitTrainingCyclePlan.objects.get_or_create(
                year=year,
                cycle=cycle,
                organization=organization,
            )
        return self.get_rows(year, organization)

    def get_formset(self, year, organization):
        kwargs = {
            "queryset": self.get_rows(year, organization),
            "prefix": "cycles",
        }
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
        return UnitTrainingCyclePlanFormSet(**kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.get_selected_year()
        organization = self.get_selected_organization()
        current_year = timezone.localdate().year
        stored_years = UnitTrainingCyclePlan.objects.values_list("year", flat=True)
        context["selected_year"] = year
        context["selected_organization"] = organization
        context["organizations"] = get_accessible_companies(self.request.user)
        context["year_choices"] = sorted(
            set(range(current_year - 2, current_year + 3)) | set(stored_years),
            reverse=True,
        )
        if organization:
            soldiers = list(
                Person.objects.filter(organization=organization)
                .select_related("rank", "organization")
                .order_by("army_number")
            )
            attach_cycle_plans(soldiers, year)
            attach_majcom(soldiers, year)
            qualifications = {
                item.solider_id: item
                for item in IndividualQual.objects.filter(
                    solider_id__in=[soldier.pk for soldier in soldiers],
                    year=year,
                ).prefetch_related(
                    "courses__course_name__level",
                )
            }
            level_names = (
                "Bde Lvl Cadre", "Div Lvl Cadre", "Army Lvl Course", "Misc Trg"
            )
            sports_by_soldier = {}
            for item in ParticipationInSportsTraining.objects.filter(
                person_id__in=[soldier.pk for soldier in soldiers],
                year=year,
            ).order_by("cycle", "pk"):
                sports_by_soldier.setdefault(item.person_id, {}).setdefault(
                    item.cycle, []
                ).append(item)
            for soldier in soldiers:
                sports = sports_by_soldier.get(soldier.pk, {})
                soldier.sports_cycle_values = []
                for cycle in CYCLES:
                    items = sports.get(cycle, [])
                    values = []
                    for item in items:
                        value = item.name_of_comp
                        if item.significant_achievement:
                            value += f" ({item.significant_achievement})"
                        values.append(value)
                    soldier.sports_cycle_values.append("; ".join(values) or "—")
                qualification = qualifications.get(soldier.pk)
                by_level = {name: {"name": "—", "result": "—"} for name in level_names}
                if qualification:
                    for course in qualification.courses.all():
                        level = course.course_name.level.name
                        if level in by_level:
                            by_level[level] = {
                                "name": course.course_name.name,
                                "result": course.result or "—",
                            }
                soldier.individual_qual_cells = [by_level[name] for name in level_names]
                soldier.individual_qualification = qualification
            context["company_soldiers"] = soldiers
        else:
            plan_org = self.get_plan_organization()
            context["rows"] = self.get_rows(year, plan_org)
        context["edit_mode"] = self.request.GET.get("edit") == "1"
        if not organization:
            plan_org = self.get_plan_organization()
            context["formset"] = kwargs.get("formset") or self.get_formset(
                year, plan_org
            )
        return context

    def post(self, request, *args, **kwargs):
        year = self.get_selected_year()
        organization = self.get_selected_organization()
        plan_org = organization or self.get_plan_organization()
        if request.POST.get("prepare"):
            self.ensure_rows(year, plan_org)
            organization_query = (
                f"&organization={organization.pk}" if organization else ""
            )
            return redirect(
                f"{reverse('training:yearly_plan_list')}?year={year}{organization_query}&edit=1"
            )
        formset = self.get_formset(year, plan_org)
        if formset.is_valid():
            with transaction.atomic():
                formset.save()
            messages.success(request, f"Training plan for {year} saved.")
            organization_query = (
                f"&organization={organization.pk}" if organization else ""
            )
            return redirect(
                f"{reverse('training:yearly_plan_list')}?year={year}{organization_query}"
            )
        return self.render_to_response(self.get_context_data(formset=formset))


class YearlyPlanUpdateView(SoldierYearEditMixin, FormView):

    form_class = SoldierYearlyPlanForm
    template_name = "training/yearly_plan_form.html"

    def get_initial(self):
        plans = {
            plan.cycle: plan.option
            for plan in YearlyPlan.objects.filter(
                solider=self.soldier,
                year=self.year,
            )
        }
        initial = {"year": self.year}

        for field_name, cycle in CYCLE_FIELDS:
            initial[field_name] = plans.get(cycle, "")

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["soldier"] = self.soldier
        context["selected_year"] = self.year
        context["cycle_fields"] = [
            (field_name, context["form"][field_name])
            for field_name, _cycle in CYCLE_FIELDS
        ]
        return context

    def form_valid(self, form):
        year = form.cleaned_data["year"]

        with transaction.atomic():
            for field_name, cycle in CYCLE_FIELDS:
                option = form.cleaned_data.get(field_name)

                if option:
                    YearlyPlan.objects.update_or_create(
                        solider=self.soldier,
                        year=year,
                        cycle=cycle,
                        defaults={"option": option},
                    )
                else:
                    YearlyPlan.objects.filter(
                        solider=self.soldier,
                        year=year,
                        cycle=cycle,
                    ).delete()

        log_change(
            self.request.user,
            self.soldier,
            f"Yearly career plan updated for {year}.",
        )
        messages.success(
            self.request,
            f"Yearly plan for {self.soldier.name} ({year}) saved.",
        )
        return redirect(
            f"{reverse('training:yearly_plan_list')}?year={year}"
        )


class MajComListView(SoldierYearBoardMixin, ListView):

    template_name = "training/majcom_list.html"
    year_source_model = ParticipationInMajCom

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        soldiers, year, context = self.get_board_context(context)
        attach_majcom(soldiers, year)
        context["majcom_fields"] = MAJCOM_FIELDS
        context["stats"] = get_majcom_statistics(
            self.get_base_queryset(),
            year,
        )
        return context


class MajComUpdateView(SoldierYearEditMixin, FormView):

    form_class = ParticipationInMajComForm
    template_name = "training/majcom_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        record = ParticipationInMajCom.objects.filter(
            solider=self.soldier,
            year=self.year,
        ).first()
        kwargs["instance"] = record or ParticipationInMajCom(
            solider=self.soldier,
            year=self.year,
        )
        return kwargs

    def get_initial(self):
        return {"year": self.year}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["soldier"] = self.soldier
        context["selected_year"] = self.year
        context["majcom_fields"] = [
            (field_name, context["form"][field_name])
            for field_name, _label in MAJCOM_FIELDS
        ]
        return context

    def form_valid(self, form):
        year = form.cleaned_data["year"]
        values = {
            field_name: (form.cleaned_data.get(field_name) or "").strip()
            for field_name, _label in MAJCOM_FIELDS
        }
        has_data = any(values.values())

        with transaction.atomic():
            record = form.save(commit=False)
            record.solider = self.soldier
            record.year = year

            if has_data:
                for field_name, value in values.items():
                    setattr(record, field_name, value)
                record.save()
            elif record.pk:
                record.delete()

        log_change(
            self.request.user,
            self.soldier,
            f"Major commitment record updated for {year}.",
        )
        messages.success(
            self.request,
            f"Major commitment for {self.soldier.name} ({year}) saved.",
        )
        return redirect(f"{reverse('training:majcom_list')}?year={year}")


class TrainingHomeView(PortalContextMixin, LoginRequiredMixin, TemplateView):

    template_name = "training/training_home.html"


class SoldierGMatterView(SoldierAccessMixin, TemplateView):
    template_name = "training/soldier_g_matter.html"

    def dispatch(self, request, *args, **kwargs):
        queryset = Person.objects.select_related("rank", "organization")
        allowed_ids = self.get_allowed_organization_ids()
        if allowed_ids is not None:
            queryset = queryset.filter(organization_id__in=allowed_ids)
        self.soldier = get_object_or_404(queryset, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = timezone.localdate().year
        links = (
            ("Yearly Career Plan", "Plan all four annual training cycles.", "training:yearly_plan_edit", True),
            ("Military Courses & Qualifications", "Enter PE, specialist qualifications, course levels, names, and results.", "training:qual_edit", True),
            ("Major Commitments", "Record GP Trg, ST, WT, FI, IHWF, and FF.", "training:majcom_edit", True),
            ("Training & Sports", "Record training participation, sports, cycle, and achievement.", "training:sports_edit", False),
            ("IPFT", "Maintain biannual IPFT attempts and results.", "training:ipft_edit", False),
            ("GP Firing", "Maintain GP firing practices.", "training:gp_firing_edit", False),
            ("SOSN Firing", "Maintain SOSN firing details.", "training:sosn_firing_edit", False),
            ("CAS Trophy", "Maintain CAS Trophy firing records.", "training:cas_trophy_edit", False),
            ("Grenade Firing", "Maintain grenade firing attempts.", "training:grenade_firing_edit", False),
            ("Speed March", "Maintain Speed March attempts and results.", "training:speed_march_edit", False),
            ("Assault Course", "Maintain assault-course times and results.", "training:assault_course_edit", False),
            ("Leave", "Maintain leave plans and approvals.", "training:leave_manage", False),
        )
        context["soldier"] = self.soldier
        context["g_matter_links"] = [
            {
                "title": title,
                "text": text,
                "url": reverse(url_name, args=[self.soldier.pk])
                + (f"?year={year}" if with_year else ""),
            }
            for title, text, url_name, with_year in links
        ]
        return context


class RelatedFormsetUpdateView(SoldierAccessMixin, TemplateView):

    formset_class = None
    formset_prefix = None
    success_url_name = None
    log_message = ""
    formset_title = ""
    section_title = ""

    def dispatch(self, request, *args, **kwargs):
        queryset = Person.objects.select_related("rank", "organization")
        allowed_ids = self.get_allowed_organization_ids()
        if allowed_ids is not None:
            queryset = queryset.filter(organization_id__in=allowed_ids)
        self.soldier = get_object_or_404(queryset, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_formset(self):
        kwargs = {
            "instance": self.soldier,
            "prefix": self.formset_prefix,
        }
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
        return self.formset_class(**kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["soldier"] = self.soldier
        context["formset"] = kwargs.get("formset") or self.get_formset()
        context["formset_title"] = self.formset_title
        context["section_title"] = self.section_title
        context["formset_prefix"] = self.formset_prefix
        context["back_url"] = reverse(self.success_url_name)
        return context

    def post(self, request, *args, **kwargs):
        formset = self.get_formset()
        if formset.is_valid():
            formset.save()
            log_change(request.user, self.soldier, self.log_message)
            messages.success(
                request,
                f"{self.formset_title} for {self.soldier.name} saved.",
            )
            return redirect(self.success_url_name)
        return self.render_to_response(self.get_context_data(formset=formset))


class SportsListView(SoldierYearBoardMixin, ListView):

    template_name = "training/sports_list.html"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("sports_trainings")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        soldiers, context = self.get_filter_context(context)
        today_records = ParticipationInSportsTraining.objects.filter(
            person__in=self.get_base_queryset()
        )
        for soldier in soldiers:
            records = list(soldier.sports_trainings.all())
            soldier.sports_records = records[:3]
            soldier.sports_count = sum(
                1 for row in records if row.type_of_comp == "sports"
            )
            soldier.training_count = sum(
                1 for row in records if row.type_of_comp == "training"
            )

        total = self.get_base_queryset().count()
        recorded = today_records.values("person_id").distinct().count()
        context["stats"] = {
            "total": total,
            "recorded": recorded,
            "sports": today_records.filter(type_of_comp="sports").count(),
            "training": today_records.filter(type_of_comp="training").count(),
        }
        return context


class SportsUpdateView(RelatedFormsetUpdateView):

    template_name = "training/related_form.html"
    formset_class = SportsTrainingFormSet
    formset_prefix = "sports"
    success_url_name = "training:sports_list"
    log_message = "Sports and training participation updated."
    formset_title = "Maj Training and Sports"
    section_title = "Participation in Maj Training and Sports"


class LeaveListView(SoldierYearBoardMixin, ListView):

    template_name = "training/leave_list.html"
    paginate_by = None

    def get_companies(self):
        return get_accessible_companies(self.request.user)

    def get_selected_company(self):
        value = self.request.GET.get("company", "")
        if value.isdigit():
            return self.get_companies().filter(pk=int(value)).first()
        return None

    def get_queryset(self):
        company = self.get_selected_company()
        if company is None:
            return self.get_base_queryset().none()
        organization_ids = collect_descendant_ids(company)
        queryset = self.get_base_queryset().filter(
            organization_id__in=organization_ids
        )
        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(army_number__icontains=search)
            )
        return queryset.prefetch_related(
            "leave_states__leave_type",
            "leave_states__applied_by",
            "leave_states__approved_by",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        soldiers = list(context["soldiers"])
        year = self.get_selected_year()
        companies = list(self.get_companies())
        selected_company = self.get_selected_company()
        today = timezone.localdate()
        scoped_leaves = LeaveState.objects.filter(
            solider__in=self.get_base_queryset()
        )
        current_leaves = scoped_leaves.filter(
            status=LeaveState.STATUS_APPROVED,
            from_date__lte=today,
            to_date__gte=today,
        ).select_related("leave_type")
        current_by_soldier = {
            row.solider_id: row for row in current_leaves
        }
        pending_by_soldier = {}
        for row in scoped_leaves.filter(
            status=LeaveState.STATUS_PENDING
        ).select_related("leave_type", "applied_by", "solider"):
            pending_by_soldier.setdefault(row.solider_id, []).append(row)

        year_leaves = {}
        for row in scoped_leaves.filter(from_date__year=year).select_related(
            "leave_type"
        ):
            if not row.slot:
                continue
            year_leaves.setdefault(row.solider_id, {})[row.slot] = row

        for soldier in soldiers:
            soldier.current_leave = current_by_soldier.get(soldier.pk)
            soldier.pending_leaves = pending_by_soldier.get(soldier.pk, [])
            soldier.leave_count = len(soldier.leave_states.all())
            slots = year_leaves.get(soldier.pk, {})
            soldier.leave_slots = []
            total_days = 0
            for slot_key, slot_label in LeaveState.SLOT_CHOICES:
                record = slots.get(slot_key)
                if record and record.status == LeaveState.STATUS_APPROVED:
                    total_days += record.no_days or 0
                soldier.leave_slots.append({
                    "label": slot_label,
                    "record": record,
                })
            soldier.leave_total_days = total_days

            approved_slots = {
                row.slot: row for row in soldier.leave_states.all()
                if row.status == LeaveState.STATUS_APPROVED
                and row.from_date.year == year
                and row.slot
            }
            p_leave = approved_slots.get(LeaveState.SLOT_P_LEAVE)
            casual_by_number = {}
            for row in approved_slots.values():
                number = LeaveState.casual_slot_number(row.slot)
                if number:
                    casual_by_number[number] = row
            soldier.p_leave = p_leave
            soldier.casual_by_number = casual_by_number
            soldier.p_leave_days = p_leave.no_days if p_leave else 0
            soldier.c_leave_days = sum(
                row.no_days or 0 for row in approved_slots.values()
                if LeaveState.is_casual_slot(row.slot)
            )
            soldier.combined_leave_days = soldier.p_leave_days + soldier.c_leave_days
            soldier.platoon_name = (
                "Coy HQ" if selected_company and soldier.organization_id == selected_company.pk
                else soldier.organization.organization_name
            )

        max_casual = 1
        for soldier in soldiers:
            if soldier.casual_by_number:
                max_casual = max(max_casual, max(soldier.casual_by_number))
        casual_column_numbers = list(range(1, max_casual + 1))
        for soldier in soldiers:
            soldier.casual_columns = [
                soldier.casual_by_number.get(number) for number in casual_column_numbers
            ]

        company_descendants = descendant_ids_by_organization(companies)
        summary_rows = []
        for company in companies:
            person_ids = list(self.get_base_queryset().filter(
                organization_id__in=company_descendants.get(company.pk, {company.pk})
            ).values_list("pk", flat=True))
            completed = LeaveState.objects.filter(
                solider_id__in=person_ids,
                slot=LeaveState.SLOT_P_LEAVE,
                status=LeaveState.STATUS_APPROVED,
                from_date__year=year,
            ).values("solider_id").distinct().count()
            summary_rows.append({
                "company": company,
                "strength": len(person_ids),
                "completed": completed,
                "remaining": max(len(person_ids) - completed, 0),
            })

        platoon_rows = []
        if selected_company:
            children = list(selected_company.child_organizations.all().order_by("organization_name"))
            platoon_descendants = descendant_ids_by_organization(children)
            for platoon in children:
                platoon_ids = list(self.get_base_queryset().filter(
                    organization_id__in=platoon_descendants.get(platoon.pk, {platoon.pk})
                ).values_list("pk", flat=True))
                if platoon.organization_name == "Coy HQ":
                    platoon_ids += list(self.get_base_queryset().filter(
                        organization=selected_company
                    ).values_list("pk", flat=True))
                platoon_ids = list(set(platoon_ids))
                completed = LeaveState.objects.filter(
                    solider_id__in=platoon_ids,
                    slot=LeaveState.SLOT_P_LEAVE,
                    status=LeaveState.STATUS_APPROVED,
                    from_date__year=year,
                ).values("solider_id").distinct().count()
                platoon_rows.append({
                    "platoon": platoon,
                    "strength": len(platoon_ids),
                    "completed": completed,
                    "remaining": max(len(platoon_ids) - completed, 0),
                })

        context.update({
            "selected_year": year,
            "year_choices": self.get_year_choices(),
            "search_query": self.request.GET.get("q", "").strip(),
            "companies": companies,
            "selected_company": selected_company,
            "company_summary_rows": summary_rows,
            "platoon_summary_rows": platoon_rows,
            "company_summary_total": {
                "strength": sum(row["strength"] for row in summary_rows),
                "completed": sum(row["completed"] for row in summary_rows),
                "remaining": sum(row["remaining"] for row in summary_rows),
            },
            "platoon_summary_total": {
                "strength": sum(row["strength"] for row in platoon_rows),
                "completed": sum(row["completed"] for row in platoon_rows),
                "remaining": sum(row["remaining"] for row in platoon_rows),
            },
            "casual_column_numbers": casual_column_numbers,
            "casual_colspan": len(casual_column_numbers) * 2,
            "individual_colspan": 12 + len(casual_column_numbers) * 2,
        })
        total = self.get_base_queryset().count()
        on_leave = current_leaves.values("solider_id").distinct().count()
        pending = scoped_leaves.filter(
            status=LeaveState.STATUS_PENDING
        )
        if selected_company:
            pending = pending.filter(
                solider__organization_id__in=collect_descendant_ids(selected_company)
            )
        context["pending_applications"] = pending.select_related(
            "solider",
            "solider__rank",
            "solider__organization",
            "leave_type",
            "applied_by",
        ).order_by("from_date", "pk")
        context["can_apply"] = self.request.user.can_apply_leave
        context["can_approve"] = self.request.user.can_approve_leave
        context["stats"] = {
            "total": total,
            "on_leave": on_leave,
            "pending": pending.count(),
            "available": max(total - on_leave, 0),
        }
        return context


class LeaveManageView(SoldierAccessMixin, FormView):

    form_class = LeaveApplyForm
    template_name = "training/leave_manage.html"

    def dispatch(self, request, *args, **kwargs):
        queryset = Person.objects.select_related(
            "rank",
            "organization",
            "organization__parent_organization",
        )
        allowed_ids = self.get_allowed_organization_ids()
        if allowed_ids is not None:
            queryset = queryset.filter(organization_id__in=allowed_ids)
        self.soldier = get_object_or_404(queryset, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop("organization_queryset", None)
        kwargs["soldier"] = self.soldier
        kwargs["applicant"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["soldier"] = self.soldier
        context["leave_records"] = self.soldier.leave_states.select_related(
            "leave_type",
            "applied_by",
            "approved_by",
        )
        context["can_apply"] = self.request.user.can_apply_leave
        context["can_approve"] = self.request.user.can_approve_leave
        context["leave_board_url"] = leave_board_url(self.soldier)
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.can_apply_leave:
            messages.error(request, "You do not have permission to apply for leave.")
            return redirect("training:leave_manage", pk=self.soldier.pk)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        leave = form.save(commit=False)
        leave.solider = self.soldier
        leave.applied_by = self.request.user
        leave.status = LeaveState.STATUS_PENDING
        leave.approved_by = None
        leave.total_no_days = 0
        leave.save()
        log_change(
            self.request.user,
            self.soldier,
            f"Leave applied: {leave.leave_type} "
            f"({leave.from_date} to {leave.to_date}).",
        )
        messages.success(
            self.request,
            f"Leave request for {self.soldier.name} submitted. "
            "A company officer or the CO can approve it on Leave State.",
        )
        if is_privilege_or_casual_slot(leave.slot):
            return redirect(leave_board_url(self.soldier, leave.from_date.year))
        return redirect("training:leave_manage", pk=self.soldier.pk)


class LeaveDecisionView(SoldierAccessMixin, View):

    def post(self, request, *args, **kwargs):
        if not request.user.can_approve_leave:
            messages.error(request, "You do not have permission to approve or reject leave.")
            return redirect("training:leave_list")

        queryset = LeaveState.objects.select_related(
            "solider",
            "solider__organization",
            "solider__organization__parent_organization",
            "leave_type",
        )
        allowed_ids = self.get_allowed_organization_ids()
        if allowed_ids is not None:
            queryset = queryset.filter(
                solider__organization_id__in=allowed_ids
            )

        leave = get_object_or_404(queryset, pk=self.kwargs["pk"])
        action = request.POST.get("action", "approve")

        if leave.status != LeaveState.STATUS_PENDING:
            messages.error(request, "This leave request has already been decided.")
            return redirect("training:leave_manage", pk=leave.solider_id)

        with transaction.atomic():
            leave.decided_at = timezone.now()
            if action == "reject":
                leave.status = LeaveState.STATUS_REJECTED
                leave.approved_by = None
                leave.remarks = (
                    request.POST.get("remarks", "").strip() or leave.remarks
                )
                leave.save()
                message = (
                    f"Leave rejected for {leave.solider.name} "
                    f"({leave.from_date} to {leave.to_date})."
                )
            else:
                leave.status = LeaveState.STATUS_APPROVED
                leave.approved_by = request.user
                leave.save()
                leave.refresh_type_totals()
                message = (
                    f"Leave approved for {leave.solider.name} "
                    f"({leave.from_date} to {leave.to_date})."
                )

        log_change(request.user, leave.solider, message)
        messages.success(request, message)
        fallback = reverse("training:leave_manage", kwargs={"pk": leave.solider_id})
        if is_privilege_or_casual_slot(leave.slot):
            fallback = leave_board_url(leave.solider, leave.from_date.year)
        return redirect(safe_redirect_target(request, fallback))


class QualListView(SoldierYearBoardMixin, ListView):

    template_name = "training/qual_list.html"
    year_source_model = IndividualQual

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            "qualifications__courses__course_name__level",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        soldiers, year, context = self.get_board_context(context)
        quals = IndividualQual.objects.filter(
            solider__in=self.get_base_queryset(),
            year=year,
        )

        for soldier in soldiers:
            records = [
                item for item in soldier.qualifications.all() if item.year == year
            ]
            header = records[0] if records else None
            courses = list(header.courses.all()) if header else []
            soldier.qualification = header
            soldier.qual_count = len(courses)
            soldier.level_count = len({
                row.course_name.level_id for row in courses
            })
            soldier.next_promo = bool(
                header and header.qual_for_next_promotion
            )
            soldier.pe = header.pe if header else ""
            soldier.latest_course = courses[0] if courses else None

        total = self.get_base_queryset().count()
        recorded = quals.count()
        context["stats"] = {
            "total": total,
            "recorded": recorded,
            "qualifications": IndividualQualCourse.objects.filter(
                qualification__solider__in=self.get_base_queryset(),
                qualification__year=year,
            ).count(),
            "next_promo": quals.filter(
                qual_for_next_promotion=True
            ).count(),
        }
        return context


class QualUpdateView(SoldierAccessMixin, TemplateView):

    template_name = "training/qual_form.html"

    def dispatch(self, request, *args, **kwargs):
        queryset = Person.objects.select_related("rank", "organization")
        allowed_ids = self.get_allowed_organization_ids()
        if allowed_ids is not None:
            queryset = queryset.filter(organization_id__in=allowed_ids)
        self.soldier = get_object_or_404(queryset, pk=self.kwargs["pk"])
        year = self.request.GET.get("year") or self.request.POST.get("year", "")
        year = str(year).strip()
        current_year = timezone.localdate().year
        self.year = int(year) if year.isdigit() and 1900 <= int(year) <= 2100 else current_year
        self.qualification = IndividualQual.objects.filter(
            solider=self.soldier,
            year=self.year,
        ).first()
        if self.qualification is None:
            self.qualification = IndividualQual(
                solider=self.soldier,
                year=self.year,
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form(self):
        kwargs = {"instance": self.qualification}
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
        return IndividualQualForm(**kwargs)

    def get_formset(self, qualification=None):
        kwargs = {
            "instance": qualification or self.qualification,
            "prefix": "courses",
        }
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
        return QualCourseFormSetFactory(**kwargs)

    def get_courses_by_level(self):
        data = {}
        for course in IndividualCourseName.objects.select_related("level"):
            data.setdefault(str(course.level_id), []).append(
                {"id": course.pk, "name": course.name}
            )
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["soldier"] = self.soldier
        context["selected_year"] = self.year
        context["form"] = kwargs.get("form") or self.get_form()
        context["formset"] = kwargs.get("formset") or self.get_formset()
        context["courses_by_level"] = self.get_courses_by_level()
        context["back_url"] = reverse("training:qual_list")
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        formset = self.get_formset()
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                qualification = form.save(commit=False)
                qualification.solider = self.soldier
                qualification.save()
                formset.instance = qualification
                formset.save()
            log_change(
                request.user,
                self.soldier,
                "Individual qualifications updated.",
            )
            messages.success(
                request,
                f"Qualifications for {self.soldier.name} saved.",
            )
            return redirect(f"{reverse('training:qual_list')}?year={self.year}")
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )


class IPFTListView(SoldierAccessMixin, TemplateView):

    template_name = "training/ipft_list.html"

    def get_selected_year(self):
        value = self.request.GET.get("year", "").strip()
        if value.isdigit() and 1900 <= int(value) <= 2100:
            return int(value)
        return timezone.localdate().year

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.get_selected_year()
        test_type = self.request.GET.get("type", IPFT.TYPE_FIRST_BIANNUAL)
        if test_type not in dict(IPFT.TYPE_CHOICES):
            test_type = IPFT.TYPE_FIRST_BIANNUAL
        allowed_organizations = self.get_allowed_organizations()
        selected_id = self.request.GET.get("organization", "").strip()
        selected_organization = None
        if selected_id.isdigit():
            selected_organization = allowed_organizations.filter(
                pk=int(selected_id)
            ).first()

        start_of_year = date(year, 1, 1)
        end_of_year = date(year, 12, 31)
        summary_rows = []
        total = {key: 0 for key in ("posted", "exempted", "eligible", "attended", "not_attended", "passed", "failed")}

        def build_summary_row(label, soldier_ids):
            soldier_ids = set(soldier_ids)
            exempted_ids = set(
                MedicalCategory.objects.filter(
                    person_id__in=soldier_ids,
                    from_date__lte=end_of_year,
                ).filter(
                    Q(to_date__isnull=True) | Q(to_date__gte=start_of_year)
                ).values_list("person_id", flat=True)
            )
            eligible_ids = soldier_ids - exempted_ids
            records = IPFT.objects.filter(
                solider_id__in=eligible_ids,
                type_of_ipft=test_type,
                date__year=year,
            )
            attended_ids = set(records.values_list("solider_id", flat=True))
            passed_ids = set(
                records.filter(result=IPFT.RESULT_PASS).values_list("solider_id", flat=True)
            )
            failed_ids = attended_ids - passed_ids
            return {
                "label": label,
                "posted": len(soldier_ids),
                "exempted": len(exempted_ids),
                "eligible": len(eligible_ids),
                "attended": len(attended_ids),
                "not_attended": max(len(eligible_ids) - len(attended_ids), 0),
                "passed": len(passed_ids),
                "failed": len(failed_ids),
                "percentage": round(len(passed_ids) * 100 / len(attended_ids), 1) if attended_ids else 0,
            }

        if selected_organization:
            category_rows = (
                ("Offr", Rank.CATEGORY_OFFICER),
                ("JCO", Rank.CATEGORY_JCO),
                ("OR", Rank.CATEGORY_OR),
            )
            for label, category in category_rows:
                soldier_ids = Person.objects.filter(
                    organization=selected_organization,
                    rank__category=category,
                ).values_list("pk", flat=True)
                summary_rows.append(build_summary_row(label, soldier_ids))

            company_soldiers = list(
                Person.objects.filter(organization=selected_organization)
                .select_related("rank", "organization")
                .order_by("rank__category", "army_number")
            )
            company_ids = [soldier.pk for soldier in company_soldiers]
            active_exempted = set(
                MedicalCategory.objects.filter(
                    person_id__in=company_ids,
                    from_date__lte=end_of_year,
                ).filter(
                    Q(to_date__isnull=True) | Q(to_date__gte=start_of_year)
                ).values_list("person_id", flat=True)
            )
            latest_records = {}
            for record in IPFT.objects.filter(
                solider_id__in=company_ids,
                type_of_ipft=test_type,
                date__year=year,
            ).order_by("solider_id", "-date", "-pk"):
                latest_records.setdefault(record.solider_id, record)
            for soldier in company_soldiers:
                soldier.summary_ipft = latest_records.get(soldier.pk)
                soldier.ipft_exempted = soldier.pk in active_exempted
            context["individual_soldiers"] = company_soldiers
        else:
            for organization in allowed_organizations:
                soldier_ids = Person.objects.filter(
                    organization=organization
                ).values_list("pk", flat=True)
                summary_rows.append(build_summary_row(organization, soldier_ids))

        for row in summary_rows:
            for key in total:
                total[key] += row[key]

        total["percentage"] = round(total["passed"] * 100 / total["attended"], 1) if total["attended"] else 0
        current_year = timezone.localdate().year
        context.update({
            "summary_rows": summary_rows,
            "summary_total": total,
            "organizations": self.get_allowed_organizations(),
            "organization_filter": selected_id,
            "selected_organization": selected_organization,
            "selected_year": year,
            "year_choices": range(current_year + 1, current_year - 3, -1),
            "selected_type": test_type,
            "type_choices": IPFT.TYPE_CHOICES,
        })
        return context


class IPFTUpdateView(RelatedFormsetUpdateView):

    template_name = "training/related_form.html"
    formset_class = IPFTFormSet
    formset_prefix = "ipft"
    success_url_name = "training:ipft_list"
    log_message = "IPFT records updated."
    formset_title = "IPFT"
    section_title = "IPFT"


class RETHomeView(SoldierAccessMixin, TemplateView):

    template_name = "training/ret_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year_value = self.request.GET.get("year", "").strip()
        year = int(year_value) if year_value.isdigit() else timezone.localdate().year
        allowed_organizations = self.get_allowed_organizations()
        selected_id = self.request.GET.get("organization", "").strip()
        selected_organization = (
            allowed_organizations.filter(pk=int(selected_id)).first()
            if selected_id.isdigit() else None
        )
        start_of_year = date(year, 1, 1)
        end_of_year = date(year, 12, 31)

        def firing_sets(soldier_ids, grenade=False):
            soldier_ids = set(soldier_ids)
            if grenade:
                records = GrenadeFiring.objects.filter(
                    solider_id__in=soldier_ids,
                    date_of_firing__year=year,
                )
                attended = set(records.values_list("solider_id", flat=True))
                passed = set(records.filter(result=FIRING_RESULT_PASS).values_list("solider_id", flat=True))
                return attended, passed
            attended, passed = set(), set()
            for model in (GPFiring, SOSNFiring, CASTrophy):
                records = model.objects.filter(
                    solider_id__in=soldier_ids,
                    date_of_firing__year=year,
                )
                attended.update(records.values_list("solider_id", flat=True))
                passed.update(records.filter(result=FIRING_RESULT_PASS).values_list("solider_id", flat=True))
            return attended, passed

        def summary_row(label, soldier_ids, grenade=False):
            soldier_ids = set(soldier_ids)
            exempted = set(
                MedicalCategory.objects.filter(
                    person_id__in=soldier_ids,
                    from_date__lte=end_of_year,
                ).filter(Q(to_date__isnull=True) | Q(to_date__gte=start_of_year))
                .values_list("person_id", flat=True)
            )
            eligible = soldier_ids - exempted
            attended, passed = firing_sets(eligible, grenade=grenade)
            failed = attended - passed
            return {
                "label": label, "posted": len(soldier_ids),
                "exempted": len(exempted), "eligible": len(eligible),
                "attended": len(attended),
                "not_attended": max(len(eligible) - len(attended), 0),
                "passed": len(passed), "failed": len(failed),
                "percentage": (
                    round(len(attended) * 100 / len(eligible), 1)
                    if grenade and eligible else
                    (round(len(passed) * 100 / len(attended), 1) if attended else 0)
                ),
            }

        groups = []
        if selected_organization:
            for label, category in (("Offr", Rank.CATEGORY_OFFICER), ("JCO", Rank.CATEGORY_JCO), ("OR", Rank.CATEGORY_OR)):
                ids = Person.objects.filter(organization=selected_organization, rank__category=category).values_list("pk", flat=True)
                groups.append((label, ids))
        else:
            for organization in allowed_organizations:
                ids = Person.objects.filter(organization=organization).values_list("pk", flat=True)
                groups.append((organization, ids))

        classification_rows = [summary_row(label, ids) for label, ids in groups]
        grenade_rows = [summary_row(label, ids, grenade=True) for label, ids in groups]

        def totals(rows, attendance_percentage=False):
            keys = ("posted", "exempted", "eligible", "attended", "not_attended", "passed", "failed")
            result = {key: sum(row[key] for row in rows) for key in keys}
            if attendance_percentage:
                result["percentage"] = round(result["attended"] * 100 / result["eligible"], 1) if result["eligible"] else 0
            else:
                result["percentage"] = round(result["passed"] * 100 / result["attended"], 1) if result["attended"] else 0
            return result

        if selected_organization:
            soldiers = list(Person.objects.filter(organization=selected_organization).select_related("rank").order_by("rank__category", "army_number"))
            for soldier in soldiers:
                classification = []
                for model in (GPFiring, SOSNFiring, CASTrophy):
                    classification.extend(model.objects.filter(solider=soldier, date_of_firing__year=year))
                classification.sort(key=lambda item: item.date_of_firing, reverse=True)
                grenade = GrenadeFiring.objects.filter(solider=soldier, date_of_firing__year=year).order_by("-date_of_firing", "-pk").first()
                soldier.latest_classification = classification[0] if classification else None
                soldier.latest_grenade = grenade
            context["individual_soldiers"] = soldiers

        current_year = timezone.localdate().year
        context.update({
            "section_title": "RET State",
            "selected_year": year,
            "year_choices": range(current_year + 1, current_year - 3, -1),
            "organizations": allowed_organizations,
            "organization_filter": selected_id,
            "selected_organization": selected_organization,
            "classification_rows": classification_rows,
            "classification_total": totals(classification_rows),
            "grenade_rows": grenade_rows,
            "grenade_total": totals(grenade_rows, attendance_percentage=True),
        })
        context["section_blurb"] = (
            "Choose a firing board to record results for soldiers in your companies."
        )
        context["section_eyebrow"] = "Training // RET"
        context["back_url"] = reverse("training:training_home")
        context["back_label"] = "Back to Training"
        return context


class RETFiringListView(SoldierYearBoardMixin, ListView):

    template_name = "training/ret_firing_list.html"
    firing_model = None
    related_name = None
    edit_url_name = None
    section_title = ""
    section_blurb = ""
    columns = ()
    date_attr = "date_of_firing"
    count_group_attr = None
    back_url_name = "training:ret_list"
    back_label = "Back to RET State"

    def get_queryset(self):
        return super().get_queryset().prefetch_related(self.related_name)

    def _cell(self, record, column):
        if record is None:
            return {"text": "—", "badge": ""}
        attr = column["attr"]
        value = getattr(record, attr)
        if column.get("choice"):
            value = getattr(record, f"get_{attr}_display")()
        elif attr in {self.date_attr, "date_of_firing", "date_of_event"}:
            value = value.strftime("%d %b %Y") if value else ""
        if column.get("result"):
            badge = ""
            if value == FIRING_RESULT_PASS:
                badge = "badge-approved"
            elif value == FIRING_RESULT_FAIL:
                badge = "badge-rejected"
            return {"text": value or "—", "badge": badge}
        return {"text": value or "—", "badge": ""}

    def _appearance_label(self, rows):
        if not rows:
            return "0"
        group_attr = self.count_group_attr
        if not group_attr:
            return str(len(rows))
        grouped = {}
        for row in rows:
            key = getattr(row, f"get_{group_attr}_display")()
            grouped[key] = grouped.get(key, 0) + 1
        return " · ".join(
            f"{name.split(' - ')[-1]}: {count}"
            for name, count in grouped.items()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        soldiers, context = self.get_filter_context(context)
        records = self.firing_model.objects.filter(
            solider__in=self.get_base_queryset()
        )

        for soldier in soldiers:
            rows = list(getattr(soldier, self.related_name).all())
            latest = rows[0] if rows else None
            soldier.firing_count = len(rows)
            soldier.appearance_label = self._appearance_label(rows)
            soldier.latest_cells = [
                self._cell(latest, column) for column in self.columns
            ]

        total = self.get_base_queryset().count()
        context["stats"] = {
            "total": total,
            "recorded": records.values("solider_id").distinct().count(),
            "passed": records.filter(result=FIRING_RESULT_PASS).count(),
            "failed": records.filter(result=FIRING_RESULT_FAIL).count(),
        }
        context["section_title"] = self.section_title
        context["section_blurb"] = self.section_blurb
        context["edit_url_name"] = self.edit_url_name
        context["column_labels"] = [column["label"] for column in self.columns]
        context["back_url"] = reverse(self.back_url_name)
        context["back_label"] = self.back_label
        return context


class GPFiringListView(RETFiringListView):

    firing_model = GPFiring
    related_name = "gp_firings"
    edit_url_name = "training:gp_firing_edit"
    section_title = "GP Firing"
    section_blurb = "GP firing at 100m and 300m by practice attempt."
    count_group_attr = "type_of_gp"
    columns = (
        {"label": "Type", "attr": "type_of_gp", "choice": True},
        {"label": "Attempt", "attr": "attempt", "choice": True},
        {"label": "Date", "attr": "date_of_firing"},
        {"label": "Result", "attr": "result", "result": True},
    )


class SOSNFiringListView(RETFiringListView):

    firing_model = SOSNFiring
    related_name = "sosn_firings"
    edit_url_name = "training:sosn_firing_edit"
    section_title = "SOSN Firing"
    section_blurb = "SOSN firing grouping, hits, total marks, and result."
    count_group_attr = "type_of_gp"
    columns = (
        {"label": "Type", "attr": "type_of_gp", "choice": True},
        {"label": "Attempt", "attr": "attempt", "choice": True},
        {"label": "Date", "attr": "date_of_firing"},
        {"label": "GP", "attr": "gp"},
        {"label": "Hit", "attr": "hit"},
        {"label": "Total Marks", "attr": "total_marks"},
        {"label": "Result", "attr": "result", "result": True},
    )


class CASTrophyListView(RETFiringListView):

    firing_model = CASTrophy
    related_name = "cas_trophies"
    edit_url_name = "training:cas_trophy_edit"
    section_title = "CAS Trophy Firing"
    section_blurb = "CAS trophy firing grouping, hits, total marks, and result."
    columns = (
        {"label": "Date", "attr": "date_of_firing"},
        {"label": "GP", "attr": "gp"},
        {"label": "Hit", "attr": "hit"},
        {"label": "Total Marks", "attr": "total_marks"},
        {"label": "Result", "attr": "result", "result": True},
    )


class GrenadeFiringListView(RETFiringListView):

    firing_model = GrenadeFiring
    related_name = "grenade_firings"
    edit_url_name = "training:grenade_firing_edit"
    section_title = "Grenade Firing"
    section_blurb = "Grenade firing by practice attempt and result."
    columns = (
        {"label": "Attempt", "attr": "attempt", "choice": True},
        {"label": "Date", "attr": "date_of_firing"},
        {"label": "Result", "attr": "result", "result": True},
    )


class GPFiringUpdateView(RelatedFormsetUpdateView):

    template_name = "training/related_form.html"
    formset_class = GPFiringFormSet
    formset_prefix = "gp_firing"
    success_url_name = "training:gp_firing_list"
    log_message = "GP firing records updated."
    formset_title = "GP Firing"
    section_title = "RET // GP Firing"


class SOSNFiringUpdateView(RelatedFormsetUpdateView):

    template_name = "training/related_form.html"
    formset_class = SOSNFiringFormSet
    formset_prefix = "sosn_firing"
    success_url_name = "training:sosn_firing_list"
    log_message = "SOSN firing records updated."
    formset_title = "SOSN Firing"
    section_title = "RET // SOSN Firing"


class CASTrophyUpdateView(RelatedFormsetUpdateView):

    template_name = "training/related_form.html"
    formset_class = CASTrophyFormSet
    formset_prefix = "cas_trophy"
    success_url_name = "training:cas_trophy_list"
    log_message = "CAS trophy firing records updated."
    formset_title = "CAS Trophy Firing"
    section_title = "RET // CAS Trophy Firing"


class GrenadeFiringUpdateView(RelatedFormsetUpdateView):

    template_name = "training/related_form.html"
    formset_class = GrenadeFiringFormSet
    formset_prefix = "grenade_firing"
    success_url_name = "training:grenade_firing_list"
    log_message = "Grenade firing records updated."
    formset_title = "Grenade Firing"
    section_title = "RET // Grenade Firing"


MARCH_COURSE_CARDS = [
    {
        "title": "Speed March",
        "text": "Record speed march practices, dates, and results.",
        "url_name": "training:speed_march_list",
    },
    {
        "title": "Assault Course",
        "text": "Record assault course practices, time, and results.",
        "url_name": "training:assault_course_list",
    },
]


class MarchCourseHomeView(PortalContextMixin, LoginRequiredMixin, TemplateView):

    template_name = "training/ret_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cards = []
        for item in MARCH_COURSE_CARDS:
            cards.append({
                **item,
                "url": reverse(item["url_name"]),
            })
        context["ret_cards"] = cards
        context["section_title"] = "Speed March & Assault Course"
        context["section_blurb"] = (
            "Record speed march and assault course practices for soldiers "
            "in your companies."
        )
        context["section_eyebrow"] = "Training // March & Assault"
        context["back_url"] = reverse("training:training_home")
        context["back_label"] = "Back to Training"
        return context


class SpeedMarchListView(SoldierAccessMixin, TemplateView):

    template_name = "training/speed_march_list.html"
    summary_attempts = ("Prac-1", "Prac-2", "Prac-3", "Prac-4")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year_value = self.request.GET.get("year", "").strip()
        year = int(year_value) if year_value.isdigit() else timezone.localdate().year
        allowed_organizations = self.get_allowed_organizations()
        selected_id = self.request.GET.get("organization", "").strip()
        selected_organization = (
            allowed_organizations.filter(pk=int(selected_id)).first()
            if selected_id.isdigit() else None
        )
        start_of_year, end_of_year = date(year, 1, 1), date(year, 12, 31)

        def summary_row(label, soldier_ids):
            soldier_ids = set(soldier_ids)
            exempted = set(
                MedicalCategory.objects.filter(
                    person_id__in=soldier_ids, from_date__lte=end_of_year,
                ).filter(Q(to_date__isnull=True) | Q(to_date__gte=start_of_year))
                .values_list("person_id", flat=True)
            )
            eligible = soldier_ids - exempted
            records = SpeedMarch.objects.filter(
                solider_id__in=eligible, date_of_event__year=year,
            )
            attended = set(records.values_list("solider_id", flat=True))
            attempts = [
                records.filter(attempt=attempt).values("solider_id").distinct().count()
                for attempt in self.summary_attempts
            ]
            return {
                "label": label, "posted": len(soldier_ids),
                "exempted": len(exempted), "eligible": len(eligible),
                "attended": len(attended),
                "not_attended": max(len(eligible) - len(attended), 0),
                "attempts": attempts,
            }

        groups = []
        if selected_organization:
            for label, category in (("Offr", Rank.CATEGORY_OFFICER), ("JCO", Rank.CATEGORY_JCO), ("OR", Rank.CATEGORY_OR)):
                ids = Person.objects.filter(organization=selected_organization, rank__category=category).values_list("pk", flat=True)
                groups.append((label, ids))
        else:
            for organization in allowed_organizations:
                ids = Person.objects.filter(organization=organization).values_list("pk", flat=True)
                groups.append((organization, ids))
        rows = [summary_row(label, ids) for label, ids in groups]
        total = {
            key: sum(row[key] for row in rows)
            for key in ("posted", "exempted", "eligible", "attended", "not_attended")
        }
        total["attempts"] = [sum(row["attempts"][index] for row in rows) for index in range(4)]

        if selected_organization:
            soldiers = list(Person.objects.filter(organization=selected_organization).select_related("rank").order_by("rank__category", "army_number"))
            records_by_soldier = {}
            for record in SpeedMarch.objects.filter(
                solider_id__in=[soldier.pk for soldier in soldiers],
                date_of_event__year=year,
                attempt__in=self.summary_attempts,
            ).order_by("solider_id", "attempt", "-date_of_event", "-pk"):
                records_by_soldier.setdefault(record.solider_id, {}).setdefault(record.attempt, record)
            for soldier in soldiers:
                mapping = records_by_soldier.get(soldier.pk, {})
                soldier.speed_attempts = [mapping.get(attempt) for attempt in self.summary_attempts]
            context["individual_soldiers"] = soldiers

        current_year = timezone.localdate().year
        context.update({
            "rows": rows, "total": total,
            "selected_year": year,
            "year_choices": range(current_year + 1, current_year - 3, -1),
            "organizations": allowed_organizations,
            "organization_filter": selected_id,
            "selected_organization": selected_organization,
        })
        return context


class AssaultCourseListView(SoldierAccessMixin, TemplateView):

    template_name = "training/assault_course_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year_value = self.request.GET.get("year", "").strip()
        year = int(year_value) if year_value.isdigit() else timezone.localdate().year
        allowed_organizations = self.get_allowed_organizations()
        selected_id = self.request.GET.get("organization", "").strip()
        selected_organization = (
            allowed_organizations.filter(pk=int(selected_id)).first()
            if selected_id.isdigit() else None
        )
        start_of_year, end_of_year = date(year, 1, 1), date(year, 12, 31)

        def summary_row(label, soldier_ids):
            soldier_ids = set(soldier_ids)
            exempted = set(
                MedicalCategory.objects.filter(
                    person_id__in=soldier_ids, from_date__lte=end_of_year,
                ).filter(Q(to_date__isnull=True) | Q(to_date__gte=start_of_year))
                .values_list("person_id", flat=True)
            )
            eligible = soldier_ids - exempted
            attended = set(
                AssaultCourse.objects.filter(
                    solider_id__in=eligible, date_of_event__year=year,
                ).values_list("solider_id", flat=True)
            )
            return {
                "label": label, "posted": len(soldier_ids),
                "exempted": len(exempted), "eligible": len(eligible),
                "attended": len(attended),
                "not_attended": max(len(eligible) - len(attended), 0),
            }

        groups = []
        if selected_organization:
            for label, category in (("Offr", Rank.CATEGORY_OFFICER), ("JCO", Rank.CATEGORY_JCO), ("OR", Rank.CATEGORY_OR)):
                ids = Person.objects.filter(organization=selected_organization, rank__category=category).values_list("pk", flat=True)
                groups.append((label, ids))
        else:
            for organization in allowed_organizations:
                ids = Person.objects.filter(organization=organization).values_list("pk", flat=True)
                groups.append((organization, ids))
        rows = [summary_row(label, ids) for label, ids in groups]
        total = {
            key: sum(row[key] for row in rows)
            for key in ("posted", "exempted", "eligible", "attended", "not_attended")
        }

        if selected_organization:
            soldiers = list(Person.objects.filter(organization=selected_organization).select_related("rank").order_by("rank__category", "army_number"))
            latest = {}
            for record in AssaultCourse.objects.filter(
                solider_id__in=[soldier.pk for soldier in soldiers],
                date_of_event__year=year,
            ).order_by("solider_id", "-date_of_event", "-pk"):
                latest.setdefault(record.solider_id, record)
            for soldier in soldiers:
                soldier.latest_assault_course = latest.get(soldier.pk)
            context["individual_soldiers"] = soldiers

        current_year = timezone.localdate().year
        context.update({
            "rows": rows, "total": total, "selected_year": year,
            "year_choices": range(current_year + 1, current_year - 3, -1),
            "organizations": allowed_organizations,
            "organization_filter": selected_id,
            "selected_organization": selected_organization,
        })
        return context


class SpeedMarchUpdateView(RelatedFormsetUpdateView):

    template_name = "training/related_form.html"
    formset_class = SpeedMarchFormSet
    formset_prefix = "speed_march"
    success_url_name = "training:speed_march_list"
    log_message = "Speed march records updated."
    formset_title = "Speed March"
    section_title = "March // Speed March"


class AssaultCourseUpdateView(RelatedFormsetUpdateView):

    template_name = "training/related_form.html"
    formset_class = AssaultCourseFormSet
    formset_prefix = "assault_course"
    success_url_name = "training:assault_course_list"
    log_message = "Assault course records updated."
    formset_title = "Assault Course"
    section_title = "March // Assault Course"

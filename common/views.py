from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from authentication.views import (
    AdminRequiredMixin,
    CoRequiredMixin,
    PortalContextMixin,
)

from .activity import log_addition, log_change, log_deletion
from .forms import (
    AnnualPerformanceReportFormSet,
    AppointmentHistoryFormSet,
    CivilEducationFormSet,
    EducationLevelForm,
    EREOrganizationForm,
    FamilyFormSet,
    MedicalCategoryFormSet,
    MobileNumberFormSet,
    OrganizationForm,
    PersonForm,
    RankHistoryFormSet,
    RankForm,
)
from .models import CivilEducationLevel, EREOrganization, Organization, Person, Rank
from .pdf import build_soldier_pdf
from .scoping import get_accessible_organization_ids, get_accessible_organizations
from training.forms import (
    AssaultCourseFormSet,
    CASTrophyFormSet,
    GPFiringFormSet,
    GrenadeFiringFormSet,
    IPFTFormSet,
    RETStateFormSet,
    SOSNFiringFormSet,
    SoldierMajComInlineFormSet,
    SoldierQualificationInlineFormSet,
    SoldierYearlyPlanInlineFormSet,
    SpeedMarchFormSet,
    SportsTrainingFormSet,
)


class AdminPortalMixin(PortalContextMixin, AdminRequiredMixin):
    pass


class SoldierAccessMixin(PortalContextMixin, LoginRequiredMixin):
    def get_allowed_organizations(self):
        return get_accessible_organizations(self.request.user)

    def get_allowed_organization_ids(self):
        return get_accessible_organization_ids(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization_queryset"] = self.get_allowed_organizations()
        return kwargs


class SoldierRecordMixin(SoldierAccessMixin):
    def get_queryset(self):
        queryset = Person.objects.on_strength().select_related(
            "rank",
            "organization",
        ).prefetch_related(
            "service_histories__organization",
            "service_histories__rank",
            "civil_educations__level",
            "medical_categories",
            "annual_performance_reports",
            "appointment_histories__organization",
            "mobile_numbers",
            "family_members",
            "yearly_plans",
            "major_competitions",
            "qualifications__courses__course_name__level",
            "leave_states__leave_type",
            "sports_trainings",
            "ipft_records",
            "gp_firings",
            "sosn_firings",
            "cas_trophies",
            "grenade_firings",
            "speed_marches",
            "assault_courses",
            "ret_states__ret_trg_type",
        )
        allowed_ids = self.get_allowed_organization_ids()
        if allowed_ids is not None:
            queryset = queryset.filter(organization_id__in=allowed_ids)
        return queryset


class SoldierAppointmentHistoryMixin:
    appointment_prefix = "appointment_histories"
    apr_prefix = "annual_performance_reports"
    mobile_prefix = "mobile_numbers"
    family_prefix = "family_members"
    medical_prefix = "medical_categories"
    education_prefix = "civil_educations"
    rank_history_prefix = "rank_histories"
    training_formset_classes = (
        ("Yearly Career Plan", "yearly_plans", SoldierYearlyPlanInlineFormSet),
        ("Major Commitments", "major_competitions", SoldierMajComInlineFormSet),
        ("Military Education / Qualification", "qualifications", SoldierQualificationInlineFormSet),
        ("Training & Sports", "sports_trainings", SportsTrainingFormSet),
        ("IPFT", "ipft_records", IPFTFormSet),
        ("RET State", "ret_states", RETStateFormSet),
        ("GP Firing", "gp_firings", GPFiringFormSet),
        ("SOSN Firing", "sosn_firings", SOSNFiringFormSet),
        ("CAS Trophy", "cas_trophies", CASTrophyFormSet),
        ("Grenade Firing", "grenade_firings", GrenadeFiringFormSet),
        ("Speed March", "speed_marches", SpeedMarchFormSet),
        ("Assault Course", "assault_courses", AssaultCourseFormSet),
    )

    def get_appointment_formset(self):
        kwargs = {
            "instance": getattr(self, "object", None),
            "prefix": self.appointment_prefix,
            "form_kwargs": {
                "organization_queryset": self.get_allowed_organizations(),
            },
        }
        if self.request.method in ("POST", "PUT"):
            kwargs.update({"data": self.request.POST, "files": self.request.FILES})
        return AppointmentHistoryFormSet(**kwargs)

    def get_apr_formset(self):
        kwargs = {
            "instance": getattr(self, "object", None),
            "prefix": self.apr_prefix,
        }
        if self.request.method in ("POST", "PUT"):
            kwargs.update({"data": self.request.POST, "files": self.request.FILES})
        return AnnualPerformanceReportFormSet(**kwargs)

    def get_mobile_formset(self):
        kwargs = {
            "instance": getattr(self, "object", None),
            "prefix": self.mobile_prefix,
        }
        if self.request.method in ("POST", "PUT"):
            kwargs.update({"data": self.request.POST, "files": self.request.FILES})
        return MobileNumberFormSet(**kwargs)

    def get_family_formset(self):
        kwargs = {
            "instance": getattr(self, "object", None),
            "prefix": self.family_prefix,
        }
        if self.request.method in ("POST", "PUT"):
            kwargs.update({"data": self.request.POST, "files": self.request.FILES})
        return FamilyFormSet(**kwargs)

    def get_medical_formset(self):
        kwargs = {
            "instance": getattr(self, "object", None),
            "prefix": self.medical_prefix,
        }
        if self.request.method in ("POST", "PUT"):
            kwargs.update({"data": self.request.POST, "files": self.request.FILES})
        return MedicalCategoryFormSet(**kwargs)

    def get_education_formset(self):
        kwargs = {
            "instance": getattr(self, "object", None),
            "prefix": self.education_prefix,
        }
        if self.request.method in ("POST", "PUT"):
            kwargs.update({"data": self.request.POST, "files": self.request.FILES})
        return CivilEducationFormSet(**kwargs)

    def get_rank_history_formset(self):
        kwargs = {
            "instance": getattr(self, "object", None),
            "prefix": self.rank_history_prefix,
            "form_kwargs": {
                "organization_queryset": self.get_allowed_organizations(),
            },
        }
        if self.request.method in ("POST", "PUT"):
            kwargs.update({"data": self.request.POST, "files": self.request.FILES})
        return RankHistoryFormSet(**kwargs)

    def get_training_formsets(self):
        result = []
        for title, prefix, formset_class in self.training_formset_classes:
            kwargs = {
                "instance": getattr(self, "object", None),
                "prefix": prefix,
            }
            if self.request.method in ("POST", "PUT"):
                kwargs.update({"data": self.request.POST, "files": self.request.FILES})
            result.append((title, formset_class(**kwargs)))
        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        context["field_groups"] = [
            (title, [form[field_name] for field_name in field_names])
            for title, field_names in PersonForm.FIELD_GROUPS
        ]
        context.setdefault("appointment_formset", self.get_appointment_formset())
        context.setdefault("apr_formset", self.get_apr_formset())
        context.setdefault("mobile_formset", self.get_mobile_formset())
        context.setdefault("family_formset", self.get_family_formset())
        context.setdefault("medical_formset", self.get_medical_formset())
        context.setdefault("education_formset", self.get_education_formset())
        context.setdefault("rank_history_formset", self.get_rank_history_formset())
        context.setdefault("training_formsets", self.get_training_formsets())
        return context


class RankCreateView(AdminPortalMixin, CreateView):
    model = Rank
    form_class = RankForm
    template_name = "common/simple_form.html"
    success_url = reverse_lazy("common:create_rank")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Create Rank"
        context["existing_items"] = Rank.objects.all()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_addition(self.request.user, self.object, "Rank created.")
        messages.success(self.request, "Rank added.")
        return response


class OrganizationCreateView(AdminPortalMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = "common/organization_form.html"
    success_url = reverse_lazy("common:create_organization")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Create Organization"
        context["existing_items"] = Organization.objects.select_related(
            "parent_organization"
        )
        context["org_kind_map"] = {
            str(org.pk): org.unit_kind
            for org in Organization.objects.only("id", "unit_kind")
        }
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_addition(self.request.user, self.object, "Organization created.")
        messages.success(self.request, "Organization added.")
        return response


class EREOrganizationCreateView(PortalContextMixin, CoRequiredMixin, CreateView):
    model = EREOrganization
    form_class = EREOrganizationForm
    template_name = "common/simple_form.html"
    success_url = reverse_lazy("common:create_ere")
    permission_message = "Only the CO or an admin can add ERE organizations."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Create ERE Organization"
        context["section_eyebrow"] = (
            "Admin" if getattr(self.request.user, "is_admin", False) else "A Matter"
        )
        context["page_intro"] = (
            "Add ERE organization names used on posting orders. "
            "The receiving company does not accept these moves; the CO approves and accepts them."
        )
        context["existing_items"] = EREOrganization.objects.select_related(
            "organization"
        )
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_addition(
            self.request.user,
            self.object,
            f"ERE organization '{self.object.name}' added.",
        )
        messages.success(
            self.request,
            f"{self.object.name} added. Company posting orders to this ERE wait for CO approval.",
        )
        return response


class EducationLevelCreateView(AdminPortalMixin, CreateView):
    model = CivilEducationLevel
    form_class = EducationLevelForm
    template_name = "common/simple_form.html"
    success_url = reverse_lazy("common:create_education_level")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Create Education Level"
        context["existing_items"] = CivilEducationLevel.objects.all()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_addition(self.request.user, self.object, "Education level created.")
        messages.success(self.request, "Education level added.")
        return response


class ActivityLogView(AdminPortalMixin, ListView):
    model = LogEntry
    template_name = "common/activity_log.html"
    context_object_name = "log_entries"
    paginate_by = 25

    def get_queryset(self):
        return LogEntry.objects.select_related("user", "content_type").order_by(
            "-action_time"
        )


class ServerMonitorView(AdminPortalMixin, ListView):
    template_name = "common/server_monitor.html"

    def get_queryset(self):
        return Person.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["monitor"] = {
            "cpu": "Local development host",
            "note": "Detailed host metrics are available on the deployed server.",
        }
        return context


class StatisticsView(AdminPortalMixin, ListView):
    template_name = "common/statistics.html"

    def get_queryset(self):
        return Person.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .services import get_admin_statistics

        context["stats"] = get_admin_statistics()
        context["by_org"] = (
            Organization.objects.annotate(
                strength=Count("persons", filter=Q(persons__on_strength=True))
            )
            .order_by("-strength", "organization_name")
        )
        return context


class SoldierListView(SoldierAccessMixin, ListView):
    model = Person
    template_name = "common/soldier_list.html"
    context_object_name = "soldiers"
    paginate_by = 10

    def get_queryset(self):
        queryset = Person.objects.on_strength().select_related("rank", "organization").order_by(
            "army_number"
        )
        allowed_ids = self.get_allowed_organization_ids()
        if allowed_ids is not None:
            queryset = queryset.filter(organization_id__in=allowed_ids)
        search = self.request.GET.get("q", "").strip()
        organization_id = self.request.GET.get("organization", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(army_number__icontains=search)
            )
        if organization_id.isdigit():
            org_id = int(organization_id)
            if allowed_ids is None or org_id in allowed_ids:
                queryset = queryset.filter(organization_id=org_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allowed_orgs = self.get_allowed_organizations()
        base = Person.objects.on_strength()
        allowed_ids = self.get_allowed_organization_ids()
        if allowed_ids is not None:
            base = base.filter(organization_id__in=allowed_ids)
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["organization_filter"] = self.request.GET.get("organization", "").strip()
        context["organizations"] = allowed_orgs
        context["has_company"] = allowed_orgs.exists()
        context["stats"] = {
            "total": base.count(),
            "orgs": allowed_orgs.count(),
            "mission": base.filter(mission=True).count(),
            "qualified": base.filter(qualification_for_next_rank=True).count(),
        }
        return context


class SoldierCreateView(SoldierAppointmentHistoryMixin, SoldierAccessMixin, CreateView):
    model = Person
    form_class = PersonForm
    template_name = "common/soldier_form.html"
    success_url = reverse_lazy("common:soldier_list")

    def form_valid(self, form):
        allowed_ids = self.get_allowed_organization_ids()
        if allowed_ids is not None and not allowed_ids:
            messages.error(
                self.request,
                "Assign an organization to your account before enlisting soldiers.",
            )
            return redirect("common:soldier_list")
        appointment_formset = self.get_appointment_formset()
        apr_formset = self.get_apr_formset()
        mobile_formset = self.get_mobile_formset()
        family_formset = self.get_family_formset()
        medical_formset = self.get_medical_formset()
        education_formset = self.get_education_formset()
        rank_history_formset = self.get_rank_history_formset()
        training_formsets = self.get_training_formsets()
        if not all((appointment_formset.is_valid(), apr_formset.is_valid(), mobile_formset.is_valid(), family_formset.is_valid(), medical_formset.is_valid(), education_formset.is_valid(), rank_history_formset.is_valid(), *(formset.is_valid() for _title, formset in training_formsets))):
            return self.form_invalid(form)
        with transaction.atomic():
            response = super().form_valid(form)
            appointment_formset.instance = self.object
            appointment_formset.save()
            apr_formset.instance = self.object
            apr_formset.save()
            mobile_formset.instance = self.object
            mobile_formset.save()
            family_formset.instance = self.object
            family_formset.save()
            medical_formset.instance = self.object
            medical_formset.save()
            education_formset.instance = self.object
            education_formset.save()
            rank_history_formset.instance = self.object
            rank_history_formset.save()
            for _title, training_formset in training_formsets:
                training_formset.instance = self.object
                training_formset.save()
        log_addition(self.request.user, self.object, "Soldier enlisted.")
        messages.success(self.request, f"{self.object.name} enlisted.")
        return response


class SoldierUpdateView(SoldierAppointmentHistoryMixin, SoldierRecordMixin, UpdateView):
    model = Person
    form_class = PersonForm
    template_name = "common/soldier_form.html"
    success_url = reverse_lazy("common:soldier_list")

    def form_valid(self, form):
        appointment_formset = self.get_appointment_formset()
        apr_formset = self.get_apr_formset()
        mobile_formset = self.get_mobile_formset()
        family_formset = self.get_family_formset()
        medical_formset = self.get_medical_formset()
        education_formset = self.get_education_formset()
        rank_history_formset = self.get_rank_history_formset()
        training_formsets = self.get_training_formsets()
        if not all((appointment_formset.is_valid(), apr_formset.is_valid(), mobile_formset.is_valid(), family_formset.is_valid(), medical_formset.is_valid(), education_formset.is_valid(), rank_history_formset.is_valid(), *(formset.is_valid() for _title, formset in training_formsets))):
            return self.form_invalid(form)
        with transaction.atomic():
            response = super().form_valid(form)
            appointment_formset.instance = self.object
            appointment_formset.save()
            apr_formset.instance = self.object
            apr_formset.save()
            mobile_formset.instance = self.object
            mobile_formset.save()
            family_formset.instance = self.object
            family_formset.save()
            medical_formset.instance = self.object
            medical_formset.save()
            education_formset.instance = self.object
            education_formset.save()
            rank_history_formset.instance = self.object
            rank_history_formset.save()
            for _title, training_formset in training_formsets:
                training_formset.instance = self.object
                training_formset.save()
        log_change(self.request.user, self.object, "Soldier updated.")
        messages.success(self.request, f"{self.object.name} updated.")
        return response


class SoldierDetailView(SoldierRecordMixin, DetailView):
    model = Person
    template_name = "common/soldier_detail.html"
    context_object_name = "soldier"


class SoldierDeleteView(SoldierRecordMixin, DeleteView):
    model = Person
    template_name = "common/soldier_confirm_delete.html"
    context_object_name = "soldier"
    success_url = reverse_lazy("common:soldier_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop("organization_queryset", None)
        return kwargs

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.on_strength = False
        self.object.save(update_fields=["on_strength"])
        log_deletion(
            self.request.user,
            self.object,
            "Soldier ID removed after posting to another unit.",
        )
        messages.success(
            self.request,
            f"{self.object.army_number} {self.object.name} removed from unit strength.",
        )
        return redirect(self.get_success_url())


class SoldierPDFView(SoldierRecordMixin, View):
    def get(self, request, *args, **kwargs):
        soldier = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        pdf_file = build_soldier_pdf(soldier)
        safe_number = "".join(
            character for character in soldier.army_number if character.isalnum()
        )
        response = HttpResponse(pdf_file.read(), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{safe_number or soldier.pk}-dossier.pdf"'
        )
        return response


class UnitSearchView(SoldierAccessMixin, ListView):
    template_name = "common/search.html"
    context_object_name = "soldiers"
    paginate_by = 20

    def get_queryset(self):
        from .search import search_soldiers

        query = self.request.GET.get("q", "").strip()
        self.interpretations = []
        if not query:
            return Person.objects.none()
        queryset, interpretations = search_soldiers(self.request.user, query)
        self.interpretations = interpretations
        return queryset.prefetch_related(
            "qualifications__courses__course_name__level",
        )

    def get_context_data(self, **kwargs):
        from .search import match_reasons

        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()
        soldiers = []
        for soldier in context["soldiers"]:
            soldier.match_reasons = match_reasons(soldier, query)
            soldiers.append(soldier)
        context["soldiers"] = soldiers
        context["search_query"] = query
        context["interpretations"] = getattr(self, "interpretations", [])
        context["result_count"] = (
            context["paginator"].count if context.get("paginator") else 0
        )
        context["example_queries"] = [
            "Which soldiers got B+ in BTT and Y+ in ATT",
            "Soldiers currently on leave",
            "HQ Company officers",
        ]
        return context


class UnitSearchSuggestView(SoldierAccessMixin, View):
    def get(self, request, *args, **kwargs):
        from .search import suggest_search

        query = request.GET.get("q", "").strip()
        return JsonResponse({"suggestions": suggest_search(request.user, query)})

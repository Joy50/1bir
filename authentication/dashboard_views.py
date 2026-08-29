from django.contrib import messages
from django.http import Http404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from common.activity import log_addition, log_change, log_deletion

from .forms import (
    DashboardSlideForm,
    HallOfFameCOForm,
    UnitAchievementForm,
    UnitHighlightForm,
    UnitProfileForm,
)
from .models import (
    DashboardSlide,
    HallOfFameCO,
    UnitAchievement,
    UnitHighlight,
    UnitProfile,
)
from .views import AdminRequiredMixin, PortalContextMixin


RESOURCE_REGISTRY = {
    "slides": {
        "model": DashboardSlide,
        "form_class": DashboardSlideForm,
        "label": "Image slides",
        "singular": "slide",
        "image_attr": "image",
        "blurb": "Photographs that rotate across the top of the home dashboard.",
    },
    "hall-of-fame": {
        "model": HallOfFameCO,
        "form_class": HallOfFameCOForm,
        "label": "Hall of Fame",
        "singular": "Commanding Officer",
        "image_attr": "photo",
        "blurb": "Every Commanding Officer of the battalion, with tenure, portrait, and quote.",
    },
    "achievements": {
        "model": UnitAchievement,
        "form_class": UnitAchievementForm,
        "label": "Achievements",
        "singular": "achievement",
        "image_attr": "image",
        "blurb": "Honours, operations, sports, and other unit accomplishments.",
    },
    "highlights": {
        "model": UnitHighlight,
        "form_class": UnitHighlightForm,
        "label": "Highlights",
        "singular": "highlight",
        "image_attr": None,
        "blurb": "Short identity cards under the Commanding Officer quote.",
    },
}


class DashboardManageHubView(PortalContextMixin, AdminRequiredMixin, TemplateView):
    template_name = "authentication/dashboard_hub.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["unit_profile"] = UnitProfile.load()
        context["resource_cards"] = [
            {
                "kind": kind,
                "label": spec["label"],
                "blurb": spec["blurb"],
                "count": spec["model"].objects.count(),
                "list_url": reverse("authentication:dashboard_resource_list", args=[kind]),
                "create_url": reverse(
                    "authentication:dashboard_resource_create", args=[kind]
                ),
            }
            for kind, spec in RESOURCE_REGISTRY.items()
        ]
        return context


class DashboardProfileUpdateView(PortalContextMixin, AdminRequiredMixin, UpdateView):
    model = UnitProfile
    form_class = UnitProfileForm
    template_name = "authentication/dashboard_form.html"
    success_url = reverse_lazy("authentication:dashboard_manage")

    def get_object(self, queryset=None):
        return UnitProfile.load()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Unit identity"
        context["page_blurb"] = (
            "Name, motto, location, crest, and the about text shown on the home dashboard."
        )
        context["cancel_url"] = reverse("authentication:dashboard_manage")
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_change(self.request.user, self.object, "Unit profile updated.")
        messages.success(self.request, "Unit identity saved.")
        return response


class DashboardResourceMixin(PortalContextMixin, AdminRequiredMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.kind = kwargs.get("kind")
        if self.kind not in RESOURCE_REGISTRY:
            raise Http404("Unknown dashboard section.")
        self.resource = RESOURCE_REGISTRY[self.kind]

    def get_queryset(self):
        return self.resource["model"].objects.all()

    def get_form_class(self):
        return self.resource["form_class"]

    def get_success_url(self):
        return reverse("authentication:dashboard_resource_list", args=[self.kind])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["kind"] = self.kind
        context["resource"] = self.resource
        context["cancel_url"] = reverse(
            "authentication:dashboard_resource_list", args=[self.kind]
        )
        return context


class DashboardResourceListView(DashboardResourceMixin, ListView):
    template_name = "authentication/dashboard_list.html"
    context_object_name = "entries"
    paginate_by = 40


class DashboardResourceCreateView(DashboardResourceMixin, CreateView):
    template_name = "authentication/dashboard_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        singular = self.resource["singular"]
        context["page_title"] = f"Add {singular}"
        context["page_blurb"] = self.resource["blurb"]
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_addition(
            self.request.user,
            self.object,
            f"{self.resource['singular'].capitalize()} added to the dashboard.",
        )
        messages.success(self.request, f"{self.resource['singular'].capitalize()} added.")
        return response


class DashboardResourceUpdateView(DashboardResourceMixin, UpdateView):
    template_name = "authentication/dashboard_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit {self.resource['singular']}"
        context["page_blurb"] = self.resource["blurb"]
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_change(
            self.request.user,
            self.object,
            f"{self.resource['singular'].capitalize()} updated.",
        )
        messages.success(self.request, f"{self.resource['singular'].capitalize()} saved.")
        return response


class DashboardResourceDeleteView(DashboardResourceMixin, DeleteView):
    template_name = "authentication/dashboard_confirm_delete.html"

    def form_valid(self, form):
        log_deletion(
            self.request.user,
            self.object,
            f"{self.resource['singular'].capitalize()} removed from the dashboard.",
        )
        messages.success(
            self.request, f"{self.resource['singular'].capitalize()} removed."
        )
        return super().form_valid(form)

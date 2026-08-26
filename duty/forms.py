from django import forms

from common.models import Person

from .models import DutyAssignment, DutyPost, SoldierPosting
from .services import available_posts, get_or_create_open_tour, suggested_soldiers


class DutyPostForm(forms.ModelForm):
    class Meta:
        model = DutyPost
        fields = (
            "name",
            "display_order",
            "duty_type",
            "day_strength",
            "night_strength",
            "latitude",
            "longitude",
            "organization",
            "description",
            "is_active",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "display_order": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "duty_type": forms.Select(attrs={"class": "form-select"}),
            "day_strength": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "night_strength": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "latitude": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.000001"}
            ),
            "longitude": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.000001"}
            ),
            "organization": forms.Select(attrs={"class": "form-select"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class SoldierPostingForm(forms.ModelForm):
    class Meta:
        model = SoldierPosting
        fields = ("soldier", "to_organization", "remarks")
        widgets = {
            "soldier": forms.Select(attrs={"class": "form-select"}),
            "to_organization": forms.Select(attrs={"class": "form-select"}),
            "remarks": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, soldier_queryset=None, organization_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if soldier_queryset is not None:
            self.fields["soldier"].queryset = soldier_queryset
        if organization_queryset is not None:
            self.fields["to_organization"].queryset = organization_queryset

    def clean(self):
        cleaned = super().clean()
        soldier = cleaned.get("soldier")
        destination = cleaned.get("to_organization")
        if soldier and destination and soldier.organization_id == destination.pk:
            self.add_error(
                "to_organization",
                "Choose a different unit. This soldier is already posted there.",
            )
        if soldier and SoldierPosting.objects.filter(
            soldier=soldier,
            status=SoldierPosting.STATUS_PENDING,
        ).exists():
            self.add_error("soldier", "This soldier already has a pending posting.")
        return cleaned


class DutyAssignForm(forms.ModelForm):
    class Meta:
        model = DutyAssignment
        fields = ("soldier", "post", "shift", "remarks")
        widgets = {
            "soldier": forms.Select(attrs={"class": "form-select"}),
            "post": forms.Select(attrs={"class": "form-select"}),
            "shift": forms.Select(attrs={"class": "form-select"}),
            "remarks": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        suggestions, _occupied, progress = suggested_soldiers(user, limit=None)
        due_ids = [soldier.pk for soldier in progress["still_due"]]
        active_soldier_ids = DutyAssignment.objects.filter(
            status=DutyAssignment.STATUS_ON_DUTY,
        ).values_list("soldier_id", flat=True)
        self.fields["soldier"].queryset = Person.objects.filter(
            pk__in=due_ids
        ).exclude(pk__in=active_soldier_ids).select_related("rank", "organization")
        self.fields["soldier"].widget.attrs.update({
            "data-searchable-soldier": "1",
            "aria-describedby": "soldierSearchHelp",
        })
        self.fields["post"].queryset = available_posts()
        self.progress = progress
        self.suggestions = suggestions

    def clean(self):
        cleaned = super().clean()
        soldier = cleaned.get("soldier")
        post = cleaned.get("post")
        shift = cleaned.get("shift")
        tour = get_or_create_open_tour()
        if soldier and DutyAssignment.objects.filter(
            soldier=soldier,
            status=DutyAssignment.STATUS_ON_DUTY,
        ).exists():
            self.add_error("soldier", "This soldier is already on duty.")
        if soldier and DutyAssignment.objects.filter(
            tour=tour,
            soldier=soldier,
        ).exclude(status=DutyAssignment.STATUS_CANCELLED).exists():
            self.add_error(
                "soldier",
                "This soldier has already been detailed in the current tour.",
            )
        if post and shift:
            capacity = (
                post.day_strength
                if shift == DutyAssignment.SHIFT_DAY
                else post.night_strength
            )
            assigned = DutyAssignment.objects.filter(
                post=post,
                shift=shift,
                status=DutyAssignment.STATUS_ON_DUTY,
            ).count()
            if capacity == 0:
                self.add_error("shift", f"{post.name} has no {shift} duty requirement.")
            elif assigned >= capacity:
                self.add_error(
                    "post",
                    f"{post.name} already has its full {shift} shift strength ({capacity}).",
                )
        if self.progress["still_due"] and soldier and soldier not in self.progress["still_due"]:
            self.add_error(
                "soldier",
                "Assign remaining soldiers first. The tour cannot repeat until everyone finishes.",
            )
        return cleaned

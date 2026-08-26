from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory, modelformset_factory

from common.models import Person

from .models import (
    AssaultCourse,
    CASTrophy,
    GrenadeFiring,
    GPFiring,
    IndividualCourseLevel,
    IndividualCourseName,
    IndividualQual,
    IndividualQualCourse,
    IPFT,
    LeaveState,
    LeaveType,
    ParticipationInMajCom,
    ParticipationInSportsTraining,
    RETState,
    SOSNFiring,
    SpeedMarch,
    UnitTrainingCyclePlan,
    YearlyPlan,
)
from .services import CYCLE_FIELDS, MAJCOM_FIELDS


class SoldierYearlyPlanForm(forms.Form):

    year = forms.IntegerField(
        min_value=1900,
        max_value=2100,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        blank_choice = [("", "— Not planned —")]
        option_choices = blank_choice + list(YearlyPlan.OPTION_CHOICES)

        for field_name, label in CYCLE_FIELDS:
            self.fields[field_name] = forms.ChoiceField(
                label=label,
                choices=option_choices,
                required=False,
                widget=forms.Select(
                    attrs={
                        "class": "form-select",
                    }
                ),
            )


class UnitTrainingCyclePlanForm(forms.ModelForm):
    class Meta:
        model = UnitTrainingCyclePlan
        fields = (
            "bde_lvl_cadre",
            "div_lvl_cadre",
            "pre_course_pe",
            "gpt",
            "misc_trg_event",
        )
        widgets = {
            field: forms.Textarea(attrs={"class": "form-control", "rows": 3})
            for field in (
                "bde_lvl_cadre", "div_lvl_cadre", "pre_course_pe", "gpt",
                "misc_trg_event",
            )
        }


UnitTrainingCyclePlanFormSet = modelformset_factory(
    UnitTrainingCyclePlan,
    form=UnitTrainingCyclePlanForm,
    extra=0,
)


class SoldierYearlyPlanInlineForm(forms.ModelForm):
    class Meta:
        model = YearlyPlan
        fields = ("year", "cycle", "option")
        widgets = {
            "year": forms.NumberInput(attrs={"class": "form-control", "min": 1900, "max": 2100}),
            "cycle": forms.Select(attrs={"class": "form-select"}),
            "option": forms.Select(attrs={"class": "form-select"}),
        }


SoldierYearlyPlanInlineFormSet = inlineformset_factory(
    Person, YearlyPlan, form=SoldierYearlyPlanInlineForm,
    fk_name="solider", extra=1, can_delete=True,
)


class ParticipationInMajComForm(forms.ModelForm):

    year = forms.IntegerField(
        min_value=1900,
        max_value=2100,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    class Meta:
        model = ParticipationInMajCom
        fields = [
            "year",
            "gp_trg",
            "st",
            "wt",
            "fi",
            "ihwf",
            "ff",
        ]
        widgets = {
            field_name: forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": label,
                }
            )
            for field_name, label in MAJCOM_FIELDS
        }


class SportsTrainingForm(forms.ModelForm):

    class Meta:
        model = ParticipationInSportsTraining
        fields = [
            "year",
            "cycle",
            "name_of_comp",
            "type_of_comp",
            "significant_achievement",
        ]
        widgets = {
            "year": forms.NumberInput(
                attrs={"class": "form-control", "min": "1900", "max": "2100"}
            ),
            "cycle": forms.Select(attrs={"class": "form-select"}),
            "name_of_comp": forms.TextInput(attrs={"class": "form-control"}),
            "type_of_comp": forms.Select(attrs={"class": "form-select"}),
            "significant_achievement": forms.TextInput(
                attrs={"class": "form-control"}
            ),
        }


def leave_type_for_slot(slot):
    if slot == LeaveState.SLOT_P_LEAVE:
        name = "Privilege Leave"
    elif slot.startswith("C lve"):
        name = "Casual Leave"
    else:
        return None
    leave_type, _created = LeaveType.objects.get_or_create(name=name)
    return leave_type


class LeaveApplyForm(forms.ModelForm):

    class Meta:
        model = LeaveState
        fields = [
            "slot",
            "from_date",
            "to_date",
            "remarks",
        ]
        widgets = {
            "slot": forms.Select(attrs={"class": "form-select"}),
            "from_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "to_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "remarks": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Reason or notes",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.soldier = kwargs.pop("soldier", None)
        super().__init__(*args, **kwargs)
        self.fields["slot"].required = True
        self.fields["slot"].label = "Leave slot"
        self.fields["remarks"].required = False
        self.fields["remarks"].label = "Reason / notes"

    def clean(self):
        cleaned = super().clean()
        from_date = cleaned.get("from_date")
        to_date = cleaned.get("to_date")
        slot = cleaned.get("slot")
        soldier = self.soldier or getattr(self.instance, "solider", None)

        if from_date and to_date and to_date < from_date:
            self.add_error("to_date", "To date must be on or after from date.")

        if slot:
            leave_type = leave_type_for_slot(slot)
            if leave_type is None:
                self.add_error("slot", "Choose a valid leave slot.")
            else:
                cleaned["leave_type"] = leave_type

        if soldier and from_date and to_date:
            overlapping = LeaveState.objects.filter(
                solider=soldier,
                status__in=[
                    LeaveState.STATUS_PENDING,
                    LeaveState.STATUS_APPROVED,
                ],
                from_date__lte=to_date,
                to_date__gte=from_date,
            )
            if self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            if overlapping.exists():
                raise forms.ValidationError(
                    "This soldier already has pending or approved leave "
                    "covering these dates."
                )

        if soldier and slot and from_date:
            same_slot = LeaveState.objects.filter(
                solider=soldier,
                slot=slot,
                from_date__year=from_date.year,
                status__in=[
                    LeaveState.STATUS_PENDING,
                    LeaveState.STATUS_APPROVED,
                ],
            )
            if self.instance.pk:
                same_slot = same_slot.exclude(pk=self.instance.pk)
            if same_slot.exists():
                self.add_error(
                    "slot",
                    "This slot is already used for that year.",
                )

        return cleaned

    def save(self, commit=True):
        leave = super().save(commit=False)
        leave_type = self.cleaned_data.get("leave_type")
        if leave_type is not None:
            leave.leave_type = leave_type
        if commit:
            leave.save()
        return leave


class IndividualQualForm(forms.ModelForm):

    class Meta:
        model = IndividualQual
        fields = [
            "year",
            "spl",
            "pe",
            "qual_for_next_promotion",
        ]
        widgets = {
            "year": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "maxlength": "4",
                    "placeholder": "2026",
                }
            ),
            "spl": forms.TextInput(attrs={"class": "form-control"}),
            "pe": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "PE result",
                }
            ),
            "qual_for_next_promotion": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["qual_for_next_promotion"].label = "Qualified for next promotion"


SoldierMajComInlineFormSet = inlineformset_factory(
    Person, ParticipationInMajCom, form=ParticipationInMajComForm,
    fk_name="solider", extra=1, can_delete=True,
)


SoldierQualificationInlineFormSet = inlineformset_factory(
    Person, IndividualQual, form=IndividualQualForm,
    fk_name="solider", extra=1, can_delete=True,
)


class IndividualQualCourseForm(forms.ModelForm):

    course_level = forms.ModelChoiceField(
        queryset=IndividualCourseLevel.objects.all(),
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "data-qual-level": "1",
            }
        ),
        label="Course level",
    )

    class Meta:
        model = IndividualQualCourse
        fields = [
            "course_name",
            "result",
        ]
        widgets = {
            "course_name": forms.Select(
                attrs={
                    "class": "form-select",
                    "data-qual-course": "1",
                }
            ),
            "result": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Pass, Fail, Qualified",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course_name"].label = "Course name"
        self.fields["course_name"].queryset = (
            IndividualCourseName.objects.select_related("level")
        )
        self.fields["course_name"].label_from_instance = lambda obj: obj.name
        instance = getattr(self, "instance", None)
        if instance and instance.pk and instance.course_name_id:
            self.fields["course_level"].initial = instance.course_name.level_id

    def clean(self):
        cleaned = super().clean()
        course = cleaned.get("course_name")
        level = cleaned.get("course_level")
        if course and level and course.level_id != level.pk:
            self.add_error(
                "course_name",
                "This course does not belong to the selected level.",
            )
        return cleaned


class QualCourseFormSet(BaseInlineFormSet):

    def clean(self):
        super().clean()
        seen = set()
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            data = form.cleaned_data
            if not data or data.get("DELETE"):
                continue
            course = data.get("course_name")
            if not course:
                continue
            if course.pk in seen:
                form.add_error(
                    "course_name",
                    "This course is already entered.",
                )
            seen.add(course.pk)


QualCourseFormSetFactory = inlineformset_factory(
    IndividualQual,
    IndividualQualCourse,
    form=IndividualQualCourseForm,
    formset=QualCourseFormSet,
    extra=1,
    can_delete=True,
)


SportsTrainingFormSet = inlineformset_factory(
    Person,
    ParticipationInSportsTraining,
    form=SportsTrainingForm,
    extra=1,
    can_delete=True,
    fk_name="person",
)


class IPFTForm(forms.ModelForm):

    class Meta:
        model = IPFT
        fields = [
            "type_of_ipft",
            "chance",
            "date",
            "result",
        ]
        widgets = {
            "type_of_ipft": forms.Select(attrs={"class": "form-select"}),
            "chance": forms.Select(attrs={"class": "form-select"}),
            "date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "result": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].input_formats = ["%Y-%m-%d"]


IPFTFormSet = inlineformset_factory(
    Person,
    IPFT,
    form=IPFTForm,
    extra=1,
    can_delete=True,
    fk_name="solider",
)


class RETStateForm(forms.ModelForm):

    class Meta:
        model = RETState
        fields = [
            "ret_trg_type",
            "date_performed",
            "result",
        ]
        widgets = {
            "ret_trg_type": forms.Select(attrs={"class": "form-select"}),
            "date_performed": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "result": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date_performed"].input_formats = ["%Y-%m-%d"]
        self.fields["ret_trg_type"].label = "RET training type"


RETStateFormSet = inlineformset_factory(
    Person,
    RETState,
    form=RETStateForm,
    extra=1,
    can_delete=True,
    fk_name="solider",
)


class FiringDateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date_of_firing"].input_formats = ["%Y-%m-%d"]


class GPFiringForm(FiringDateForm):

    class Meta:
        model = GPFiring
        fields = [
            "type_of_gp",
            "attempt",
            "date_of_firing",
            "result",
        ]
        widgets = {
            "type_of_gp": forms.Select(attrs={"class": "form-select"}),
            "attempt": forms.Select(attrs={"class": "form-select"}),
            "date_of_firing": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "result": forms.Select(attrs={"class": "form-select"}),
        }


GPFiringFormSet = inlineformset_factory(
    Person,
    GPFiring,
    form=GPFiringForm,
    extra=1,
    can_delete=True,
    fk_name="solider",
)


class SOSNFiringForm(FiringDateForm):

    class Meta:
        model = SOSNFiring
        fields = [
            "type_of_gp",
            "attempt",
            "date_of_firing",
            "gp",
            "hit",
            "total_marks",
            "result",
        ]
        widgets = {
            "type_of_gp": forms.Select(attrs={"class": "form-select"}),
            "attempt": forms.Select(attrs={"class": "form-select"}),
            "date_of_firing": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "gp": forms.TextInput(attrs={"class": "form-control"}),
            "hit": forms.TextInput(attrs={"class": "form-control"}),
            "total_marks": forms.TextInput(attrs={"class": "form-control"}),
            "result": forms.Select(attrs={"class": "form-select"}),
        }


SOSNFiringFormSet = inlineformset_factory(
    Person,
    SOSNFiring,
    form=SOSNFiringForm,
    extra=1,
    can_delete=True,
    fk_name="solider",
)


class CASTrophyForm(FiringDateForm):

    class Meta:
        model = CASTrophy
        fields = [
            "date_of_firing",
            "gp",
            "hit",
            "total_marks",
            "result",
        ]
        widgets = {
            "date_of_firing": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "gp": forms.TextInput(attrs={"class": "form-control"}),
            "hit": forms.TextInput(attrs={"class": "form-control"}),
            "total_marks": forms.TextInput(attrs={"class": "form-control"}),
            "result": forms.Select(attrs={"class": "form-select"}),
        }


CASTrophyFormSet = inlineformset_factory(
    Person,
    CASTrophy,
    form=CASTrophyForm,
    extra=1,
    can_delete=True,
    fk_name="solider",
)


class GrenadeFiringForm(FiringDateForm):

    class Meta:
        model = GrenadeFiring
        fields = [
            "attempt",
            "date_of_firing",
            "result",
        ]
        widgets = {
            "attempt": forms.Select(attrs={"class": "form-select"}),
            "date_of_firing": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "result": forms.Select(attrs={"class": "form-select"}),
        }


GrenadeFiringFormSet = inlineformset_factory(
    Person,
    GrenadeFiring,
    form=GrenadeFiringForm,
    extra=1,
    can_delete=True,
    fk_name="solider",
)


class EventDateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date_of_event"].input_formats = ["%Y-%m-%d"]


class SpeedMarchForm(EventDateForm):

    class Meta:
        model = SpeedMarch
        fields = [
            "attempt",
            "date_of_event",
            "result",
        ]
        widgets = {
            "attempt": forms.Select(attrs={"class": "form-select"}),
            "date_of_event": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "result": forms.Select(attrs={"class": "form-select"}),
        }


SpeedMarchFormSet = inlineformset_factory(
    Person,
    SpeedMarch,
    form=SpeedMarchForm,
    extra=1,
    can_delete=True,
    fk_name="solider",
)


class AssaultCourseForm(EventDateForm):

    class Meta:
        model = AssaultCourse
        fields = [
            "attempt",
            "date_of_event",
            "time",
            "result",
        ]
        widgets = {
            "attempt": forms.Select(attrs={"class": "form-select"}),
            "date_of_event": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "time": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Time",
                }
            ),
            "result": forms.Select(attrs={"class": "form-select"}),
        }


AssaultCourseFormSet = inlineformset_factory(
    Person,
    AssaultCourse,
    form=AssaultCourseForm,
    extra=1,
    can_delete=True,
    fk_name="solider",
)

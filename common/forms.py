from django import forms

from .models import (
    AnnualPerformanceReport,
    AppointmentHistory,
    CivilEducation,
    CivilEducationLevel,
    Family,
    MedicalCategory,
    MobileNumber,
    Organization,
    Person,
    Rank,
    ServiceHistory,
)

INPUT_CLASS = "form-control"
SELECT_CLASS = "form-select"


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault("class", SELECT_CLASS)
            elif not isinstance(widget, (forms.CheckboxInput, forms.FileInput)):
                widget.attrs.setdefault("class", INPUT_CLASS)


class RankForm(StyledModelForm):
    class Meta:
        model = Rank
        fields = ("rank_name", "category")


class OrganizationForm(StyledModelForm):
    class Meta:
        model = Organization
        fields = ("organization_name", "unit_kind", "parent_organization")
        labels = {
            "unit_kind": "Organization type",
            "parent_organization": "Parent organization",
        }
        help_texts = {
            "unit_kind": "Unit contains battalions, a battalion contains companies, a company contains platoons, and a platoon contains sections.",
            "parent_organization": "Leave blank for a Unit. A Battalion sits under a Unit. A Company sits under a Battalion or a Unit.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parents = Organization.objects.exclude(
            unit_kind=Organization.KIND_SECTION
        ).order_by("organization_name")
        if self.instance.pk:
            parents = parents.exclude(pk=self.instance.pk)
        self.fields["parent_organization"].queryset = parents
        self.fields["parent_organization"].required = False
        self.fields["parent_organization"].label_from_instance = (
            lambda org: f"{org.organization_name} ({org.get_unit_kind_display()})"
        )
        self.fields["unit_kind"].required = True

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("unit_kind") == Organization.KIND_UNIT:
            cleaned_data["parent_organization"] = None
        return cleaned_data


class EducationLevelForm(StyledModelForm):
    class Meta:
        model = CivilEducationLevel
        fields = ("level_name",)


class PersonForm(StyledModelForm):
    FIELD_GROUPS = (
        ("Identity & service", ("army_number", "rank", "name", "organization", "dob", "doe", "batch", "al1_13", "dor")),
        ("Conduct & posting", ("discipline", "punishment", "mission")),
        ("Medical", ("height", "overweight")),
        ("Appointment & promotion", ("qualification_for_next_rank", "reason_unqualified")),
        ("Identification & online details", ("nid_number", "birth_certificate_number", "phone_registration_nid", "phone_imei", "social_media_links", "passport_number", "passport_type", "service_id_card_number")),
        ("Address & photo", ("present_address", "permanent_address", "photo")),
    )

    class Meta:
        model = Person
        fields = (
            "army_number",
            "rank",
            "name",
            "organization",
            "dob",
            "doe",
            "batch",
            "al1_13",
            "dor",
            "discipline",
            "punishment",
            "mission",
            "height",
            "overweight",
            "qualification_for_next_rank",
            "reason_unqualified",
            "nid_number",
            "birth_certificate_number",
            "phone_registration_nid",
            "phone_imei",
            "social_media_links",
            "passport_number",
            "passport_type",
            "service_id_card_number",
            "present_address",
            "permanent_address",
            "photo",
        )
        labels = {
            "organization": "Coy/ERE", "dob": "DOB", "doe": "DOE",
            "al1_13": "AI 1/13", "dor": "DOR", "mission": "Mission (Yes/No)",
            "height": "Height (Inch/CM)",
            "overweight": "Over Weight (KG/Pound)",
            "qualification_for_next_rank": "Qualified for Next Rank", "reason_unqualified": "Reason of Unqualified",
            "nid_number": "NID Number",
            "birth_certificate_number": "Birth Certificate Number", "phone_registration_nid": "NID Used for Personal Cell Phone",
            "phone_imei": "IMEI No of Personal Cell Phone", "social_media_links": "Social Media ID Links",
            "passport_type": "Passport Type (Official/Unofficial)", "service_id_card_number": "Svc ID Card Number",
            "permanent_address": "Permanent Address", "photo": "Photo (Uniform with Present Rank)",
        }
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
            "doe": forms.DateInput(attrs={"type": "date"}),
            "dor": forms.DateInput(attrs={"type": "date"}),
            "discipline": forms.Textarea(attrs={"rows": 2}),
            "punishment": forms.Textarea(attrs={"rows": 2}),
            "present_address": forms.Textarea(attrs={"rows": 2}),
            "permanent_address": forms.Textarea(attrs={"rows": 2}),
        }

        widgets["reason_unqualified"] = forms.Textarea(attrs={"rows": 2})
        widgets["social_media_links"] = forms.Textarea(attrs={"rows": 2})

    def __init__(self, *args, organization_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization_queryset is not None:
            self.fields["organization"].queryset = organization_queryset


class AppointmentHistoryForm(StyledModelForm):
    class Meta:
        model = AppointmentHistory
        fields = ("appointment_name", "organization", "start_date", "end_date")
        labels = {
            "appointment_name": "Appointment / Unit detail",
            "organization": "Previous Unit/Organization",
        }
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, organization_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization_queryset is not None:
            self.fields["organization"].queryset = organization_queryset


AppointmentHistoryFormSet = forms.inlineformset_factory(
    Person,
    AppointmentHistory,
    form=AppointmentHistoryForm,
    fields=("appointment_name", "organization", "start_date", "end_date"),
    extra=1,
    can_delete=True,
)


class AnnualPerformanceReportForm(StyledModelForm):
    class Meta:
        model = AnnualPerformanceReport
        fields = ("year", "report", "score")
        labels = {
            "report": "APR report/details",
            "score": "APR score",
        }
        widgets = {
            "year": forms.NumberInput(attrs={"min": 1900, "max": 2100}),
            "report": forms.Textarea(attrs={"rows": 2}),
            "score": forms.NumberInput(attrs={"min": 0}),
        }


AnnualPerformanceReportFormSet = forms.inlineformset_factory(
    Person,
    AnnualPerformanceReport,
    form=AnnualPerformanceReportForm,
    fields=("year", "report", "score"),
    extra=1,
    can_delete=True,
)


class MobileNumberForm(StyledModelForm):
    class Meta:
        model = MobileNumber
        fields = ("type_of_number", "mobile_number")
        labels = {
            "type_of_number": "Number type",
            "mobile_number": "Mobile number",
        }
        widgets = {
            "type_of_number": forms.Select(attrs={"class": SELECT_CLASS}),
            "mobile_number": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "e.g. 01700000000"}
            ),
        }


MobileNumberFormSet = forms.inlineformset_factory(
    Person,
    MobileNumber,
    form=MobileNumberForm,
    fields=("type_of_number", "mobile_number"),
    extra=1,
    can_delete=True,
)


class FamilyForm(StyledModelForm):
    class Meta:
        model = Family
        fields = ("relation_name", "occupation", "remarks")
        labels = {
            "relation_name": "Relation name",
            "occupation": "Occupation",
            "remarks": "Remarks",
        }
        widgets = {
            "relation_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "occupation": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "remarks": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
        }


FamilyFormSet = forms.inlineformset_factory(
    Person,
    Family,
    form=FamilyForm,
    fields=("relation_name", "occupation", "remarks"),
    extra=1,
    can_delete=True,
)


class MedicalCategoryForm(StyledModelForm):
    class Meta:
        model = MedicalCategory
        fields = ("type", "from_date", "to_date")
        labels = {"type": "Medical category"}
        widgets = {
            "type": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "from_date": forms.DateInput(attrs={"class": INPUT_CLASS, "type": "date"}),
            "to_date": forms.DateInput(attrs={"class": INPUT_CLASS, "type": "date"}),
        }


MedicalCategoryFormSet = forms.inlineformset_factory(
    Person,
    MedicalCategory,
    form=MedicalCategoryForm,
    fields=("type", "from_date", "to_date"),
    extra=1,
    can_delete=True,
)


class CivilEducationForm(StyledModelForm):
    class Meta:
        model = CivilEducation
        fields = ("level", "institution_name", "from_date", "to_date", "grade")
        widgets = {
            "from_date": forms.DateInput(attrs={"type": "date"}),
            "to_date": forms.DateInput(attrs={"type": "date"}),
        }


CivilEducationFormSet = forms.inlineformset_factory(
    Person,
    CivilEducation,
    form=CivilEducationForm,
    fields=("level", "institution_name", "from_date", "to_date", "grade"),
    extra=1,
    can_delete=True,
)


class RankHistoryForm(StyledModelForm):
    class Meta:
        model = ServiceHistory
        fields = ("rank", "organization", "start_date", "end_date")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, organization_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization_queryset is not None:
            self.fields["organization"].queryset = organization_queryset


RankHistoryFormSet = forms.inlineformset_factory(
    Person,
    ServiceHistory,
    form=RankHistoryForm,
    fields=("rank", "organization", "start_date", "end_date"),
    extra=1,
    can_delete=True,
)

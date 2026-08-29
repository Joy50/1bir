from django.contrib import admin

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


class ServiceHistoryInline(admin.TabularInline):
    model = ServiceHistory
    extra = 0


class CivilEducationInline(admin.TabularInline):
    model = CivilEducation
    extra = 0


class MedicalCategoryInline(admin.TabularInline):
    model = MedicalCategory
    extra = 0


class AnnualPerformanceReportInline(admin.TabularInline):
    model = AnnualPerformanceReport
    extra = 0


class AppointmentHistoryInline(admin.TabularInline):
    model = AppointmentHistory
    extra = 0


class MobileNumberInline(admin.TabularInline):
    model = MobileNumber
    extra = 0


class FamilyInline(admin.TabularInline):
    model = Family
    extra = 0


@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    search_fields = ("rank_name",)
    list_display = ("rank_name", "category")
    list_filter = ("category",)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    search_fields = ("organization_name",)
    list_display = ("organization_name", "parent_organization", "unit_kind")
    list_filter = ("unit_kind",)


@admin.register(CivilEducationLevel)
class CivilEducationLevelAdmin(admin.ModelAdmin):
    search_fields = ("level_name",)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("army_number", "name", "rank", "organization", "batch", "mission", "qualification_for_next_rank")
    search_fields = ("name", "army_number", "nid_number", "service_id_card_number", "mobile_numbers__mobile_number")
    list_filter = ("rank", "organization", "batch", "mission", "qualification_for_next_rank")
    autocomplete_fields = ("rank", "organization")
    readonly_fields = (
        "present_age", "present_service_years", "civil_education",
        "physical_efficiency", "army_courses", "cadres", "specialist_cadre",
        "all_apr",
        "previous_unit_organizations",
        "previous_rank_date", "present_rank_date",
    )
    fieldsets = (
        ("Identity & service", {"fields": ("army_number", "rank", "name", "organization", "dob", "doe", "batch", ("present_age", "present_service_years"), ("previous_rank_date", "present_rank_date"), "al1_13", "dor")} ),
        ("Conduct & posting", {"fields": ("discipline", "punishment", "mission")} ),
        ("Training-derived particulars", {"description": "These values are maintained in Training and are read-only here.", "fields": ("civil_education", "physical_efficiency", "army_courses", "cadres", "specialist_cadre")} ),
        ("Annual performance summary", {"description": "Manage individual APR entries using the inline below.", "fields": ("all_apr",)}),
        ("Medical", {"fields": ("height", "overweight")} ),
        ("Promotion", {"fields": ("qualification_for_next_rank", "reason_unqualified")} ),
        ("Previous Unit/Organizations", {"description": "Generated from Appointment History entries below.", "fields": ("previous_unit_organizations",)}),
        ("Identification & address", {"fields": ("nid_number", "birth_certificate_number", "phone_registration_nid", "phone_imei", "social_media_links", "passport_number", "passport_type", "service_id_card_number", "present_address", "permanent_address", "photo")} ),
    )
    inlines = (
        ServiceHistoryInline,
        CivilEducationInline,
        MedicalCategoryInline,
        AnnualPerformanceReportInline,
        AppointmentHistoryInline,
        MobileNumberInline,
        FamilyInline,
    )

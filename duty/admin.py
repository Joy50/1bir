from django.contrib import admin

from .models import (
    DutyAssignment, DutyPost, DutyTour, ParadeAbsenceDocument, ParadeState, ParadeStateCompany,
    SoldierPosting,
)


@admin.register(DutyPost)
class DutyPostAdmin(admin.ModelAdmin):
    list_display = (
        "display_order", "name", "duty_type", "day_strength", "night_strength",
        "total_strength", "organization", "is_active",
    )
    search_fields = ("name", "description")
    list_filter = ("duty_type", "is_active", "organization")


@admin.register(SoldierPosting)
class SoldierPostingAdmin(admin.ModelAdmin):
    list_display = (
        "soldier",
        "from_organization",
        "to_organization",
        "status",
        "posted_by",
        "posted_at",
    )
    list_filter = ("status",)
    search_fields = ("soldier__name", "soldier__army_number")


@admin.register(DutyTour)
class DutyTourAdmin(admin.ModelAdmin):
    list_display = ("number", "status", "opened_at", "reported_at", "reported_by")


@admin.register(DutyAssignment)
class DutyAssignmentAdmin(admin.ModelAdmin):
    list_display = ("soldier", "post", "shift", "tour", "status", "assigned_at", "completed_at")
    list_filter = ("shift", "status")
    search_fields = ("soldier__name", "post__name")


class ParadeStateCompanyInline(admin.TabularInline):
    model = ParadeStateCompany
    extra = 0


class ParadeAbsenceDocumentInline(admin.TabularInline):
    model = ParadeAbsenceDocument
    extra = 0
    readonly_fields = ("uploaded_by", "uploaded_at")


@admin.register(ParadeState)
class ParadeStateAdmin(admin.ModelAdmin):
    list_display = ("report_date", "authorized_total", "created_by", "updated_at")
    inlines = (ParadeStateCompanyInline, ParadeAbsenceDocumentInline,)

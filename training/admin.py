from django.contrib import admin

from common.admin import PersonAdmin

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
    RETTrainingType,
    SOSNFiring,
    SpeedMarch,
    UnitTrainingCyclePlan,
    YearlyPlan,
)


class IndividualCourseNameInline(admin.TabularInline):

    model = IndividualCourseName
    extra = 1
    fields = ("name",)
    ordering = ("name",)


class IndividualQualCourseInline(admin.TabularInline):

    model = IndividualQualCourse
    extra = 1
    fields = (
        "course_name",
        "result",
    )
    autocomplete_fields = ("course_name",)
    ordering = (
        "course_name__level__name",
        "course_name__name",
    )


class IndividualQualInline(admin.TabularInline):

    model = IndividualQual
    extra = 0
    classes = ("collapse",)
    fields = (
        "year",
        "spl",
        "pe",
        "qual_for_next_promotion",
    )
    ordering = ("-year",)
    fk_name = "solider"


class YearlyPlanInline(admin.TabularInline):

    model = YearlyPlan
    extra = 0
    classes = ("collapse",)
    fields = ("year", "cycle", "option")
    ordering = ("-year", "cycle")
    fk_name = "solider"


class MajComInline(admin.TabularInline):

    model = ParticipationInMajCom
    extra = 0
    classes = ("collapse",)
    fields = ("year", "gp_trg", "st", "wt", "fi", "ihwf", "ff")
    ordering = ("-year",)
    fk_name = "solider"


class LeaveStateInline(admin.TabularInline):

    model = LeaveState
    extra = 0
    classes = ("collapse",)
    fields = (
        "leave_type",
        "slot",
        "from_date",
        "to_date",
        "status",
        "no_days",
        "applied_by",
        "approved_by",
    )
    autocomplete_fields = (
        "leave_type",
        "applied_by",
        "approved_by",
    )
    readonly_fields = ("no_days",)
    ordering = ("-from_date",)
    fk_name = "solider"


class SportsTrainingInline(admin.TabularInline):

    model = ParticipationInSportsTraining
    extra = 0
    classes = ("collapse",)
    fields = (
        "year",
        "cycle",
        "name_of_comp",
        "type_of_comp",
        "significant_achievement",
    )
    ordering = ("name_of_comp",)


class IPFTInline(admin.TabularInline):

    model = IPFT
    extra = 0
    classes = ("collapse",)
    fields = (
        "type_of_ipft",
        "chance",
        "date",
        "result",
    )
    ordering = ("-date",)
    fk_name = "solider"


class RETStateInline(admin.TabularInline):

    model = RETState
    extra = 0
    classes = ("collapse",)
    fields = (
        "ret_trg_type",
        "date_performed",
        "result",
    )
    autocomplete_fields = ("ret_trg_type",)
    ordering = ("-date_performed",)
    fk_name = "solider"


class GPFiringInline(admin.TabularInline):

    model = GPFiring
    extra = 0
    classes = ("collapse",)
    fields = (
        "type_of_gp",
        "attempt",
        "date_of_firing",
        "result",
    )
    ordering = ("-date_of_firing",)
    fk_name = "solider"


class SOSNFiringInline(admin.TabularInline):

    model = SOSNFiring
    extra = 0
    classes = ("collapse",)
    fields = (
        "type_of_gp",
        "attempt",
        "date_of_firing",
        "gp",
        "hit",
        "total_marks",
        "result",
    )
    ordering = ("-date_of_firing",)
    fk_name = "solider"


class CASTrophyInline(admin.TabularInline):

    model = CASTrophy
    extra = 0
    classes = ("collapse",)
    fields = (
        "date_of_firing",
        "gp",
        "hit",
        "total_marks",
        "result",
    )
    ordering = ("-date_of_firing",)
    fk_name = "solider"


class GrenadeFiringInline(admin.TabularInline):

    model = GrenadeFiring
    extra = 0
    classes = ("collapse",)
    fields = (
        "attempt",
        "date_of_firing",
        "result",
    )
    ordering = ("-date_of_firing",)
    fk_name = "solider"


class SpeedMarchInline(admin.TabularInline):

    model = SpeedMarch
    extra = 0
    classes = ("collapse",)
    fields = (
        "attempt",
        "date_of_event",
        "result",
    )
    ordering = ("-date_of_event",)
    fk_name = "solider"


class AssaultCourseInline(admin.TabularInline):

    model = AssaultCourse
    extra = 0
    classes = ("collapse",)
    fields = (
        "attempt",
        "date_of_event",
        "time",
        "result",
    )
    ordering = ("-date_of_event",)
    fk_name = "solider"


PersonAdmin.inlines = tuple(PersonAdmin.inlines) + (
    YearlyPlanInline,
    MajComInline,
    IndividualQualInline,
    LeaveStateInline,
    SportsTrainingInline,
    IPFTInline,
    RETStateInline,
    GPFiringInline,
    SOSNFiringInline,
    CASTrophyInline,
    GrenadeFiringInline,
    SpeedMarchInline,
    AssaultCourseInline,
)


@admin.register(IndividualCourseLevel)
class IndividualCourseLevelAdmin(admin.ModelAdmin):

    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    inlines = (IndividualCourseNameInline,)
    list_per_page = 25


@admin.register(IndividualCourseName)
class IndividualCourseNameAdmin(admin.ModelAdmin):

    list_display = ("name", "level")
    search_fields = ("name", "level__name")
    list_filter = ("level",)
    autocomplete_fields = ("level",)
    list_select_related = ("level",)
    ordering = ("level__name", "name")
    list_per_page = 25


@admin.register(IndividualQual)
class IndividualQualAdmin(admin.ModelAdmin):

    list_display = (
        "solider",
        "year",
        "spl",
        "pe",
        "qual_for_next_promotion",
    )
    search_fields = (
        "solider__name",
        "solider__army_number",
        "spl",
        "pe",
        "year",
    )
    list_filter = (
        "year",
        "qual_for_next_promotion",
    )
    autocomplete_fields = ("solider",)
    list_select_related = ("solider",)
    inlines = (IndividualQualCourseInline,)
    ordering = ("-year",)
    list_per_page = 25


@admin.register(YearlyPlan)
class YearlyPlanAdmin(admin.ModelAdmin):

    list_display = ("solider", "year", "cycle", "option")
    search_fields = (
        "solider__name",
        "solider__army_number",
    )
    list_filter = ("year", "cycle", "option")
    autocomplete_fields = ("solider",)
    list_select_related = ("solider",)
    ordering = ("-year", "cycle")
    list_per_page = 25


@admin.register(UnitTrainingCyclePlan)
class UnitTrainingCyclePlanAdmin(admin.ModelAdmin):
    list_display = ("year", "organization", "cycle", "bde_lvl_cadre", "div_lvl_cadre", "gpt")
    list_filter = ("year", "organization", "cycle")
    ordering = ("-year", "cycle")


@admin.register(ParticipationInMajCom)
class ParticipationInMajComAdmin(admin.ModelAdmin):

    list_display = (
        "solider",
        "year",
        "gp_trg",
        "st",
        "wt",
        "fi",
        "ihwf",
        "ff",
    )
    search_fields = (
        "solider__name",
        "solider__army_number",
        "gp_trg",
        "st",
        "wt",
        "fi",
        "ihwf",
        "ff",
    )
    list_filter = ("year",)
    autocomplete_fields = ("solider",)
    list_select_related = ("solider",)
    ordering = ("-year",)
    list_per_page = 25


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):

    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 25


@admin.register(LeaveState)
class LeaveStateAdmin(admin.ModelAdmin):

    list_display = (
        "solider",
        "leave_type",
        "slot",
        "from_date",
        "to_date",
        "status",
        "no_days",
        "total_no_days",
        "applied_by",
        "approved_by",
    )
    search_fields = (
        "solider__name",
        "solider__army_number",
        "leave_type__name",
        "applied_by__name",
        "applied_by__username",
        "approved_by__name",
        "approved_by__username",
        "remarks",
    )
    list_filter = (
        "status",
        "leave_type",
        "slot",
        "from_date",
    )
    autocomplete_fields = (
        "solider",
        "leave_type",
        "applied_by",
        "approved_by",
    )
    list_select_related = (
        "solider",
        "leave_type",
        "applied_by",
        "approved_by",
    )
    date_hierarchy = "from_date"
    ordering = ("-from_date",)
    readonly_fields = (
        "no_days",
        "applied_at",
    )
    list_per_page = 25
    fieldsets = (
        (
            "Application",
            {
                "fields": (
                    "solider",
                    "leave_type",
                    "from_date",
                    "to_date",
                    "remarks",
                    "applied_by",
                    "applied_at",
                )
            },
        ),
        (
            "Decision",
            {
                "fields": (
                    "status",
                    "approved_by",
                    "decided_at",
                )
            },
        ),
        (
            "Days",
            {
                "fields": (
                    "no_days",
                    "total_no_days",
                )
            },
        ),
    )


@admin.register(ParticipationInSportsTraining)
class ParticipationInSportsTrainingAdmin(admin.ModelAdmin):

    list_display = (
        "person",
        "year",
        "cycle",
        "name_of_comp",
        "type_of_comp",
        "significant_achievement",
    )
    search_fields = (
        "person__name",
        "person__army_number",
        "name_of_comp",
        "significant_achievement",
    )
    list_filter = ("year", "cycle", "type_of_comp")
    autocomplete_fields = ("person",)
    list_select_related = ("person",)
    ordering = ("person__army_number", "name_of_comp")
    list_per_page = 25


@admin.register(IPFT)
class IPFTAdmin(admin.ModelAdmin):

    list_display = (
        "solider",
        "type_of_ipft",
        "chance",
        "date",
        "result",
    )
    search_fields = (
        "solider__name",
        "solider__army_number",
    )
    list_filter = (
        "type_of_ipft",
        "chance",
        "result",
        "date",
    )
    autocomplete_fields = ("solider",)
    list_select_related = ("solider",)
    date_hierarchy = "date"
    ordering = ("-date",)
    list_per_page = 25


@admin.register(RETTrainingType)
class RETTrainingTypeAdmin(admin.ModelAdmin):

    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 25


@admin.register(RETState)
class RETStateAdmin(admin.ModelAdmin):

    list_display = (
        "solider",
        "ret_trg_type",
        "date_performed",
        "result",
    )
    search_fields = (
        "solider__name",
        "solider__army_number",
        "ret_trg_type__name",
    )
    list_filter = (
        "ret_trg_type",
        "result",
        "date_performed",
    )
    autocomplete_fields = (
        "solider",
        "ret_trg_type",
    )
    list_select_related = (
        "solider",
        "ret_trg_type",
    )
    date_hierarchy = "date_performed"
    ordering = ("-date_performed",)
    list_per_page = 25


@admin.register(GPFiring)
class GPFiringAdmin(admin.ModelAdmin):

    list_display = (
        "solider",
        "type_of_gp",
        "attempt",
        "date_of_firing",
        "result",
    )
    search_fields = (
        "solider__name",
        "solider__army_number",
    )
    list_filter = (
        "type_of_gp",
        "attempt",
        "result",
        "date_of_firing",
    )
    autocomplete_fields = ("solider",)
    list_select_related = ("solider",)
    date_hierarchy = "date_of_firing"
    ordering = ("-date_of_firing",)
    list_per_page = 25


@admin.register(SOSNFiring)
class SOSNFiringAdmin(admin.ModelAdmin):

    list_display = (
        "solider",
        "type_of_gp",
        "attempt",
        "date_of_firing",
        "gp",
        "hit",
        "total_marks",
        "result",
    )
    search_fields = (
        "solider__name",
        "solider__army_number",
    )
    list_filter = (
        "type_of_gp",
        "attempt",
        "result",
        "date_of_firing",
    )
    autocomplete_fields = ("solider",)
    list_select_related = ("solider",)
    date_hierarchy = "date_of_firing"
    ordering = ("-date_of_firing",)
    list_per_page = 25


@admin.register(CASTrophy)
class CASTrophyAdmin(admin.ModelAdmin):

    list_display = (
        "solider",
        "date_of_firing",
        "gp",
        "hit",
        "total_marks",
        "result",
    )
    search_fields = (
        "solider__name",
        "solider__army_number",
    )
    list_filter = (
        "result",
        "date_of_firing",
    )
    autocomplete_fields = ("solider",)
    list_select_related = ("solider",)
    date_hierarchy = "date_of_firing"
    ordering = ("-date_of_firing",)
    list_per_page = 25


@admin.register(GrenadeFiring)
class GrenadeFiringAdmin(admin.ModelAdmin):

    list_display = (
        "solider",
        "attempt",
        "date_of_firing",
        "result",
    )
    search_fields = (
        "solider__name",
        "solider__army_number",
    )
    list_filter = (
        "attempt",
        "result",
        "date_of_firing",
    )
    autocomplete_fields = ("solider",)
    list_select_related = ("solider",)
    date_hierarchy = "date_of_firing"
    ordering = ("-date_of_firing",)
    list_per_page = 25


@admin.register(SpeedMarch)
class SpeedMarchAdmin(admin.ModelAdmin):

    list_display = (
        "solider",
        "attempt",
        "date_of_event",
        "result",
    )
    search_fields = (
        "solider__name",
        "solider__army_number",
    )
    list_filter = (
        "attempt",
        "result",
        "date_of_event",
    )
    autocomplete_fields = ("solider",)
    list_select_related = ("solider",)
    date_hierarchy = "date_of_event"
    ordering = ("-date_of_event",)
    list_per_page = 25


@admin.register(AssaultCourse)
class AssaultCourseAdmin(admin.ModelAdmin):

    list_display = (
        "solider",
        "attempt",
        "date_of_event",
        "time",
        "result",
    )
    search_fields = (
        "solider__name",
        "solider__army_number",
    )
    list_filter = (
        "attempt",
        "result",
        "date_of_event",
    )
    autocomplete_fields = ("solider",)
    list_select_related = ("solider",)
    date_hierarchy = "date_of_event"
    ordering = ("-date_of_event",)
    list_per_page = 25

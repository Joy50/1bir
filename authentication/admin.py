from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import (
    DashboardSlide,
    HallOfFameCO,
    UnitAchievement,
    UnitHighlight,
    UnitProfile,
    User,
)


class PortalUserChangeForm(UserChangeForm):

    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


class PortalUserCreationForm(AdminUserCreationForm):

    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("username", "name", "role", "rank", "organizations")


@admin.register(User)
class UserAdmin(BaseUserAdmin):

    form = PortalUserChangeForm
    add_form = PortalUserCreationForm

    list_display = (
        "username",
        "name",
        "role",
        "rank",
        "appointment",
        "is_active",
        "date_joined",
    )
    list_filter = (
        "role",
        "is_active",
        "rank",
    )
    search_fields = (
        "username",
        "name",
        "appointment",
        "rank__rank_name",
    )
    ordering = ("username",)
    list_select_related = ("rank",)
    autocomplete_fields = ("rank",)
    filter_horizontal = (
        "organizations",
        "groups",
        "user_permissions",
    )
    readonly_fields = (
        "date_joined",
        "last_login",
        "is_staff",
        "is_superuser",
    )
    list_per_page = 25

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "username",
                    "password",
                )
            },
        ),
        (
            "Profile",
            {
                "fields": (
                    "name",
                    "rank",
                    "appointment",
                    "organizations",
                    "photo",
                    "sign",
                )
            },
        ),
        (
            "Role",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "groups",
                    "user_permissions",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "name",
                    "role",
                    "rank",
                    "organizations",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


class SingletonProfileAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not UnitProfile.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UnitProfile)
class UnitProfileAdmin(SingletonProfileAdmin):
    fields = (
        "unit_name",
        "short_name",
        "motto",
        "location",
        "raised_on",
        "war_cry",
        "about",
        "crest",
    )


@admin.register(DashboardSlide)
class DashboardSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "display_order", "is_published")
    list_editable = ("display_order", "is_published")


@admin.register(HallOfFameCO)
class HallOfFameCOAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "rank",
        "tenure_start",
        "tenure_end",
        "is_current",
        "is_published",
        "display_order",
    )
    list_filter = ("is_current", "is_published")
    search_fields = ("name", "rank")


@admin.register(UnitAchievement)
class UnitAchievementAdmin(admin.ModelAdmin):
    list_display = ("title", "year", "display_order", "is_published")
    list_editable = ("display_order", "is_published")
    search_fields = ("title", "year")


@admin.register(UnitHighlight)
class UnitHighlightAdmin(admin.ModelAdmin):
    list_display = ("title", "icon", "display_order", "is_published")
    list_editable = ("display_order", "is_published")

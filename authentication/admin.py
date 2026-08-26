from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import User


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

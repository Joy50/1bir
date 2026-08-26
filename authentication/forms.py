from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
)
from django.contrib.auth.password_validation import validate_password

from common.models import Organization, Rank

from .models import User


# ============================================================
# Common CSS Class
# ============================================================

INPUT_CLASS = (
    "form-control"
)

SELECT_CLASS = (
    "form-select"
)


# ============================================================
# Login Form
# ============================================================

class LoginForm(AuthenticationForm):

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "e.g. officer.lastname",
                "autofocus": True,
                "autocomplete": "username",
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "••••••••",
                "autocomplete": "current-password",
            }
        )
    )


# ============================================================
# Change Password Form
# ============================================================

class ChangePasswordForm(PasswordChangeForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["old_password"].widget.attrs.update({
            "class": INPUT_CLASS,
            "placeholder": "Current password",
            "autocomplete": "current-password",
        })

        self.fields["new_password1"].widget.attrs.update({
            "class": INPUT_CLASS,
            "placeholder": "New password",
            "autocomplete": "new-password",
        })

        self.fields["new_password2"].widget.attrs.update({
            "class": INPUT_CLASS,
            "placeholder": "Confirm new password",
            "autocomplete": "new-password",
        })


# ============================================================
# Create User Form (Admin only)
# ============================================================

class UserCreateForm(forms.ModelForm):

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "Password",
                "autocomplete": "new-password",
            }
        )
    )

    password_confirm = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "Confirm password",
                "autocomplete": "new-password",
            }
        )
    )

    class Meta:
        model = User

        fields = [
            "username",
            "name",
            "rank",
            "organizations",
            "appointment",
            "role",
            "sign",
            "photo",
            "is_active",
        ]

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Username",
                    "autocomplete": "off",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Full name",
                }
            ),
            "rank": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                }
            ),
            "organizations": forms.CheckboxSelectMultiple(
                attrs={
                    "class": "org-check-list",
                }
            ),
            "appointment": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Appointment / post",
                }
            ),
            "role": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                }
            ),
            "sign": forms.ClearableFileInput(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),
            "photo": forms.ClearableFileInput(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "name": "Full Name",
            "organizations": "Organizations",
            "sign": "Signature",
            "photo": "Photo",
            "is_active": "Active",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["rank"].queryset = Rank.objects.all().order_by(
            "rank_name"
        )
        self.fields["rank"].required = False
        self.fields["organizations"].queryset = (
            Organization.objects.all().order_by("organization_name")
        )
        self.fields["organizations"].required = False
        self.fields["organizations"].help_text = (
            "A user can belong to more than one organization."
        )
        self.fields["is_active"].initial = True

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm:
            if password != password_confirm:
                raise forms.ValidationError(
                    "Passwords do not match."
                )

        if password:
            user = User(
                username=cleaned_data.get("username") or "",
                name=cleaned_data.get("name") or "",
            )
            try:
                validate_password(password, user)
            except forms.ValidationError as error:
                self.add_error("password", error)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()
            self.save_m2m()

        return user


# ============================================================
# Update User Form (Admin only)
# ============================================================

class UserUpdateForm(forms.ModelForm):

    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "Leave blank to keep current password",
                "autocomplete": "new-password",
            }
        )
    )

    password_confirm = forms.CharField(
        required=False,
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "Confirm new password",
                "autocomplete": "new-password",
            }
        )
    )

    class Meta:
        model = User

        fields = [
            "username",
            "name",
            "rank",
            "organizations",
            "appointment",
            "role",
            "sign",
            "photo",
            "is_active",
        ]

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Username",
                    "autocomplete": "off",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Full name",
                }
            ),
            "rank": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                }
            ),
            "organizations": forms.CheckboxSelectMultiple(
                attrs={
                    "class": "org-check-list",
                }
            ),
            "appointment": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Appointment / post",
                }
            ),
            "role": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                }
            ),
            "sign": forms.ClearableFileInput(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),
            "photo": forms.ClearableFileInput(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "name": "Full Name",
            "organizations": "Organizations",
            "sign": "Signature",
            "photo": "Photo",
            "is_active": "Active",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["rank"].queryset = Rank.objects.all().order_by(
            "rank_name"
        )
        self.fields["rank"].required = False
        self.fields["organizations"].queryset = (
            Organization.objects.all().order_by("organization_name")
        )
        self.fields["organizations"].required = False
        self.fields["organizations"].help_text = (
            "A user can belong to more than one organization."
        )
        self.fields["password"].help_text = (
            "Leave blank to keep the current password."
        )

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password or password_confirm:
            if password != password_confirm:
                raise forms.ValidationError(
                    "Passwords do not match."
                )

        if password:
            try:
                validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error("password", error)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")

        if password:
            user.set_password(password)

        if commit:
            user.save()
            self.save_m2m()

        return user

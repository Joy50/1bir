from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
)
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from common.activity import log_addition, log_change

from .forms import (
    ChangePasswordForm,
    LoginForm,
    UserCreateForm,
    UserUpdateForm,
)
from .models import User
from .portal import get_portal_context


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_admin

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(
                self.request,
                "Only admin accounts can access this page."
            )
            return redirect("authentication:home")

        return super().handle_no_permission()


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles = ()
    permission_message = "You do not have permission to access this page."

    def test_func(self):
        user = self.request.user
        if User.ROLE_CO in self.allowed_roles and user.is_co:
            return True
        if User.ROLE_ADMIN in self.allowed_roles and user.is_admin:
            return True
        return user.role in self.allowed_roles

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, self.permission_message)
            return redirect("authentication:home")
        return super().handle_no_permission()


class CoRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.ROLE_ADMIN, User.ROLE_CO)
    permission_message = "Only the CO or an admin can access this page."

    def test_func(self):
        return self.request.user.can_view_duty_map


class OfficerActionMixin(RoleRequiredMixin):
    allowed_roles = (User.ROLE_ADMIN, User.ROLE_OFFICER)
    permission_message = "Only officers can accept postings or complete this action."


class DutyAssignMixin(RoleRequiredMixin):
    allowed_roles = (User.ROLE_ADMIN, User.ROLE_CO, User.ROLE_OFFICER)
    permission_message = "Only officers or the CO can assign duty."


class PortalContextMixin:

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_portal_context(self.request))
        return context


# ============================================================
# Home
# ============================================================

class HomeView(PortalContextMixin, LoginRequiredMixin, TemplateView):

    template_name = "authentication/home.html"


# ============================================================
# Login
# ============================================================

class UserLoginView(LoginView):

    form_class = LoginForm
    template_name = "authentication/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(
            self.request,
            f"Welcome, {form.get_user().name}."
        )
        return super().form_valid(form)


# ============================================================
# Logout
# ============================================================

class UserLogoutView(LogoutView):

    next_page = reverse_lazy("authentication:login")

    def post(self, request, *args, **kwargs):
        was_authenticated = request.user.is_authenticated
        response = super().post(request, *args, **kwargs)

        if was_authenticated:
            messages.success(
                request,
                "You have been logged out."
            )

        return response


# ============================================================
# Change Password
# ============================================================

class ChangePasswordView(PortalContextMixin, LoginRequiredMixin, PasswordChangeView):

    form_class = ChangePasswordForm
    template_name = "authentication/change_password.html"
    success_url = reverse_lazy("authentication:home")

    def form_valid(self, form):
        messages.success(
            self.request,
            "Password changed successfully."
        )
        return super().form_valid(form)


# ============================================================
# Create User (Admin only)
# ============================================================

class CreateUserView(PortalContextMixin, AdminRequiredMixin, CreateView):

    model = User
    form_class = UserCreateForm
    template_name = "authentication/create_user.html"
    success_url = reverse_lazy("authentication:manage_users")

    def form_valid(self, form):
        response = super().form_valid(form)
        log_addition(self.request.user, self.object, "User created.")
        messages.success(
            self.request,
            f"User '{self.object.username}' created successfully."
        )
        return response


# ============================================================
# User Management (Admin only)
# ============================================================

class ManageUsersView(PortalContextMixin, AdminRequiredMixin, ListView):

    model = User
    template_name = "authentication/manage_users.html"
    context_object_name = "users"
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.select_related("rank").prefetch_related(
            "organizations"
        ).order_by("username")
        search = self.request.GET.get("q", "").strip()
        role = self.request.GET.get("role", "").strip()
        status = self.request.GET.get("status", "").strip()

        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(name__icontains=search)
                | Q(appointment__icontains=search)
                | Q(organizations__organization_name__icontains=search)
            ).distinct()

        if role in {
            User.ROLE_ADMIN,
            User.ROLE_CO,
            User.ROLE_OFFICER,
            User.ROLE_CLERK,
        }:
            queryset = queryset.filter(role=role)

        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["role_filter"] = self.request.GET.get("role", "").strip()
        context["status_filter"] = self.request.GET.get("status", "").strip()
        context["role_choices"] = User.ROLE_CHOICES
        return context


class UpdateUserView(PortalContextMixin, AdminRequiredMixin, UpdateView):

    model = User
    form_class = UserUpdateForm
    template_name = "authentication/update_user.html"
    success_url = reverse_lazy("authentication:manage_users")

    def form_valid(self, form):
        if (
            self.object.pk == self.request.user.pk
            and not form.cleaned_data.get("is_active", True)
        ):
            form.add_error(
                "is_active",
                "You cannot deactivate your own account."
            )
            return self.form_invalid(form)

        if (
            self.object.pk == self.request.user.pk
            and form.cleaned_data.get("role") != User.ROLE_ADMIN
        ):
            form.add_error(
                "role",
                "You cannot remove admin access from your own account."
            )
            return self.form_invalid(form)

        response = super().form_valid(form)
        log_change(self.request.user, self.object, "User updated.")
        messages.success(
            self.request,
            f"User '{self.object.username}' updated successfully."
        )
        return response

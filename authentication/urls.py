from django.urls import path

from . import dashboard_views, error_views, views

app_name = "authentication"

urlpatterns = [
    path(
        "",
        views.HomeView.as_view(),
        name="home",
    ),
    path(
        "login/",
        views.UserLoginView.as_view(),
        name="login",
    ),
    path(
        "logout/",
        views.UserLogoutView.as_view(),
        name="logout",
    ),
    path(
        "password/change/",
        views.ChangePasswordView.as_view(),
        name="change_password",
    ),
    path(
        "users/create/",
        views.CreateUserView.as_view(),
        name="create_user",
    ),
    path(
        "users/",
        views.ManageUsersView.as_view(),
        name="manage_users",
    ),
    path(
        "users/<int:pk>/edit/",
        views.UpdateUserView.as_view(),
        name="update_user",
    ),
    path(
        "dashboard/manage/",
        dashboard_views.DashboardManageHubView.as_view(),
        name="dashboard_manage",
    ),
    path(
        "dashboard/manage/profile/",
        dashboard_views.DashboardProfileUpdateView.as_view(),
        name="dashboard_profile",
    ),
    path(
        "dashboard/manage/<slug:kind>/",
        dashboard_views.DashboardResourceListView.as_view(),
        name="dashboard_resource_list",
    ),
    path(
        "dashboard/manage/<slug:kind>/new/",
        dashboard_views.DashboardResourceCreateView.as_view(),
        name="dashboard_resource_create",
    ),
    path(
        "dashboard/manage/<slug:kind>/<int:pk>/edit/",
        dashboard_views.DashboardResourceUpdateView.as_view(),
        name="dashboard_resource_edit",
    ),
    path(
        "dashboard/manage/<slug:kind>/<int:pk>/delete/",
        dashboard_views.DashboardResourceDeleteView.as_view(),
        name="dashboard_resource_delete",
    ),
    path(
        "errors/<int:code>/",
        error_views.preview,
        name="error_preview",
    ),
]

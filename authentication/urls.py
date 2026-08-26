from django.urls import path

from . import views

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
]

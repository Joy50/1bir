from django.urls import path

from . import views

app_name = "common"

urlpatterns = [
    path("ranks/create/", views.RankCreateView.as_view(), name="create_rank"),
    path(
        "organizations/create/",
        views.OrganizationCreateView.as_view(),
        name="create_organization",
    ),
    path("ere/", views.EREOrganizationCreateView.as_view(), name="create_ere"),
    path(
        "education-levels/create/",
        views.EducationLevelCreateView.as_view(),
        name="create_education_level",
    ),
    path("activity-log/", views.ActivityLogView.as_view(), name="activity_log"),
    path("server-monitor/", views.ServerMonitorView.as_view(), name="server_monitor"),
    path("statistics/", views.StatisticsView.as_view(), name="statistics"),
    path("search/", views.UnitSearchView.as_view(), name="search"),
    path("search/suggest/", views.UnitSearchSuggestView.as_view(), name="search_suggest"),
    path("soldiers/", views.SoldierListView.as_view(), name="soldier_list"),
    path("soldiers/create/", views.SoldierCreateView.as_view(), name="soldier_create"),
    path("soldiers/<int:pk>/", views.SoldierDetailView.as_view(), name="soldier_detail"),
    path("soldiers/<int:pk>/pdf/", views.SoldierPDFView.as_view(), name="soldier_pdf"),
    path(
        "soldiers/<int:pk>/edit/",
        views.SoldierUpdateView.as_view(),
        name="soldier_update",
    ),
    path(
        "soldiers/<int:pk>/delete/",
        views.SoldierDeleteView.as_view(),
        name="soldier_delete",
    ),
]

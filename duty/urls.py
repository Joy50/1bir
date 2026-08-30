from django.urls import path

from . import roster_views, views

app_name = "duty"

urlpatterns = [
    path("duty/", views.DutyHomeView.as_view(), name="home"),
    path("duty/roster/", roster_views.DutyRosterDailyView.as_view(), name="roster_daily"),
    path(
        "duty/roster/pdf/",
        roster_views.DutyRosterDailyPDFView.as_view(),
        name="roster_daily_pdf",
    ),
    path(
        "duty/roster/monthly/",
        roster_views.DutyRosterMonthlyView.as_view(),
        name="roster_monthly",
    ),
    path(
        "duty/roster/monthly/pdf/",
        roster_views.DutyRosterMonthlyPDFView.as_view(),
        name="roster_monthly_pdf",
    ),
    path("duty/posts/", views.DutyPostListView.as_view(), name="post_list"),
    path("duty/posts/create/", views.DutyPostCreateView.as_view(), name="post_create"),
    path("duty/posts/<int:pk>/edit/", views.DutyPostUpdateView.as_view(), name="post_edit"),
    path("duty/assign/", views.DutyAssignView.as_view(), name="assign"),
    path("duty/assign/<int:pk>/complete/", views.DutyCompleteView.as_view(), name="complete"),
    path("duty/map/", views.DutyMapView.as_view(), name="map"),
    path("duty/map/report/", views.DutyTourReportView.as_view(), name="report_tour"),
    path("parade-state/", views.ParadeStateListView.as_view(), name="parade_state_list"),
    path("parade-state/<int:pk>/", views.ParadeStateEditView.as_view(), name="parade_state_edit"),
    path("postings/", views.SoldierPostingListView.as_view(), name="posting_list"),
    path("postings/create/", views.SoldierPostingCreateView.as_view(), name="posting_create"),
    path(
        "postings/<int:pk>/decide/",
        views.SoldierPostingDecideView.as_view(),
        name="posting_decide",
    ),
]

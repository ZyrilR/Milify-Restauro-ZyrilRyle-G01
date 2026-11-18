from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("owner/", views.owner_dashboard, name="owner_dashboard"),
    path("member/", views.member_dashboard, name="member_dashboard"),
]

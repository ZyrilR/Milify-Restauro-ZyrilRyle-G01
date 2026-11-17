from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("owner/", views.owner_dashboard, name="owner_dashboard"),
    path("member/", views.member_dashboard, name="member_dashboard"),
    path("owner/create-project/", views.owner_create_project, name="owner_create_project"),
    path("member/join-project/", views.member_join_project, name="member_join_project"),
]

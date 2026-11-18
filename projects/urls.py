from django.urls import path

from . import views


urlpatterns = [
    path("owner/create-project/", views.owner_create_project, name="owner_create_project"),
    path("owner/projects/<int:pk>/", views.owner_project_detail, name="owner_project_detail"),
    path("owner/projects/<int:pk>/edit/", views.owner_edit_project, name="owner_edit_project"),
    path("owner/projects/<int:pk>/delete/", views.owner_delete_project, name="owner_delete_project"),
    path(
        "owner/projects/<int:pk>/invite-user/",
        views.owner_invite_by_username,
        name="owner_invite_by_username",
    ),
    path(
        "owner/projects/<int:pk>/generate-invite-code/",
        views.owner_generate_invite_code,
        name="owner_generate_invite_code",
    ),
    path("member/join-project/", views.member_join_project, name="member_join_project"),
    path(
        "invitations/<int:pk>/<str:response>/",
        views.respond_to_invitation,
        name="respond_to_invitation",
    ),
]

from django.urls import path

from . import views


urlpatterns = [
    path("owner/create-project/", views.owner_create_project, name="owner_create_project"),
    path("owner/projects/<int:pk>/", views.owner_project_detail, name="owner_project_detail"),
    path("owner/projects/<int:pk>/edit/", views.owner_edit_project, name="owner_edit_project"),
    path("owner/projects/<int:pk>/delete/", views.owner_delete_project, name="owner_delete_project"),
]

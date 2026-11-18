from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProjectForm
from .models import Project


@login_required
def owner_create_project(request):
    if request.user.role != request.user.Role.OWNER:
        return redirect("dashboard")

    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            messages.success(request, "Project created successfully.")
            return redirect("owner_project_detail", pk=project.pk)
    else:
        form = ProjectForm()

    return render(request, "projects/project_form.html", {"form": form})


def _owned_project(request, pk):
    if request.user.role != request.user.Role.OWNER:
        return None
    return get_object_or_404(Project, pk=pk, owner=request.user)


@login_required
def owner_project_detail(request, pk):
    project = _owned_project(request, pk)
    if project is None:
        return redirect("dashboard")
    return render(request, "projects/project_detail.html", {"project": project})


@login_required
def owner_edit_project(request, pk):
    project = _owned_project(request, pk)
    if project is None:
        return redirect("dashboard")

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, "Project updated successfully.")
            return redirect("owner_project_detail", pk=project.pk)
    else:
        form = ProjectForm(instance=project)

    return render(
        request,
        "projects/project_form.html",
        {"form": form, "project": project},
    )


@login_required
def owner_delete_project(request, pk):
    project = _owned_project(request, pk)
    if project is None:
        return redirect("dashboard")

    if request.method == "POST":
        project.delete()
        messages.success(request, "Project deleted successfully.")
        return redirect("owner_dashboard")

    return render(
        request,
        "projects/project_confirm_delete.html",
        {"project": project},
    )

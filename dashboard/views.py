from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Project, ProjectMember


@login_required
def dashboard(request):
    owns_projects = Project.objects.filter(owner=request.user).exists()
    is_member = ProjectMember.objects.filter(user=request.user).exists()

    if owns_projects and not is_member:
        return redirect("owner_dashboard")
    if is_member and not owns_projects:
        return redirect("member_dashboard")

    return render(
        request,
        "dashboard/home.html",
        {
            "owns_projects": owns_projects,
            "is_member": is_member,
        },
    )


@login_required
def owner_dashboard(request):
    projects = Project.objects.filter(owner=request.user).order_by("name")
    if not projects.exists():
        if ProjectMember.objects.filter(user=request.user).exists():
            return redirect("member_dashboard")
        return redirect("dashboard")

    return render(
        request,
        "dashboard/owner.html",
        {
            "projects": projects,
            "project_count": projects.count(),
            "is_member": ProjectMember.objects.filter(user=request.user).exists(),
        },
    )


@login_required
def member_dashboard(request):
    projects = Project.objects.filter(
        memberships__user=request.user,
    ).order_by("name")
    if not projects.exists():
        if Project.objects.filter(owner=request.user).exists():
            return redirect("owner_dashboard")
        return redirect("dashboard")

    return render(
        request,
        "dashboard/member.html",
        {
            "projects": projects,
            "owns_projects": Project.objects.filter(owner=request.user).exists(),
        },
    )

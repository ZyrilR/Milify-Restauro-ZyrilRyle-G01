from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def dashboard(request):
    if request.user.role == request.user.Role.OWNER:
        return redirect("owner_dashboard")
    return redirect("member_dashboard")


@login_required
def owner_dashboard(request):
    if request.user.role != request.user.Role.OWNER:
        return redirect("dashboard")
    return render(request, "dashboard/owner.html")


@login_required
def member_dashboard(request):
    if request.user.role != request.user.Role.MEMBER:
        return redirect("dashboard")
    return render(request, "dashboard/member.html")


@login_required
def owner_create_project(request):
    if request.user.role != request.user.Role.OWNER:
        return redirect("dashboard")
    return render(
        request,
        "dashboard/placeholder.html",
        {
            "title": "Create a project",
            "description": "Project creation is not available yet.",
            "dashboard_url": "owner_dashboard",
        },
    )


@login_required
def member_join_project(request):
    if request.user.role != request.user.Role.MEMBER:
        return redirect("dashboard")
    return render(
        request,
        "dashboard/placeholder.html",
        {
            "title": "Join a project",
            "description": "Joining a project is not available yet.",
            "dashboard_url": "member_dashboard",
        },
    )

import secrets
import string

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ProjectForm, ProjectInviteCodeForm, ProjectUsernameInviteForm
from .models import Project, ProjectInvitation, ProjectMember


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
    pending_invitations = project.invitations.filter(
        status=ProjectInvitation.Status.PENDING
    ).select_related("invitee")
    return render(
        request,
        "projects/project_detail.html",
        {
            "project": project,
            "username_invite_form": ProjectUsernameInviteForm(),
            "pending_invitations": pending_invitations,
        },
    )


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


@login_required
@require_POST
def owner_invite_by_username(request, pk):
    project = _owned_project(request, pk)
    if project is None:
        return redirect("dashboard")

    form = ProjectUsernameInviteForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a valid username.")
        return redirect("owner_project_detail", pk=project.pk)

    User = get_user_model()
    invitee = User.objects.filter(
        username__iexact=form.cleaned_data["username"]
    ).first()
    if invitee is None:
        messages.error(request, "No Milify user was found with that username.")
    elif invitee.pk == project.owner_id:
        messages.error(request, "You cannot invite yourself to your own project.")
    elif invitee.role != invitee.Role.MEMBER:
        messages.error(request, "Only member accounts can be invited to a project.")
    elif ProjectMember.objects.filter(project=project, user=invitee).exists():
        messages.error(request, "That user is already a project member.")
    elif ProjectInvitation.objects.filter(
        project=project,
        invitee=invitee,
        status=ProjectInvitation.Status.PENDING,
    ).exists():
        messages.error(request, "That user already has a pending invitation.")
    else:
        ProjectInvitation.objects.create(
            project=project,
            invited_by=request.user,
            invitee=invitee,
        )
        messages.success(
            request,
            f"Invitation sent to @{invitee.username}. They must accept it to join.",
        )

    return redirect("owner_project_detail", pk=project.pk)


@login_required
@require_POST
def owner_generate_invite_code(request, pk):
    project = _owned_project(request, pk)
    if project is None:
        return redirect("dashboard")

    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        if code != project.invite_code and not Project.objects.filter(
            invite_code=code
        ).exists():
            break

    project.invite_code = code
    project.save(update_fields=["invite_code"])
    messages.success(request, "A new six-character invite code is ready to share.")
    return redirect("owner_project_detail", pk=project.pk)


@login_required
def member_join_project(request):
    if request.user.role != request.user.Role.MEMBER:
        return redirect("dashboard")

    if request.method == "POST":
        form = ProjectInviteCodeForm(request.POST)
        if form.is_valid():
            project = Project.objects.filter(
                invite_code=form.cleaned_data["code"]
            ).select_related("owner").first()
            if project is None:
                messages.error(request, "That invite code is invalid.")
            elif project.owner_id == request.user.pk:
                messages.error(request, "You cannot join your own project.")
            elif ProjectMember.objects.filter(project=project, user=request.user).exists():
                messages.error(request, "You are already a member of that project.")
            elif ProjectInvitation.objects.filter(
                project=project,
                invitee=request.user,
                status=ProjectInvitation.Status.PENDING,
            ).exists():
                messages.error(request, "You already have a pending invitation for that project.")
            else:
                ProjectInvitation.objects.create(
                    project=project,
                    invited_by=project.owner,
                    invitee=request.user,
                )
                messages.success(
                    request,
                    f"Invitation found for {project.name}. Review and accept it below to join.",
                )
        else:
            messages.error(request, "Enter a valid six-character invite code.")
    else:
        form = ProjectInviteCodeForm()

    pending_invitations = ProjectInvitation.objects.filter(
        invitee=request.user,
        status=ProjectInvitation.Status.PENDING,
    ).select_related("project", "invited_by").order_by("-created_at")
    return render(
        request,
        "projects/member_invitations.html",
        {
            "form": form,
            "pending_invitations": pending_invitations,
        },
    )


@login_required
@require_POST
def respond_to_invitation(request, pk, response):
    if response not in ("accept", "decline"):
        return redirect("dashboard")

    with transaction.atomic():
        invitation = get_object_or_404(
            ProjectInvitation.objects.select_for_update(),
            pk=pk,
            invitee=request.user,
            status=ProjectInvitation.Status.PENDING,
        )
        if response == "accept":
            ProjectMember.objects.get_or_create(
                project=invitation.project,
                user=request.user,
            )
            invitation.status = ProjectInvitation.Status.ACCEPTED
            message = f"You joined {invitation.project.name}."
        else:
            invitation.status = ProjectInvitation.Status.DECLINED
            message = f"You declined the invitation to {invitation.project.name}."
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=["status", "responded_at"])

    messages.success(request, message)
    if response == "accept":
        return redirect("member_dashboard")
    return redirect("member_join_project")

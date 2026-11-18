from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Value
from django.db.models.functions import Trim
from django.db.models.lookups import GreaterThan


class Project(models.Model):
    project_id = models.BigAutoField(primary_key=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="owned_projects",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    invite_code = models.CharField(max_length=6, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dashboard_project"
        constraints = [
            models.CheckConstraint(
                condition=GreaterThan(Trim("name"), Value("")),
                name="project_name_not_blank",
            ),
        ]

    def clean(self):
        super().clean()
        if self.name and not self.name.strip():
            raise ValidationError({"name": "Project name cannot be blank."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProjectMember(models.Model):
    project_member_id = models.BigAutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dashboard_projectmember"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                name="unique_project_member",
            ),
        ]

    def clean(self):
        super().clean()
        if self.project_id and self.user_id and self.project.owner_id == self.user_id:
            raise ValidationError(
                {"user": "A project owner cannot also be a member of that project."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.project}"


class ProjectInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_project_invitations",
    )
    invitee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_project_invitations",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "invitee"],
                condition=models.Q(status="pending"),
                name="unique_pending_project_invitation",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["pending", "accepted", "declined"]),
                name="project_invitation_status_valid",
            ),
        ]

    def clean(self):
        super().clean()
        if self.project_id and self.invited_by_id != self.project.owner_id:
            raise ValidationError({"invited_by": "Only the project owner can invite users."})
        if self.project_id and self.invitee_id == self.project.owner_id:
            raise ValidationError({"invitee": "A project owner cannot join their own project."})
        if (
            self.status == self.Status.PENDING
            and self.project_id
            and self.invitee_id
            and ProjectMember.objects.filter(
                project_id=self.project_id,
                user_id=self.invitee_id,
            ).exists()
        ):
            raise ValidationError({"invitee": "This user is already a project member."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invitee} invited to {self.project}"

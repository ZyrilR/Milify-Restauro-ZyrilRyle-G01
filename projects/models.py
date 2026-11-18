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

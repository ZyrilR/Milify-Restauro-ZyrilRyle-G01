from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import RestrictedError
from django.test import TestCase
from django.urls import reverse

from .models import Project, ProjectMember


User = get_user_model()


class ProjectModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            full_name="Project Owner",
            role=User.Role.OWNER,
        )

    def test_project_can_be_created_with_an_existing_owner(self):
        project = Project.objects.create(owner=self.owner, name="Milify project")

        self.assertEqual(project.owner, self.owner)
        self.assertEqual(project.name, "Milify project")

    def test_project_requires_an_owner(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(name="Project without owner")

    def test_user_can_own_multiple_projects(self):
        first = Project.objects.create(owner=self.owner, name="First project")
        second = Project.objects.create(owner=self.owner, name="Second project")

        self.assertEqual(
            set(Project.objects.filter(owner=self.owner).values_list("pk", flat=True)),
            {first.pk, second.pk},
        )

    def test_project_name_cannot_be_blank_or_whitespace(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(owner=self.owner, name="   ")

    def test_deleting_project_owner_is_restricted(self):
        Project.objects.create(owner=self.owner, name="Milify project")

        with self.assertRaises(RestrictedError):
            self.owner.delete()


class ProjectMemberModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            full_name="Project Owner",
            role=User.Role.OWNER,
        )
        self.member = User.objects.create_user(
            username="member",
            email="member@example.com",
            full_name="Project Member",
            role=User.Role.MEMBER,
        )
        self.project = Project.objects.create(owner=self.owner, name="Project")

    def test_user_can_be_a_member_of_multiple_projects(self):
        another_project = Project.objects.create(owner=self.owner, name="Another project")
        ProjectMember.objects.create(project=self.project, user=self.member)
        ProjectMember.objects.create(project=another_project, user=self.member)

        self.assertEqual(self.member.project_memberships.count(), 2)

    def test_duplicate_membership_is_rejected_by_database_constraint(self):
        ProjectMember.objects.create(project=self.project, user=self.member)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProjectMember.objects.bulk_create(
                    [ProjectMember(project=self.project, user=self.member)]
                )

    def test_project_owner_cannot_be_a_member_of_the_same_project(self):
        with self.assertRaises(ValidationError):
            ProjectMember.objects.create(project=self.project, user=self.owner)

    def test_membership_does_not_change_the_users_account_role(self):
        another_owner = User.objects.create_user(
            username="another-owner",
            email="another-owner@example.com",
            full_name="Another Owner",
            role=User.Role.OWNER,
        )
        another_project = Project.objects.create(
            owner=another_owner,
            name="Another project",
        )
        ProjectMember.objects.create(project=another_project, user=self.owner)

        self.owner.refresh_from_db()
        self.assertEqual(self.owner.role, User.Role.OWNER)

    def test_deleting_project_removes_its_memberships(self):
        membership = ProjectMember.objects.create(project=self.project, user=self.member)

        self.project.delete()

        self.assertFalse(ProjectMember.objects.filter(pk=membership.pk).exists())

    def test_deleting_member_removes_their_memberships(self):
        membership = ProjectMember.objects.create(project=self.project, user=self.member)

        self.member.delete()

        self.assertFalse(ProjectMember.objects.filter(pk=membership.pk).exists())


class ProjectCRUDTests(TestCase):
    def setUp(self):
        self.password = "MilifySafePass!42"
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            full_name="Project Owner",
            password=self.password,
            role=User.Role.OWNER,
        )
        self.other_owner = User.objects.create_user(
            username="other-owner",
            email="other-owner@example.com",
            full_name="Other Owner",
            password=self.password,
            role=User.Role.OWNER,
        )
        self.member = User.objects.create_user(
            username="member",
            email="member@example.com",
            full_name="Project Member",
            password=self.password,
            role=User.Role.MEMBER,
        )

    def test_owner_can_create_project(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("owner_create_project"),
            {"name": "Milify Website", "description": "A project workspace"},
        )

        project = Project.objects.get(name="Milify Website")
        self.assertEqual(project.owner, self.owner)
        self.assertRedirects(
            response,
            reverse("owner_project_detail", args=[project.pk]),
        )

    def test_blank_project_name_shows_validation_error(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("owner_create_project"),
            {"name": "   ", "description": "No valid name"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Project name cannot be blank.")
        self.assertFalse(Project.objects.exists())

    def test_owner_dashboard_lists_only_owned_projects(self):
        owned = Project.objects.create(owner=self.owner, name="Owned project")
        Project.objects.create(owner=self.other_owner, name="Other project")
        self.client.force_login(self.owner)

        response = self.client.get(reverse("owner_dashboard"))

        self.assertContains(response, owned.name)
        self.assertNotContains(response, "Other project")

    def test_owner_can_view_edit_and_delete_owned_project(self):
        project = Project.objects.create(
            owner=self.owner,
            name="Original name",
            description="Original description",
        )
        self.client.force_login(self.owner)

        detail = self.client.get(reverse("owner_project_detail", args=[project.pk]))
        self.assertContains(detail, "Original name")

        edit = self.client.post(
            reverse("owner_edit_project", args=[project.pk]),
            {"name": "Updated name", "description": "Updated description"},
        )
        self.assertRedirects(
            edit,
            reverse("owner_project_detail", args=[project.pk]),
        )
        project.refresh_from_db()
        self.assertEqual(project.name, "Updated name")

        delete = self.client.post(
            reverse("owner_delete_project", args=[project.pk]),
        )
        self.assertRedirects(delete, reverse("owner_dashboard"))
        self.assertFalse(Project.objects.filter(pk=project.pk).exists())

    def test_owner_cannot_open_another_owner_project(self):
        project = Project.objects.create(owner=self.other_owner, name="Private project")
        self.client.force_login(self.owner)

        for route in (
            "owner_project_detail",
            "owner_edit_project",
            "owner_delete_project",
        ):
            response = self.client.get(reverse(route, args=[project.pk]))
            self.assertEqual(response.status_code, 404)

    def test_member_cannot_open_owner_project_routes(self):
        project = Project.objects.create(owner=self.owner, name="Owner project")
        self.client.force_login(self.member)

        for route in (
            "owner_project_detail",
            "owner_edit_project",
            "owner_delete_project",
        ):
            response = self.client.get(reverse(route, args=[project.pk]))
            self.assertRedirects(
                response,
                reverse("dashboard"),
                fetch_redirect_response=False,
            )

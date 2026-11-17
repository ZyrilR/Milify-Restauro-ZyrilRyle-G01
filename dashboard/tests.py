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


class DashboardRoleTests(TestCase):
    def setUp(self):
        self.password = "MilifySafePass!42"
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            full_name="Project Owner",
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

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('dashboard')}",
            fetch_redirect_response=False,
        )

    def test_dashboard_routes_each_account_to_its_role(self):
        for user, route in (
            (self.owner, "owner_dashboard"),
            (self.member, "member_dashboard"),
        ):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                response = self.client.get(reverse("dashboard"))
                self.assertRedirects(response, reverse(route))

    def test_each_role_dashboard_shows_its_own_action(self):
        self.client.force_login(self.owner)
        owner_response = self.client.get(reverse("owner_dashboard"))
        self.assertContains(owner_response, "Create project")
        self.assertNotContains(owner_response, "Join project")

        self.client.force_login(self.member)
        member_response = self.client.get(reverse("member_dashboard"))
        self.assertContains(member_response, "Join project")
        self.assertNotContains(member_response, "Create project")

    def test_user_cannot_open_another_roles_dashboard_by_url(self):
        self.client.force_login(self.member)
        self.assertRedirects(
            self.client.get(reverse("owner_dashboard")),
            reverse("dashboard"),
            fetch_redirect_response=False,
        )

        self.client.force_login(self.owner)
        self.assertRedirects(
            self.client.get(reverse("member_dashboard")),
            reverse("dashboard"),
            fetch_redirect_response=False,
        )

    def test_role_specific_placeholder_pages_are_protected(self):
        self.client.force_login(self.owner)
        self.assertContains(
            self.client.get(reverse("owner_create_project")),
            "Project creation is not available yet.",
        )
        self.assertRedirects(
            self.client.get(reverse("member_join_project")),
            reverse("dashboard"),
            fetch_redirect_response=False,
        )

        self.client.force_login(self.member)
        self.assertContains(
            self.client.get(reverse("member_join_project")),
            "Joining a project is not available yet.",
        )
        self.assertRedirects(
            self.client.get(reverse("owner_create_project")),
            reverse("dashboard"),
            fetch_redirect_response=False,
        )

    def test_navigation_displays_role_badge_and_matching_action(self):
        self.client.force_login(self.owner)
        owner_response = self.client.get(reverse("owner_dashboard"))
        self.assertContains(owner_response, "Owner")
        self.assertContains(owner_response, reverse("owner_create_project"))

        self.client.force_login(self.member)
        member_response = self.client.get(reverse("member_dashboard"))
        self.assertContains(member_response, "Member")
        self.assertContains(member_response, reverse("member_join_project"))

    def test_login_redirects_to_the_selected_role_dashboard(self):
        for user, route in (
            (self.owner, "owner_dashboard"),
            (self.member, "member_dashboard"),
        ):
            with self.subTest(role=user.role):
                response = self.client.post(
                    reverse("login"),
                    {"username": user.username, "password": self.password},
                    follow=True,
                )
                self.assertRedirects(response, reverse(route))

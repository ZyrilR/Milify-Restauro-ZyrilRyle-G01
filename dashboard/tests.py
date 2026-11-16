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
        )

    def create_project(self, owner=None, name="Milify project"):
        return Project.objects.create(
            owner=owner or self.owner,
            name=name,
        )

    def test_project_can_be_created_with_an_existing_owner(self):
        project = self.create_project()

        self.assertEqual(project.owner, self.owner)
        self.assertEqual(project.name, "Milify project")

    def test_project_requires_an_owner(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(name="Project without owner")

    def test_user_can_own_multiple_projects(self):
        first_project = self.create_project(name="First project")
        second_project = self.create_project(name="Second project")

        self.assertEqual(
            set(Project.objects.filter(owner=self.owner).values_list("pk", flat=True)),
            {first_project.pk, second_project.pk},
        )

    def test_project_name_cannot_be_blank_or_whitespace(self):
        with self.assertRaises(ValidationError):
            self.create_project(name="   ")

    def test_deleting_project_owner_is_restricted(self):
        self.create_project()

        with self.assertRaises(RestrictedError):
            self.owner.delete()


class ProjectMemberModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            full_name="Project Owner",
        )
        self.member = User.objects.create_user(
            username="member",
            email="member@example.com",
            full_name="Project Member",
        )
        self.first_project = Project.objects.create(
            owner=self.owner,
            name="First project",
        )
        self.second_project = Project.objects.create(
            owner=self.owner,
            name="Second project",
        )

    def test_user_can_be_a_member_of_multiple_projects(self):
        first_membership = ProjectMember.objects.create(
            project=self.first_project,
            user=self.member,
        )
        second_membership = ProjectMember.objects.create(
            project=self.second_project,
            user=self.member,
        )

        self.assertEqual(first_membership.user, self.member)
        self.assertEqual(second_membership.user, self.member)
        self.assertEqual(self.member.project_memberships.count(), 2)

    def test_duplicate_membership_is_rejected_by_database_constraint(self):
        ProjectMember.objects.create(project=self.first_project, user=self.member)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProjectMember.objects.bulk_create(
                    [ProjectMember(project=self.first_project, user=self.member)]
                )

    def test_project_owner_cannot_be_a_member_of_the_same_project(self):
        with self.assertRaises(ValidationError):
            ProjectMember.objects.create(
                project=self.first_project,
                user=self.owner,
            )

    def test_user_can_own_one_project_and_be_member_of_another(self):
        other_owner = User.objects.create_user(
            username="other-owner",
            email="other-owner@example.com",
            full_name="Other Owner",
        )
        other_project = Project.objects.create(
            owner=other_owner,
            name="Other project",
        )
        membership = ProjectMember.objects.create(
            project=other_project,
            user=self.owner,
        )

        self.assertEqual(membership.user, self.owner)
        self.assertEqual(self.first_project.owner, self.owner)

    def test_deleting_project_removes_its_memberships(self):
        membership = ProjectMember.objects.create(
            project=self.first_project,
            user=self.member,
        )

        self.first_project.delete()

        self.assertFalse(
            ProjectMember.objects.filter(pk=membership.pk).exists()
        )

    def test_deleting_member_removes_their_memberships(self):
        membership = ProjectMember.objects.create(
            project=self.first_project,
            user=self.member,
        )

        self.member.delete()

        self.assertFalse(
            ProjectMember.objects.filter(pk=membership.pk).exists()
        )


class DashboardViewTests(TestCase):
    def setUp(self):
        self.password = "MilifySafePass!42"
        self.user = User.objects.create_user(
            username="dashboard-user",
            email="dashboard@example.com",
            full_name="Dashboard User",
            password=self.password,
        )
        self.other_user = User.objects.create_user(
            username="other-user",
            email="other@example.com",
            full_name="Other User",
        )
        self.member_user = User.objects.create_user(
            username="member-user",
            email="member-user@example.com",
            full_name="Member User",
            password=self.password,
        )
        self.owner_project = Project.objects.create(
            owner=self.user,
            name="Owned project",
            description="A project owned by this user.",
        )
        self.member_project = Project.objects.create(
            owner=self.other_user,
            name="Member project",
            description="A project joined by this user.",
        )

    def test_main_dashboard_requires_authentication(self):
        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('dashboard')}",
            fetch_redirect_response=False,
        )

    def test_owner_only_user_is_redirected_to_owner_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(response, reverse("owner_dashboard"))

    def test_member_only_user_is_redirected_to_member_dashboard(self):
        ProjectMember.objects.create(
            project=self.member_project,
            user=self.member_user,
        )
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(response, reverse("member_dashboard"))

    def test_user_with_both_roles_can_access_both_dashboards(self):
        ProjectMember.objects.create(project=self.member_project, user=self.user)
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("owner_dashboard"))
        self.assertContains(response, reverse("member_dashboard"))
        self.assertEqual(
            self.client.get(reverse("owner_dashboard")).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("member_dashboard")).status_code,
            200,
        )

    def test_user_without_projects_sees_empty_state(self):
        self.owner_project.delete()
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You have not created or joined any projects yet.")

    def test_newly_registered_user_has_no_project_role(self):
        response = self.client.post(
            reverse("register"),
            {
                "full_name": "New Dashboard User",
                "username": "new-dashboard-user",
                "email": "new-dashboard@example.com",
                "password1": self.password,
                "password2": self.password,
            },
        )

        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username="new-dashboard-user")
        self.assertFalse(Project.objects.filter(owner=new_user).exists())
        self.assertFalse(ProjectMember.objects.filter(user=new_user).exists())
        self.client.force_login(new_user)
        dashboard_response = self.client.get(reverse("dashboard"))
        self.assertContains(
            dashboard_response,
            "You have not created or joined any projects yet.",
        )

    def test_owner_dashboard_requires_authentication(self):
        response = self.client.get(reverse("owner_dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_member_dashboard_requires_authentication(self):
        response = self.client.get(reverse("member_dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_member_cannot_open_owner_dashboard_by_url(self):
        ProjectMember.objects.create(
            project=self.member_project,
            user=self.member_user,
        )
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("owner_dashboard"))

        self.assertRedirects(response, reverse("member_dashboard"))

    def test_owner_cannot_open_member_dashboard_by_url(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("member_dashboard"))

        self.assertRedirects(response, reverse("owner_dashboard"))

    def test_owner_dashboard_only_shows_owned_projects(self):
        other_project = Project.objects.create(
            owner=self.other_user,
            name="Not owned by dashboard user",
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("owner_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.owner_project.name)
        self.assertNotContains(response, self.member_project.name)
        self.assertNotContains(response, other_project.name)
        self.assertEqual(response.context["project_count"], 1)

    def test_member_dashboard_only_shows_joined_projects(self):
        unrelated_owner = User.objects.create_user(
            username="unrelated-owner",
            email="unrelated-owner@example.com",
            full_name="Unrelated Owner",
        )
        unrelated_project = Project.objects.create(
            owner=unrelated_owner,
            name="Unrelated project",
        )
        ProjectMember.objects.create(
            project=self.member_project,
            user=self.member_user,
        )
        self.client.force_login(self.member_user)

        response = self.client.get(reverse("member_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.member_project.name)
        self.assertNotContains(response, self.owner_project.name)
        self.assertNotContains(response, unrelated_project.name)

    def test_login_redirects_through_main_dashboard_to_owner_dashboard(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": self.password},
            follow=True,
        )

        self.assertRedirects(response, reverse("owner_dashboard"))

    def test_login_redirects_through_main_dashboard_to_member_dashboard(self):
        ProjectMember.objects.create(
            project=self.member_project,
            user=self.member_user,
        )

        response = self.client.post(
            reverse("login"),
            {"username": self.member_user.username, "password": self.password},
            follow=True,
        )

        self.assertRedirects(response, reverse("member_dashboard"))

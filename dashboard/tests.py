from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


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

    def test_role_specific_actions_are_protected(self):
        self.client.force_login(self.owner)
        self.assertContains(
            self.client.get(reverse("owner_create_project")),
            "Create project",
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

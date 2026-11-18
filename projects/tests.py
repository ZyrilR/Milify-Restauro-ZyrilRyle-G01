from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import RestrictedError
from django.test import TestCase
from django.urls import reverse

from .models import Project, ProjectInvitation, ProjectMember


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


class ProjectInvitationModelTests(TestCase):
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

    def test_only_project_owner_can_send_invitation(self):
        with self.assertRaises(ValidationError):
            ProjectInvitation.objects.create(
                project=self.project,
                invited_by=self.member,
                invitee=self.member,
            )

    def test_existing_member_cannot_receive_another_invitation(self):
        ProjectMember.objects.create(project=self.project, user=self.member)

        with self.assertRaises(ValidationError):
            ProjectInvitation.objects.create(
                project=self.project,
                invited_by=self.owner,
                invitee=self.member,
            )


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

    def test_member_dashboard_lists_only_joined_projects(self):
        joined_project = Project.objects.create(owner=self.owner, name="Joined project")
        ProjectMember.objects.create(project=joined_project, user=self.member)
        Project.objects.create(owner=self.other_owner, name="Not joined project")
        self.client.force_login(self.member)

        response = self.client.get(reverse("member_dashboard"))

        self.assertContains(response, joined_project.name)
        self.assertNotContains(response, "Not joined project")
        self.assertContains(response, "Owner: Project Owner")


class ProjectInvitationFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            full_name="Project Owner",
            password="MilifySafePass!42",
            role=User.Role.OWNER,
        )
        self.member = User.objects.create_user(
            username="member",
            email="member@example.com",
            full_name="Project Member",
            password="MilifySafePass!42",
            role=User.Role.MEMBER,
        )
        self.project = Project.objects.create(
            owner=self.owner,
            name="Invitation project",
        )

    def test_owner_can_invite_existing_member_by_username(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("owner_invite_by_username", args=[self.project.pk]),
            {"username": "@member"},
            follow=True,
        )

        invitation = ProjectInvitation.objects.get(
            project=self.project,
            invitee=self.member,
        )
        self.assertEqual(invitation.status, ProjectInvitation.Status.PENDING)
        self.assertEqual(invitation.invited_by, self.owner)
        self.assertFalse(
            ProjectMember.objects.filter(project=self.project, user=self.member).exists()
        )
        self.assertContains(response, "Invitation sent to @member")

    def test_inviting_unknown_username_shows_error(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("owner_invite_by_username", args=[self.project.pk]),
            {"username": "@missing"},
            follow=True,
        )

        self.assertContains(response, "No Milify user was found with that username.")
        self.assertFalse(ProjectInvitation.objects.exists())

    def test_duplicate_pending_invitation_is_not_created(self):
        ProjectInvitation.objects.create(
            project=self.project,
            invited_by=self.owner,
            invitee=self.member,
        )
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("owner_invite_by_username", args=[self.project.pk]),
            {"username": "member"},
            follow=True,
        )

        self.assertContains(response, "already has a pending invitation")
        self.assertEqual(ProjectInvitation.objects.count(), 1)

    def test_owner_can_generate_six_character_invite_code(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("owner_generate_invite_code", args=[self.project.pk]),
        )

        self.project.refresh_from_db()
        original_code = self.project.invite_code
        self.assertRegex(original_code, r"^[A-Z0-9]{6}$")
        self.client.post(
            reverse("owner_generate_invite_code", args=[self.project.pk]),
        )
        self.project.refresh_from_db()
        self.assertRegex(self.project.invite_code, r"^[A-Z0-9]{6}$")
        self.assertNotEqual(self.project.invite_code, original_code)
        self.assertRedirects(
            response,
            reverse("owner_project_detail", args=[self.project.pk]),
        )

    def test_code_submission_creates_pending_invitation_only(self):
        self.project.invite_code = "AB12CD"
        self.project.save()
        self.client.force_login(self.member)

        response = self.client.post(
            reverse("member_join_project"),
            {"code": "ab12cd"},
            follow=True,
        )

        invitation = ProjectInvitation.objects.get(
            project=self.project,
            invitee=self.member,
        )
        self.assertEqual(invitation.status, ProjectInvitation.Status.PENDING)
        self.assertFalse(
            ProjectMember.objects.filter(project=self.project, user=self.member).exists()
        )
        self.assertContains(response, "Review and accept it below to join")

    def test_accepting_invitation_creates_membership(self):
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            invited_by=self.owner,
            invitee=self.member,
        )
        self.client.force_login(self.member)

        response = self.client.post(
            reverse(
                "respond_to_invitation",
                args=[invitation.pk, "accept"],
            ),
        )

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitation.Status.ACCEPTED)
        self.assertIsNotNone(invitation.responded_at)
        self.assertTrue(
            ProjectMember.objects.filter(project=self.project, user=self.member).exists()
        )
        self.assertRedirects(response, reverse("member_dashboard"))
        dashboard = self.client.get(response.url)
        self.assertContains(dashboard, self.project.name)
        self.assertContains(dashboard, "Projects you’ve joined")

    def test_declining_invitation_does_not_create_membership(self):
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            invited_by=self.owner,
            invitee=self.member,
        )
        self.client.force_login(self.member)

        self.client.post(
            reverse(
                "respond_to_invitation",
                args=[invitation.pk, "decline"],
            ),
        )

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitation.Status.DECLINED)
        self.assertIsNotNone(invitation.responded_at)
        self.assertFalse(
            ProjectMember.objects.filter(project=self.project, user=self.member).exists()
        )

    def test_other_user_cannot_respond_to_invitation(self):
        other_member = User.objects.create_user(
            username="other-member",
            email="other@example.com",
            full_name="Other Member",
            role=User.Role.MEMBER,
        )
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            invited_by=self.owner,
            invitee=self.member,
        )
        self.client.force_login(other_member)

        response = self.client.post(
            reverse(
                "respond_to_invitation",
                args=[invitation.pk, "accept"],
            ),
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            ProjectMember.objects.filter(
                project=self.project,
                user__in=[self.member, other_member],
            ).exists()
        )

    def test_invite_endpoints_require_project_owner(self):
        self.client.force_login(self.member)

        for route in ("owner_invite_by_username", "owner_generate_invite_code"):
            response = self.client.post(
                reverse(route, args=[self.project.pk]),
            )
            self.assertRedirects(
                response,
                reverse("dashboard"),
                fetch_redirect_response=False,
            )

    def test_invalid_code_shows_error(self):
        self.client.force_login(self.member)

        response = self.client.post(
            reverse("member_join_project"),
            {"code": "BAD123"},
            follow=True,
        )

        self.assertContains(response, "That invite code is invalid.")
        self.assertFalse(ProjectInvitation.objects.exists())

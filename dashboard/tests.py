from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import RestrictedError
from django.test import TestCase

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

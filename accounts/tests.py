from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .forms import CustomUserCreationForm


User = get_user_model()


class RegistrationTests(TestCase):
    def setUp(self):
        self.url = reverse("register")
        self.password = "MilifySafePass!42"

    def registration_data(self, **overrides):
        data = {
            "full_name": "New User",
            "username": "newuser",
            "email": "newuser@example.com",
            "role": User.Role.MEMBER,
            "password1": self.password,
            "password2": self.password,
        }
        data.update(overrides)
        return data

    def test_registration_page_is_available(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/register.html")
        self.assertIsInstance(response.context["form"], CustomUserCreationForm)
        self.assertContains(response, "Choose your role")

    def test_valid_registration_creates_user_with_hashed_password(self):
        response = self.client.post(
            self.url,
            self.registration_data(),
            follow=True,
        )

        self.assertRedirects(response, self.url)
        self.assertContains(response, "Your account has been created successfully.")
        user = User.objects.get(username="newuser")
        self.assertEqual(user.full_name, "New User")
        self.assertEqual(user.email, "newuser@example.com")
        self.assertEqual(user.role, User.Role.MEMBER)
        self.assertNotEqual(user.password, self.password)
        self.assertTrue(user.check_password(self.password))

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password=self.password,
            full_name="Existing User",
        )

        response = self.client.post(
            self.url,
            self.registration_data(username="existing"),
        )

        self.assertFormError(
            response.context["form"],
            "username",
            "A user with that username already exists.",
        )
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password=self.password,
            full_name="Existing User",
        )

        response = self.client.post(
            self.url,
            self.registration_data(email="existing@example.com"),
        )

        self.assertFormError(
            response.context["form"],
            "email",
            "An account with this email address already exists.",
        )
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_email_is_rejected(self):
        response = self.client.post(
            self.url,
            self.registration_data(email="not-an-email"),
        )

        self.assertFormError(response.context["form"], "email", "Enter a valid email address.")
        self.assertEqual(User.objects.count(), 0)

    def test_invalid_registration_preserves_non_password_fields(self):
        response = self.client.post(
            self.url,
            self.registration_data(email="not-an-email"),
        )

        self.assertContains(response, 'value="New User"')
        self.assertContains(response, 'value="newuser"')
        self.assertContains(response, 'value="not-an-email"')
        self.assertNotContains(response, self.password)

    def test_password_mismatch_is_rejected(self):
        response = self.client.post(
            self.url,
            self.registration_data(password2="AnotherSafePass!42"),
        )

        self.assertFormError(
            response.context["form"],
            "password2",
            "The two password fields didn’t match.",
        )
        self.assertNotContains(response, self.password)
        self.assertEqual(User.objects.count(), 0)

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            self.url,
            self.registration_data(password1="password", password2="password"),
        )

        self.assertIn("password2", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 0)

    def test_missing_fields_are_rejected(self):
        response = self.client.post(self.url, {})
        form = response.context["form"]

        for field in ("full_name", "username", "email", "role", "password1", "password2"):
            self.assertFormError(form, field, "This field is required.")
        self.assertEqual(User.objects.count(), 0)

    def test_registration_saves_the_selected_owner_role(self):
        response = self.client.post(
            self.url,
            self.registration_data(role=User.Role.OWNER),
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(
            User.objects.get(username="newuser").role,
            User.Role.OWNER,
        )

    def test_registration_rejects_an_unknown_role(self):
        response = self.client.post(
            self.url,
            self.registration_data(role="admin"),
        )

        self.assertIn("Select a valid choice.", response.context["form"].errors["role"][0])
        self.assertFalse(User.objects.filter(username="newuser").exists())


class AuthenticationTests(TestCase):
    def setUp(self):
        self.login_url = reverse("login")
        self.password = "MilifySafePass!42"
        self.user = User.objects.create_user(
            username="existing",
            password=self.password,
            email="existing@example.com",
            full_name="Existing User",
        )

    def test_accounts_root_redirects_to_login(self):
        response = self.client.get("/accounts/", follow=True)

        self.assertRedirects(response, self.login_url)

    def test_accounts_root_without_trailing_slash_redirects_to_login(self):
        response = self.client.get("/accounts", follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(
            response,
            self.login_url,
            status_code=301,
            target_status_code=200,
        )

    def test_login_page_has_username_and_password_fields(self):
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_valid_login_redirects_to_main_dashboard(self):
        response = self.client.post(
            self.login_url,
            {"username": self.user.username, "password": self.password},
        )

        self.assertRedirects(
            response,
            reverse("dashboard"),
            fetch_redirect_response=False,
        )
        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(self.user.pk),
        )

    def test_invalid_login_displays_error(self):
        response = self.client.post(
            self.login_url,
            {"username": self.user.username, "password": "incorrect"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_preserves_requested_destination(self):
        destination = reverse("admin:index")
        response = self.client.post(
            f"{self.login_url}?next={destination}",
            {"username": self.user.username, "password": self.password},
        )

        self.assertRedirects(response, destination, fetch_redirect_response=False)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_login_rejects_unsafe_requested_destination(self):
        response = self.client.post(
            f"{self.login_url}?next=https://example.com/",
            {"username": self.user.username, "password": self.password},
        )

        self.assertRedirects(
            response,
            reverse("dashboard"),
            fetch_redirect_response=False,
        )

    def test_logout_terminates_session_and_displays_confirmation(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("logout"), follow=True)

        self.assertRedirects(response, self.login_url)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "You have been logged out successfully.")

    def test_admin_requires_authentication(self):
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            f"{reverse('admin:login')}?next={reverse('admin:index')}",
        )


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile-user",
            email="profile@example.com",
            full_name="Profile User",
            password="MilifySafePass!42",
        )
        self.other_user = User.objects.create_user(
            username="other-profile-user",
            email="other-profile@example.com",
            full_name="Other Profile User",
        )
        self.url = reverse("profile")
        self.password_url = reverse("change_password")

    def test_profile_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_user_can_view_their_own_profile(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile.html")
        self.assertContains(response, self.user.full_name)
        self.assertContains(response, self.user.username)
        self.assertContains(response, self.user.email)
        self.assertContains(response, self.user.get_role_display())
        self.assertNotContains(response, self.other_user.email)
        self.assertEqual(response.context["form"].instance, self.user)
        self.assertEqual(list(response.context["form"].fields), ["full_name", "email"])
        self.assertNotIn("role", response.context["form"].fields)
        self.assertContains(response, f'href="{self.url}">Profile</a>')
        self.assertContains(response, f'href="{self.password_url}">Change password</a>')

    def test_change_password_page_requires_authentication(self):
        response = self.client.get(self.password_url)

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={self.password_url}",
            fetch_redirect_response=False,
        )

    def test_user_can_open_change_password_page(self):
        self.client.force_login(self.user)

        response = self.client.get(self.password_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/change_password.html")
        self.assertContains(response, 'name="old_password"')
        self.assertContains(response, 'name="new_password1"')
        self.assertContains(response, 'name="new_password2"')

    def test_user_can_update_their_own_profile(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            {
                "full_name": "Updated Profile User",
                "email": "updated-profile@example.com",
            },
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.other_user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Profile User")
        self.assertEqual(self.user.email, "updated-profile@example.com")
        self.assertEqual(self.user.username, "profile-user")
        self.assertEqual(self.other_user.full_name, "Other Profile User")
        self.assertEqual(self.other_user.email, "other-profile@example.com")

    def test_profile_cannot_change_the_account_role(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            {
                "full_name": "Updated Profile User",
                "email": self.user.email,
                "role": User.Role.OWNER,
            },
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.MEMBER)

    def test_database_rejects_roles_outside_the_defined_choices(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.filter(pk=self.user.pk).update(role="admin")

    def test_user_can_change_password_with_their_current_password(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.password_url,
            {
                "old_password": "MilifySafePass!42",
                "new_password1": "NewMilifySafePass!43",
                "new_password2": "NewMilifySafePass!43",
            },
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewMilifySafePass!43"))
        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(self.user.pk),
        )

    def test_password_change_rejects_an_incorrect_current_password(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.password_url,
            {
                "old_password": "IncorrectCurrentPassword!42",
                "new_password1": "NewMilifySafePass!43",
                "new_password2": "NewMilifySafePass!43",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "old_password",
            "Your old password was entered incorrectly. Please enter it again.",
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("MilifySafePass!42"))

    def test_password_change_rejects_mismatched_confirmation(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.password_url,
            {
                "old_password": "MilifySafePass!42",
                "new_password1": "NewMilifySafePass!43",
                "new_password2": "DifferentMilifyPass!44",
            },
        )

        self.assertFormError(
            response.context["form"],
            "new_password2",
            "The two password fields didn’t match.",
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("MilifySafePass!42"))

    def test_profile_accepts_the_users_existing_email(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            {
                "full_name": "Updated Profile User",
                "email": self.user.email,
            },
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Profile User")
        self.assertEqual(self.user.email, "profile@example.com")

    def test_profile_rejects_missing_required_fields(self):
        self.client.force_login(self.user)

        response = self.client.post(self.url, {"full_name": "", "email": ""})

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "full_name", "This field is required.")
        self.assertFormError(response.context["form"], "email", "This field is required.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Profile User")
        self.assertEqual(self.user.email, "profile@example.com")

    def test_profile_rejects_invalid_email(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            {"full_name": "Updated Profile User", "email": "not-an-email"},
        )

        self.assertFormError(
            response.context["form"],
            "email",
            "Enter a valid email address.",
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Profile User")
        self.assertEqual(self.user.email, "profile@example.com")

    def test_profile_rejects_another_users_email(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            {
                "full_name": "Updated Profile User",
                "email": self.other_user.email,
            },
        )

        self.assertFormError(
            response.context["form"],
            "email",
            "An account with this email address already exists.",
        )
        self.user.refresh_from_db()
        self.other_user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Profile User")
        self.assertEqual(self.user.email, "profile@example.com")
        self.assertEqual(self.other_user.email, "other-profile@example.com")

    def test_url_and_submitted_identifiers_cannot_target_another_user(self):
        self.client.force_login(self.user)

        response = self.client.get(f"{self.url}?user_id={self.other_user.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].instance, self.user)
        self.assertEqual(
            self.client.get(f"{self.url}{self.other_user.pk}/").status_code,
            404,
        )

        response = self.client.post(
            f"{self.url}?user_id={self.other_user.pk}",
            {
                "user_id": self.other_user.pk,
                "username": self.other_user.username,
                "is_staff": "on",
                "full_name": "Still the authenticated user",
                "email": "still-self@example.com",
            },
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.other_user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Still the authenticated user")
        self.assertEqual(self.user.email, "still-self@example.com")
        self.assertEqual(self.user.username, "profile-user")
        self.assertFalse(self.user.is_staff)
        self.assertEqual(self.other_user.full_name, "Other Profile User")
        self.assertEqual(self.other_user.email, "other-profile@example.com")
        self.assertEqual(self.other_user.username, "other-profile-user")

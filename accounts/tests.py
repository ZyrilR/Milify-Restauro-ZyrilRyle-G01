from django.contrib.auth import get_user_model
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

        for field in ("full_name", "username", "email", "password1", "password2"):
            self.assertFormError(form, field, "This field is required.")
        self.assertEqual(User.objects.count(), 0)

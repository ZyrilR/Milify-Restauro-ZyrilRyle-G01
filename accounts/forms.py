from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import CustomUser


class MilifyAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Please enter a correct username and password.",
    }


class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[("", "Choose your role"), *CustomUser.Role.choices],
        help_text="Choose one role for your account. This cannot be changed later.",
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("full_name", "username", "email", "role")
        error_messages = {
            "email": {
                "unique": "An account with this email address already exists.",
            },
        }


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("full_name", "email")
        error_messages = {
            "email": {
                "unique": "An account with this email address already exists.",
            },
        }

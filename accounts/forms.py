from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import CustomUser


class MilifyAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Please enter a correct username and password.",
    }


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("full_name", "username", "email")
        error_messages = {
            "email": {
                "unique": "An account with this email address already exists.",
            },
        }

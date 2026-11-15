from django.contrib.auth.forms import UserCreationForm

from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("full_name", "username", "email")
        error_messages = {
            "email": {
                "unique": "An account with this email address already exists.",
            },
        }

from django import forms

from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "description")
        error_messages = {
            "name": {
                "required": "Project name cannot be blank.",
            },
        }
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "e.g. Mobile App Redesign",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Describe the project...",
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Project name cannot be blank.")
        return name


class ProjectUsernameInviteForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Username",
        help_text="Enter the member's username, with or without @.",
    )

    def clean_username(self):
        return self.cleaned_data["username"].strip().removeprefix("@").strip()


class ProjectInviteCodeForm(forms.Form):
    code = forms.CharField(
        min_length=6,
        max_length=6,
        label="Invite code",
    )

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()

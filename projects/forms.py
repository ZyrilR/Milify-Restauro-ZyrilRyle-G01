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

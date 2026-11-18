import django.db.models.deletion
import django.db.models.functions.text
import django.db.models.lookups
from django.conf import settings
from django.db import migrations, models


def move_project_content_types(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    database = schema_editor.connection.alias

    for model in ("project", "projectmember"):
        ContentType.objects.using(database).filter(
            app_label="dashboard",
            model=model,
        ).update(app_label="projects")


def restore_project_content_types(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    database = schema_editor.connection.alias

    for model in ("project", "projectmember"):
        ContentType.objects.using(database).filter(
            app_label="projects",
            model=model,
        ).update(app_label="dashboard")


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0002_customuser_role"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("dashboard", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Project",
                    fields=[
                        ("project_id", models.BigAutoField(primary_key=True, serialize=False)),
                        ("name", models.CharField(max_length=150)),
                        ("description", models.TextField(blank=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        (
                            "owner",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.RESTRICT,
                                related_name="owned_projects",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "db_table": "dashboard_project",
                        "constraints": [
                            models.CheckConstraint(
                                condition=django.db.models.lookups.GreaterThan(
                                    django.db.models.functions.text.Trim("name"),
                                    models.Value(""),
                                ),
                                name="project_name_not_blank",
                            ),
                        ],
                    },
                ),
                migrations.CreateModel(
                    name="ProjectMember",
                    fields=[
                        ("project_member_id", models.BigAutoField(primary_key=True, serialize=False)),
                        ("joined_at", models.DateTimeField(auto_now_add=True)),
                        (
                            "project",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="memberships",
                                to="projects.project",
                            ),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="project_memberships",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "db_table": "dashboard_projectmember",
                        "constraints": [
                            models.UniqueConstraint(
                                fields=("project", "user"),
                                name="unique_project_member",
                            ),
                        ],
                    },
                ),
            ],
        ),
        migrations.RunPython(
            move_project_content_types,
            restore_project_content_types,
        ),
    ]

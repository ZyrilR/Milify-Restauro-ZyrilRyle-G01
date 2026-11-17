from django.db import migrations, models


def assign_existing_roles(apps, schema_editor):
    User = apps.get_model("accounts", "CustomUser")
    Project = apps.get_model("dashboard", "Project")
    database = schema_editor.connection.alias

    owner_ids = Project.objects.using(database).values_list("owner_id", flat=True).distinct()
    User.objects.using(database).filter(pk__in=owner_ids).update(role="owner")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("dashboard", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="role",
            field=models.CharField(
                choices=[("owner", "Owner"), ("member", "Member")],
                default="member",
                max_length=10,
            ),
        ),
        migrations.RunPython(assign_existing_roles, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="customuser",
            constraint=models.CheckConstraint(
                condition=models.Q(role__in=["owner", "member"]),
                name="customuser_role_valid",
            ),
        ),
    ]

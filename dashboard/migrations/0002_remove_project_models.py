from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0001_initial"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="ProjectMember"),
                migrations.DeleteModel(name="Project"),
            ],
        ),
    ]

from django.db import migrations


def create_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ("admin", "operator", "user"):
        Group.objects.get_or_create(name=name)


def remove_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=("admin", "operator", "user")).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0010_referencetext_user"),
    ]

    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]

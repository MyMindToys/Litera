from django.db import migrations


def set_optional(apps, schema_editor):
    ReferenceField = apps.get_model("app", "ReferenceField")
    ReferenceField.objects.filter(name="resource_type_mark").update(required=False)


def set_required(apps, schema_editor):
    ReferenceField = apps.get_model("app", "ReferenceField")
    ReferenceField.objects.filter(name="resource_type_mark").update(required=True)


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0006_add_online_journal_fields"),
    ]

    operations = [
        migrations.RunPython(set_optional, set_required),
    ]

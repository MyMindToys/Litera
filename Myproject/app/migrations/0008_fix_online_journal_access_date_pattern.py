from django.db import migrations


def fix_access_date_pattern(apps, schema_editor):
    """Исправить pattern для access_date: проверять извлечённую дату (дд.мм.гггг), а не сырую фразу."""
    ReferenceField = apps.get_model("app", "ReferenceField")
    ReferenceField.objects.filter(
        reference_type__code="ONLINE_JOURNAL",
        name="access_date",
    ).update(pattern=r"\d{2}\.\d{2}\.\d{4}")


def revert_access_date_pattern(apps, schema_editor):
    ReferenceField = apps.get_model("app", "ReferenceField")
    ReferenceField.objects.filter(
        reference_type__code="ONLINE_JOURNAL",
        name="access_date",
    ).update(pattern=r"дата\s+обращения:\s*\d{2}\.\d{2}\.\d{4}")


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0007_make_resource_type_mark_optional"),
    ]

    operations = [
        migrations.RunPython(fix_access_date_pattern, revert_access_date_pattern),
    ]

from django.db import migrations


def fix_url_label_pattern(apps, schema_editor):
    """Разрешить для «Метка URL» (ONLINE) и «URL:», и «Режим доступа:» (по ГОСТ)."""
    ReferenceField = apps.get_model("app", "ReferenceField")
    # URL: | Режим доступа: | — Режим доступа:
    new_pattern = r"^(?:URL|(?:[\u002d\u2013\u2014]\s*)?Режим\s+доступа)\s*:?$"
    ReferenceField.objects.filter(
        reference_type__code="ONLINE",
        name="url_label",
    ).update(pattern=new_pattern)


def revert_url_label_pattern(apps, schema_editor):
    ReferenceField = apps.get_model("app", "ReferenceField")
    ReferenceField.objects.filter(
        reference_type__code="ONLINE",
        name="url_label",
    ).update(pattern=r"URL:")


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0008_fix_online_journal_access_date_pattern"),
    ]

    operations = [
        migrations.RunPython(fix_url_label_pattern, revert_url_label_pattern),
    ]

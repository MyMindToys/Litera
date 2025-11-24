from django.db import migrations


def add_online_journal_fields(apps, schema_editor):
    ReferenceType = apps.get_model("app", "ReferenceType")
    ReferenceField = apps.get_model("app", "ReferenceField")
    
    # Получаем тип ONLINE_JOURNAL
    try:
        ref_type = ReferenceType.objects.get(code="ONLINE_JOURNAL")
    except ReferenceType.DoesNotExist:
        # Если типа нет, создаем его
        ref_type = ReferenceType.objects.create(
            code="ONLINE_JOURNAL",
            name="Электронный журнал",
        )
    
    # Создаем поля для электронного журнала
    # Формат: name, label, required, order_index, separator_before, separator_after, pattern, comment
    fields_data = [
        ("title_main", "Основное заглавие", True, 1, "", " ", r".+", "Электронный журнал"),
        ("resource_type_mark", "Пометка ресурса", True, 2, "", ": ", r"\[Электронный\s+ресурс\]", ""),
        ("title_sub", "Подзаголовок", True, 3, "", ". ", r".+", "Название журнала"),
        ("access_mode_label", "Метка режима доступа", True, 4, " — ", ": ", r"Режим\s+доступа:", ""),
        ("url", "URL", True, 5, "", " ", r".+", ""),
        ("access_date", "Дата обращения", True, 6, " (", ")", r"дата\s+обращения:\s*\d{2}\.\d{2}\.\d{4}", ""),
    ]
    
    for name, label, required, order_index, separator_before, separator_after, pattern, comment in fields_data:
        ReferenceField.objects.get_or_create(
            reference_type=ref_type,
            name=name,
            defaults={
                "label": label,
                "required": required,
                "order_index": order_index,
                "separator_before": separator_before,
                "separator_after": separator_after,
                "pattern": pattern,
                "comment": comment,
            },
        )


def remove_online_journal_fields(apps, schema_editor):
    ReferenceField = apps.get_model("app", "ReferenceField")
    # Удаляем поля
    ReferenceField.objects.filter(reference_type__code="ONLINE_JOURNAL").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0005_add_online_journal_type"),
    ]

    operations = [
        migrations.RunPython(add_online_journal_fields, remove_online_journal_fields),
    ]


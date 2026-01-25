# Электронный ресурс на физическом носителе (CD-ROM и т.п.) без URL:
# — url, url_label, access_date делаем необязательными;
# — добавляем authors (сведения об ответственности), place, publisher, year, carrier.

from django.db import migrations


def forward(apps, schema_editor):
    ReferenceType = apps.get_model("app", "ReferenceType")
    ReferenceField = apps.get_model("app", "ReferenceField")

    ref_type = ReferenceType.objects.get(code="ONLINE")

    # 1. Сдвиг order_index для url_label, url, access_date: 3,4,5 -> 4,5,6
    ReferenceField.objects.filter(reference_type=ref_type, name="url_label").update(order_index=4)
    ReferenceField.objects.filter(reference_type=ref_type, name="url").update(order_index=5)
    ReferenceField.objects.filter(reference_type=ref_type, name="access_date").update(order_index=6)

    # 2. Сделать url_label, url, access_date необязательными
    ReferenceField.objects.filter(reference_type=ref_type, name__in=("url_label", "url", "access_date")).update(required=False)

    # 3. Добавить authors (сведения об ответственности), order_index=3
    ReferenceField.objects.get_or_create(
        reference_type=ref_type,
        name="authors",
        defaults={
            "label": "Сведения об ответственности",
            "required": False,
            "order_index": 3,
            "separator_before": " / ",
            "separator_after": " ",
            "pattern": r".*",
            "comment": "Разработчик, изд. и т.п. для электронного ресурса",
        },
    )

    # 4. Добавить place, publisher, year, carrier (order 7,8,9,10)
    extra = [
        ("place", "Место издания", 7, "", ": ", r".*", "Город издательства"),
        ("publisher", "Издательство", 8, " ", ", ", r".*", ""),
        ("year", "Год", 9, " ", ". ", r"\d{4}", ""),
        ("carrier", "Сведения о носителе", 10, " – ", "", r".*", "1 CD-ROM, 1 электрон. опт. диск и т.п."),
    ]
    for name, label, idx, sep_before, sep_after, pattern, comment in extra:
        ReferenceField.objects.get_or_create(
            reference_type=ref_type,
            name=name,
            defaults={
                "label": label,
                "required": False,
                "order_index": idx,
                "separator_before": sep_before,
                "separator_after": sep_after,
                "pattern": pattern,
                "comment": comment,
            },
        )


def reverse(apps, schema_editor):
    ReferenceType = apps.get_model("app", "ReferenceType")
    ReferenceField = apps.get_model("app", "ReferenceField")

    ref_type = ReferenceType.objects.get(code="ONLINE")

    # Удалить добавленные поля
    ReferenceField.objects.filter(
        reference_type=ref_type,
        name__in=("authors", "place", "publisher", "year", "carrier"),
    ).delete()

    # Вернуть order_index 3,4,5 для url_label, url, access_date
    ReferenceField.objects.filter(reference_type=ref_type, name="url_label").update(order_index=3, required=True)
    ReferenceField.objects.filter(reference_type=ref_type, name="url").update(order_index=4, required=True)
    ReferenceField.objects.filter(reference_type=ref_type, name="access_date").update(order_index=5, required=True)


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0011_create_role_groups"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]

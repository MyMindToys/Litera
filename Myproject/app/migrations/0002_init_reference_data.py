from django.db import migrations


def create_reference_data(apps, schema_editor):
    ReferenceType = apps.get_model("app", "ReferenceType")
    ReferenceField = apps.get_model("app", "ReferenceField")

    # 1. Типы ссылок
    type_data = [
        ("BOOK", "Книга"),
        ("ARTICLE_JOURNAL", "Статья из журнала"),
        ("ARTICLE_PROCEEDINGS", "Статья из сборника/конференции"),
        ("ONLINE", "Электронный ресурс"),
        ("DISSERTATION", "Диссертация/автореферат"),
        ("STANDARD", "Нормативный документ"),
        ("PATENT", "Патент"),
    ]

    code_to_obj = {}
    for code, name in type_data:
        obj, _ = ReferenceType.objects.get_or_create(
            code=code,
            defaults={"name": name},
        )
        code_to_obj[code] = obj

    # 2. Поля шаблонов
    # Формат: type_code, name, label, required, order_index,
    #         separator_before, separator_after, pattern, comment
    fields_data = [
        # BOOK — книга
        ("BOOK", "authors", "Авторы", True, 1, "", ". ", r".+", ""),
        ("BOOK", "title", "Заглавие", True, 2, "", ": ", r".+", ""),
        ("BOOK", "document_type", "Тип документа", False, 3, "", ". ", r".+", "Учеб. пособие, монография и др."),
        ("BOOK", "edition", "Сведения об издании", False, 4, "", ". ", r".*", "2-е изд., перераб. и доп. и др."),
        ("BOOK", "place", "Место издания", True, 5, "", ": ", r".+", "М., СПб. и т.п."),
        ("BOOK", "publisher", "Издательство", True, 6, "", ", ", r".+", ""),
        ("BOOK", "year", "Год издания", True, 7, "", ". ", r"\d{4}", ""),
        ("BOOK", "pages", "Объем", True, 8, "", "", r".+", "Количество страниц"),

        # ARTICLE_JOURNAL — статья из журнала
        ("ARTICLE_JOURNAL", "authors", "Авторы", True, 1, "", ". ", r".+", ""),
        ("ARTICLE_JOURNAL", "title", "Заглавие статьи", True, 2, "", " // ", r".+", ""),
        ("ARTICLE_JOURNAL", "journal_title", "Название журнала", True, 3, "", ". ", r".+", ""),
        ("ARTICLE_JOURNAL", "year", "Год", True, 4, "", ". ", r"\d{4}", ""),
        ("ARTICLE_JOURNAL", "volume", "Том", False, 5, "", ", ", r".*", "Т. 21 и т.п."),
        ("ARTICLE_JOURNAL", "issue", "Номер", True, 6, "", ". ", r".+", "№ 4 и т.п."),
        ("ARTICLE_JOURNAL", "pages", "Страницы", True, 7, "", "", r".+", "С. 45–58 и т.п."),

        # ARTICLE_PROCEEDINGS — статья из сборника/конференции
        ("ARTICLE_PROCEEDINGS", "authors", "Авторы", True, 1, "", ". ", r".+", ""),
        ("ARTICLE_PROCEEDINGS", "title", "Заглавие статьи", True, 2, "", " // ", r".+", ""),
        ("ARTICLE_PROCEEDINGS", "collection_title", "Название сборника", True, 3, "", ": ", r".+", ""),
        ("ARTICLE_PROCEEDINGS", "collection_subtitle", "Подзаголовок", False, 4, "", ". ", r".*", "Материалы конференции и др."),
        ("ARTICLE_PROCEEDINGS", "place", "Место издания", True, 5, "", ", ", r".+", ""),
        ("ARTICLE_PROCEEDINGS", "year", "Год", True, 6, "", ". ", r"\d{4}", ""),
        ("ARTICLE_PROCEEDINGS", "pages", "Страницы", True, 7, "", "", r".+", ""),

        # ONLINE — электронный ресурс
        ("ONLINE", "title", "Заглавие", True, 1, "", " ", r".+", ""),
        ("ONLINE", "resource_type_mark", "Пометка ресурса", True, 2, "", ". ", r"\[Электронный ресурс\]", ""),
        ("ONLINE", "url_label", "Метка URL", True, 3, "", " ", r"URL:", ""),
        ("ONLINE", "url", "URL", True, 4, "", " ", r".+", ""),
        ("ONLINE", "access_date", "Дата обращения", True, 5, "", "", r".+", "В скобках: (дата обращения: ...)"),

        # DISSERTATION — диссертация/автореферат
        ("DISSERTATION", "author", "Автор", True, 1, "", ". ", r".+", ""),
        ("DISSERTATION", "title", "Заглавие", True, 2, "", ": ", r".+", ""),
        ("DISSERTATION", "dissertation_mark", "Вид работы", True, 3, "", ". ", r".+", "дис. ... канд. экон. наук и др."),
        ("DISSERTATION", "place", "Место", True, 4, "", ", ", r".+", ""),
        ("DISSERTATION", "year", "Год", True, 5, "", ". ", r"\d{4}", ""),
        ("DISSERTATION", "pages", "Объем", True, 6, "", "", r".+", "Количество страниц"),

        # STANDARD — нормативный документ
        ("STANDARD", "doc_code", "Обозначение документа", True, 1, "", ". ", r".+", "ГОСТ, закон и др."),
        ("STANDARD", "title_main", "Основной заголовок", True, 2, "", ". ", r".+", ""),
        ("STANDARD", "title_sub", "Дополнительный заголовок", False, 3, "", ". ", r".*", ""),
        ("STANDARD", "place", "Место издания", True, 4, "", ": ", r".+", ""),
        ("STANDARD", "publisher", "Издательство", True, 5, "", ", ", r".+", ""),
        ("STANDARD", "year", "Год", True, 6, "", ". ", r"\d{4}", ""),
        ("STANDARD", "pages", "Объем", True, 7, "", "", r".+", ""),

        # PATENT — патент
        ("PATENT", "patent_mark", "Обозначение патента", True, 1, "", ". ", r".+", "Пат. NNNNNN РФ и др."),
        ("PATENT", "title", "Название изобретения", True, 2, "", " / ", r".+", ""),
        ("PATENT", "inventors", "Изобретатели", True, 3, "", "; ", r".+", ""),
        ("PATENT", "owner_info", "Правообладатель", False, 4, "", ". ", r".*", ""),
        ("PATENT", "application_date", "Дата заявки", False, 5, "", "; ", r".*", "Заявл. ..."),
        ("PATENT", "publication_date", "Дата публикации", False, 6, "", ", ", r".*", "Опубл. ..."),
        ("PATENT", "bulletin", "Бюллетень", False, 7, "", "", r".*", "Бюл. № ..."),
    ]

    for (
        type_code,
        name,
        label,
        required,
        order_index,
        separator_before,
        separator_after,
        pattern,
        comment,
    ) in fields_data:
        ref_type = code_to_obj.get(type_code)
        if not ref_type:
            continue

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


def delete_reference_data(apps, schema_editor):
    ReferenceType = apps.get_model("app", "ReferenceType")
    ReferenceField = apps.get_model("app", "ReferenceField")

    codes = [
        "BOOK",
        "ARTICLE_JOURNAL",
        "ARTICLE_PROCEEDINGS",
        "ONLINE",
        "DISSERTATION",
        "STANDARD",
        "PATENT",
    ]

    ReferenceField.objects.filter(reference_type__code__in=codes).delete()
    ReferenceType.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_reference_data, delete_reference_data),
    ]



import re

from .models import Reference, ReferenceField, ReferenceIssue
from .parsers import parse_reference_instance


def check_reference(reference: Reference) -> None:
    """
    Проверяет одну ссылку:
    - пересоздает ReferenceIssue для нее;
    - обновляет reference.parsed_data и reference.status.
    """
    # Удалить старые проблемы для этой ссылки
    ReferenceIssue.objects.filter(reference=reference).delete()
    
    # 1. Проверка: выбран ли тип
    if reference.reference_type is None:
        ReferenceIssue.objects.create(
            reference=reference,
            field_name="",
            severity="error",
            message="Не выбран тип ссылки.",
        )
        reference.parsed_data = {}
        reference.status = "error"
        reference.save()
        return
    
    # 2. Парсинг
    data = parse_reference_instance(reference)
    if not data:
        ReferenceIssue.objects.create(
            reference=reference,
            field_name="",
            severity="error",
            message=f"Не удалось распарсить ссылку для типа '{reference.reference_type.name}'.",
        )
        reference.parsed_data = {}
        reference.status = "error"
        reference.save()
        return
    
    # 3. Проверка обязательных полей по ReferenceField
    errors = []
    fields_qs = ReferenceField.objects.filter(
        reference_type=reference.reference_type
    ).order_by("order_index")
    
    for field in fields_qs:
        value = (data.get(field.name) or "").strip()
        
        if field.required and not value:
            errors.append(
                ReferenceIssue(
                    reference=reference,
                    field_name=field.name,
                    severity="error",
                    message=f"Отсутствует обязательное поле: {field.label}.",
                )
            )
        
        # При наличии pattern можно проверить формат
        pattern = (field.pattern or "").strip()
        if pattern and value:
            try:
                if not re.match(pattern, value):
                    errors.append(
                        ReferenceIssue(
                            reference=reference,
                            field_name=field.name,
                            severity="warning",
                            message=f"Поле «{field.label}» не соответствует ожидаемому формату.",
                        )
                    )
            except re.error:
                # Если регулярка в БД некорректная, просто игнорируем проверку формата
                pass

    # Специальное правило для ONLINE: при наличии URL дата обращения обязательна (ГОСТ для сетевых ресурсов)
    if reference.reference_type and reference.reference_type.code == "ONLINE":
        url_val = (data.get("url") or "").strip()
        access_val = (data.get("access_date") or "").strip()
        if url_val and not access_val:
            errors.append(
                ReferenceIssue(
                    reference=reference,
                    field_name="access_date",
                    severity="error",
                    message="Для сетевого ресурса (с URL) укажите дату обращения: (дата обращения: ДД.ММ.ГГГГ).",
                )
            )

    # Сохранить parsed_data и статус
    reference.parsed_data = data
    reference.status = "error" if errors else "ok"
    reference.save()
    
    if errors:
        ReferenceIssue.objects.bulk_create(errors)



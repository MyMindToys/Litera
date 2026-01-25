from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden

from .models import ReferenceType, ReferenceField, Reference, ReferenceIssue, ReferenceText
from .forms import ReferenceTypeForm
from .utils import clean_reference_line
from .parsers import parse_reference_instance
from .validators import check_reference
from .auth_utils import (
    login_required,
    role_required,
    is_admin,
    is_operator,
    can_edit_templates,
    can_see_all_checks,
    can_see_templates,
)


def index(request):
    """Главная: неавторизованный — только О программе и Войти; иначе — по ролям."""
    return render(request, "index.html")


def about(request):
    """О программе — доступно всем."""
    return render(request, "about.html")


@login_required
def check_list(request):
    """Страница проверки списка ссылок. user — только свои, operator/admin — все."""
    if request.method == "POST":
        reference_list = request.POST.get("reference_list", "").strip()
        if reference_list:
            reference_text = ReferenceText.objects.create(
                input_text=reference_list,
                status="new",
                user=request.user,
            )
            return redirect("check_list_parse", pk=reference_text.pk)

    if can_see_all_checks(request.user):
        reference_texts = ReferenceText.objects.all()
    else:
        reference_texts = ReferenceText.objects.filter(user=request.user)
    # Проверяем, есть ли у каждого ReferenceText связанные Reference с заполненными данными
    for text in reference_texts:
        try:
            has_checked = Reference.objects.filter(
                reference_text=text
            ).exclude(parsed_data__isnull=True).exclude(parsed_data={}).exists()
            if has_checked:
                text.display_status = "Проверено"
            else:
                text.display_status = text.status
        except Exception:
            text.display_status = text.status
    
    return render(request, 'check_list.html', {
        'reference_texts': reference_texts
    })


@login_required
def check_list_parse(request, pk):
    """Страница с распарсенным текстом по строкам. user — только свои проверки."""
    if can_see_all_checks(request.user):
        reference_text = get_object_or_404(ReferenceText, pk=pk)
    else:
        reference_text = get_object_or_404(ReferenceText, pk=pk, user=request.user)
    
    # Разбиваем текст на строки
    lines = reference_text.input_text.splitlines()
    # Убираем пустые строки и сохраняем с номером строки
    parsed_lines = []
    for idx, line in enumerate(lines, start=1):
        line_text = line.strip()
        if line_text:  # Пропускаем пустые строки
            parsed_lines.append({
                'number': idx,
                'text': line_text
            })
    
    return render(request, 'check_list_parse.html', {
        'reference_text': reference_text,
        'parsed_lines': parsed_lines
    })


@login_required
def check_list_edit(request, pk):
    """Редактирование исходного текста списка ссылок. После сохранения — удаление сохранённых Reference и редирект на verify."""
    if can_see_all_checks(request.user):
        reference_text = get_object_or_404(ReferenceText, pk=pk)
    else:
        reference_text = get_object_or_404(ReferenceText, pk=pk, user=request.user)

    if request.method == "POST":
        new_text = request.POST.get("input_text", "").strip()
        if new_text:
            reference_text.input_text = new_text
            reference_text.intermediate_text = ""
            reference_text.output_text = ""
            reference_text.save()
            Reference.objects.filter(reference_text=reference_text).delete()
            messages.success(request, "Текст сохранён. Выполните «Очистить и сохранить ссылки» для повторной обработки.")
        else:
            messages.warning(request, "Текст не может быть пустым.")
        return redirect("check_list_verify", pk=pk)

    return render(request, "check_list_edit.html", {"reference_text": reference_text})


@login_required
def check_list_verify(request, pk):
    """Страница проверки списка ссылок. user — только свои проверки."""
    if can_see_all_checks(request.user):
        reference_text = get_object_or_404(ReferenceText, pk=pk)
    else:
        reference_text = get_object_or_404(ReferenceText, pk=pk, user=request.user)
    
    # Обработка POST-запроса для проверки всех ссылок
    if request.method == 'POST' and request.POST.get('action') == 'check_all':
        try:
            # Получаем все сохраненные ссылки
            saved_references = Reference.objects.filter(reference_text=reference_text)
            
            if not saved_references.exists():
                messages.warning(request, 'Нет сохраненных ссылок для проверки.')
                return redirect('check_list_verify', pk=pk)
            
            # 1) Сначала обновляем типы по данным из формы
            for ref in saved_references:
                ref_type_id = request.POST.get(f'reference_type_{ref.id}', '').strip()
                if ref_type_id:
                    try:
                        ref_type = ReferenceType.objects.get(pk=int(ref_type_id))
                        ref.reference_type = ref_type
                    except (ReferenceType.DoesNotExist, ValueError):
                        ref.reference_type = None
                else:
                    ref.reference_type = None
                ref.save()
            
            # 2) Затем проверяем каждую ссылку и создаем issues
            checked_count = 0
            for ref in saved_references:
                check_reference(ref)
                checked_count += 1
            
            messages.success(request, f'Проверено {checked_count} ссылок.')
            return redirect('check_list_verify', pk=pk)
        except Exception as e:
            import traceback
            messages.error(request, f'Ошибка при проверке: {str(e)}')
            return redirect('check_list_verify', pk=pk)
    
    # Обработка POST-запроса для сохранения типов ссылок
    if request.method == 'POST' and request.POST.get('action') == 'save_types':
        try:
            saved_count = 0
            # Получаем все сохраненные ссылки
            saved_references = Reference.objects.filter(reference_text=reference_text)
            
            if not saved_references.exists():
                messages.warning(request, 'Нет сохраненных ссылок для обновления.')
                return redirect('check_list_verify', pk=pk)
            
            for ref in saved_references:
                ref_type_id = request.POST.get(f'reference_type_{ref.id}', '').strip()
                if ref_type_id:
                    try:
                        ref_type = ReferenceType.objects.get(pk=int(ref_type_id))
                        ref.reference_type = ref_type
                    except (ReferenceType.DoesNotExist, ValueError) as e:
                        ref.reference_type = None
                else:
                    ref.reference_type = None
                ref.save()
                # Перезагружаем объект из базы для получения актуальных данных
                ref.refresh_from_db()
                saved_count += 1
            
            messages.success(request, f'Типы ссылок сохранены для {saved_count} ссылок.')
            return redirect('check_list_verify', pk=pk)
        except Exception as e:
            import traceback
            messages.error(request, f'Ошибка при сохранении типов: {str(e)}')
            return redirect('check_list_verify', pk=pk)
    
    # Обработка POST-запроса для сохранения очищенных ссылок
    if request.method == 'POST' and request.POST.get('action') == 'clean_and_save':
        try:
            # Удаляем старые ссылки для этого ReferenceText
            Reference.objects.filter(reference_text=reference_text).delete()
            
            # Разбиваем текст на строки
            lines = reference_text.input_text.splitlines()
            
            # Очищаем и сохраняем каждую строку как Reference
            created_count = 0
            for idx, line in enumerate(lines, start=1):
                line_text = line.strip()
                if line_text:  # Пропускаем пустые строки
                    # Очищаем строку
                    cleaned_text = clean_reference_line(line_text)
                    
                    if cleaned_text:  # Сохраняем только если после очистки остался текст
                        Reference.objects.create(
                            reference_text=reference_text,
                            raw_text=cleaned_text,
                            status='new'
                        )
                        created_count += 1
            
            messages.success(request, f'Сохранено {created_count} очищенных ссылок.')
            return redirect('check_list_verify', pk=pk)
        except Exception as e:
            # Если миграция не применена, показываем ошибку
            messages.error(request, f'Ошибка при сохранении: необходимо применить миграцию. {str(e)}')
            return redirect('check_list_verify', pk=pk)
    
    # Получаем уже сохраненные ссылки, если они есть
    # Используем try-except на случай, если миграция еще не применена
    try:
        saved_references = Reference.objects.filter(reference_text=reference_text).select_related('reference_type').order_by('id')
        has_saved = saved_references.exists()
    except Exception as e:
        # Если миграция не применена, считаем что сохраненных ссылок нет
        saved_references = Reference.objects.none()
        has_saved = False
        # Логируем ошибку для отладки
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при загрузке ссылок: {str(e)}")
    
    # Получаем все типы ссылок для выпадающего меню
    reference_types = ReferenceType.objects.all().order_by('name')
    
    # Если есть сохраненные ссылки, показываем их
    # Если нет - показываем распарсенные строки из исходного текста
    if has_saved:
        references_list = []
        # Создаем словарь соответствия ID ссылки -> порядковый номер
        reference_id_to_number = {}
        for idx, ref in enumerate(saved_references, start=1):
            # Получаем ID типа ссылки, если он установлен
            ref_type_id = None
            if ref.reference_type:
                ref_type_id = ref.reference_type.id
            reference_id_to_number[ref.id] = idx
            references_list.append({
                'number': idx,
                'text': ref.raw_text,
                'id': ref.id,
                'reference_type_id': ref_type_id,
                'status': ref.status if hasattr(ref, 'status') else '',
                'reference_obj': ref  # Передаем сам объект для доступа к issues
            })
    else:
        # Разбиваем текст на строки только если нет сохраненных ссылок
        reference_id_to_number = {}
        lines = reference_text.input_text.splitlines()
        references_list = []
        for idx, line in enumerate(lines, start=1):
            line_text = line.strip()
            if line_text:  # Пропускаем пустые строки
                references_list.append({
                    'number': idx,
                    'text': line_text
                })
    
    # Получаем все проблемы для данного ReferenceText
    try:
        issues_qs = ReferenceIssue.objects.filter(
            reference__reference_text=reference_text
        ).select_related("reference").order_by('reference__id', '-severity')
        # Добавляем порядковый номер к каждой проблеме
        issues = []
        for issue in issues_qs:
            issue.reference_number = reference_id_to_number.get(issue.reference.id, issue.reference.id)
            issues.append(issue)
    except Exception:
        issues = []
    
    return render(request, 'check_list_verify.html', {
        'reference_text': reference_text,
        'references_list': references_list,
        'has_saved_references': has_saved,
        'reference_types': reference_types,
        'issues': issues
    })


@login_required
def reference_errors(request, pk):
    """Страница с детальной информацией об ошибках. user — только свои проверки."""
    reference = get_object_or_404(Reference, pk=pk)
    rt = reference.reference_text
    if not can_see_all_checks(request.user):
        if not rt or rt.user != request.user:
            return HttpResponseForbidden("Доступ запрещён.")

    # Получаем все проблемы для этой ссылки
    try:
        issues = ReferenceIssue.objects.filter(reference=reference).order_by('-severity', 'field_name')
    except Exception:
        issues = []

    # Получаем parsed_data
    parsed_data = reference.parsed_data if hasattr(reference, 'parsed_data') and reference.parsed_data else {}

    # Ход парсинга: когда парсинг не удался — показываем, что найдено, что нет
    parse_steps = []
    if not parsed_data and reference.reference_type_id:
        try:
            from .parse_diagnostics import get_parse_diagnostic
            parse_steps = get_parse_diagnostic(reference.raw_text or "", reference.reference_type.code)
        except Exception:
            parse_steps = []

    return render(request, 'reference_errors.html', {
        'reference': reference,
        'issues': issues,
        'parsed_data': parsed_data,
        'parse_steps': parse_steps,
    })


# CRUD для ReferenceType: operator — просмотр, admin — полный доступ
@login_required
def reference_type_list(request):
    """Список типов ссылок. operator и admin — просмотр; admin — редактирование."""
    if not can_see_templates(request.user):
        return HttpResponseForbidden("Доступ запрещён.")
    reference_types = ReferenceType.objects.all()
    reference_fields = ReferenceField.objects.all()
    references = Reference.objects.all()
    reference_issues = ReferenceIssue.objects.all()
    return render(
        request,
        "reference_type/list.html",
        {
            "reference_types": reference_types,
            "reference_fields": reference_fields,
            "references": references,
            "reference_issues": reference_issues,
            "can_edit": can_edit_templates(request.user),
        },
    )


@login_required
def reference_type_detail(request, pk):
    """Детальный просмотр типа ссылки. operator — просмотр, admin — редактирование."""
    if not can_see_templates(request.user):
        return HttpResponseForbidden("Доступ запрещён.")
    reference_type = get_object_or_404(ReferenceType, pk=pk)
    return render(
        request,
        "reference_type/detail.html",
        {"reference_type": reference_type, "can_edit": can_edit_templates(request.user)},
    )


@role_required("admin")
def reference_type_create(request):
    """Создание нового типа ссылки — только admin."""
    if request.method == "POST":
        form = ReferenceTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Тип ссылки успешно создан.')
            return redirect('reference_type_list')
    else:
        form = ReferenceTypeForm()
    return render(request, 'reference_type/form.html', {
        'form': form,
        'title': 'Создать тип ссылки'
    })


@role_required("admin")
def reference_type_update(request, pk):
    """Редактирование типа ссылки — только admin."""
    reference_type = get_object_or_404(ReferenceType, pk=pk)
    if request.method == "POST":
        form = ReferenceTypeForm(request.POST, instance=reference_type)
        if form.is_valid():
            form.save()
            messages.success(request, 'Тип ссылки успешно обновлен.')
            return redirect('reference_type_detail', pk=reference_type.pk)
    else:
        form = ReferenceTypeForm(instance=reference_type)
    return render(request, 'reference_type/form.html', {
        'form': form,
        'reference_type': reference_type,
        'title': 'Редактировать тип ссылки'
    })


@role_required("admin")
def reference_type_delete(request, pk):
    """Удаление типа ссылки — только admin."""
    reference_type = get_object_or_404(ReferenceType, pk=pk)
    if request.method == "POST":
        reference_type.delete()
        messages.success(request, 'Тип ссылки успешно удален.')
        return redirect('reference_type_list')
    return render(request, 'reference_type/delete.html', {
        'reference_type': reference_type
    })


@login_required
def reference_type_fields(request, pk):
    """Список полей типа ссылки. operator и admin — просмотр."""
    if not can_see_templates(request.user):
        return HttpResponseForbidden("Доступ запрещён.")
    reference_type = get_object_or_404(ReferenceType, pk=pk)
    fields = ReferenceField.objects.filter(reference_type=reference_type).order_by("order_index")
    return render(
        request,
        "reference_type/fields.html",
        {"reference_type": reference_type, "fields": fields, "can_edit": can_edit_templates(request.user)},
    )

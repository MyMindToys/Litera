from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import ReferenceType
from .forms import ReferenceTypeForm


def index(request):
    """Главная страница"""
    return render(request, 'index.html')


def about(request):
    """Страница О программе"""
    return render(request, 'about.html')


# CRUD для ReferenceType
def reference_type_list(request):
    """Список типов ссылок"""
    reference_types = ReferenceType.objects.all()
    return render(request, 'reference_type/list.html', {
        'reference_types': reference_types
    })


def reference_type_detail(request, pk):
    """Детальный просмотр типа ссылки"""
    reference_type = get_object_or_404(ReferenceType, pk=pk)
    return render(request, 'reference_type/detail.html', {
        'reference_type': reference_type
    })


def reference_type_create(request):
    """Создание нового типа ссылки"""
    if request.method == 'POST':
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


def reference_type_update(request, pk):
    """Редактирование типа ссылки"""
    reference_type = get_object_or_404(ReferenceType, pk=pk)
    if request.method == 'POST':
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


def reference_type_delete(request, pk):
    """Удаление типа ссылки"""
    reference_type = get_object_or_404(ReferenceType, pk=pk)
    if request.method == 'POST':
        reference_type.delete()
        messages.success(request, 'Тип ссылки успешно удален.')
        return redirect('reference_type_list')
    return render(request, 'reference_type/delete.html', {
        'reference_type': reference_type
    })

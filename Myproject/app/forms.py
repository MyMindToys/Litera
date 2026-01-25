from django import forms
from .models import ReferenceType, ReferenceField


class ReferenceTypeForm(forms.ModelForm):
    """Форма для создания и редактирования типа ссылки"""
    
    class Meta:
        model = ReferenceType
        fields = ['code', 'name']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Введите код типа ссылки'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Введите название типа ссылки'
            }),
        }
        labels = {
            'code': 'Код',
            'name': 'Название',
        }


class ReferenceFieldForm(forms.ModelForm):
    """Форма для создания и редактирования поля типа ссылки."""

    class Meta:
        model = ReferenceField
        fields = [
            'name', 'label', 'required', 'order_index',
            'separator_before', 'separator_after', 'comment',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'label': forms.TextInput(attrs={'class': 'form-input'}),
            'required': forms.CheckboxInput(attrs={'class': 'form-input'}),
            'order_index': forms.NumberInput(attrs={'class': 'form-input'}),
            'separator_before': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '—'}),
            'separator_after': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '—'}),
            'comment': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }
        labels = {
            'name': 'Имя поля',
            'label': 'Метка',
            'required': 'Обязательное',
            'order_index': 'Порядок',
            'separator_before': 'Разделитель перед',
            'separator_after': 'Разделитель после',
            'comment': 'Комментарий',
        }



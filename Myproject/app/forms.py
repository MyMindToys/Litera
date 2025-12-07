from django import forms
from .models import ReferenceType


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



from django.db import models


class ReferenceType(models.Model):
    """Тип библиографической ссылки"""
    code = models.CharField(max_length=64, unique=True, verbose_name="Код")
    name = models.CharField(max_length=255, verbose_name="Название")

    class Meta:
        verbose_name = "Тип ссылки"
        verbose_name_plural = "Типы ссылок"
        ordering = ['name']

    def __str__(self):
        return self.name


class ReferenceField(models.Model):
    """Поле библиографической ссылки"""
    reference_type = models.ForeignKey(
        ReferenceType,
        on_delete=models.CASCADE,
        related_name='fields',
        verbose_name="Тип ссылки"
    )
    name = models.CharField(max_length=255, verbose_name="Имя поля")
    label = models.CharField(max_length=255, verbose_name="Метка")
    required = models.BooleanField(default=False, verbose_name="Обязательное")
    order_index = models.IntegerField(default=0, verbose_name="Порядок")
    separator_before = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Разделитель перед"
    )
    separator_after = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Разделитель после"
    )
    pattern = models.TextField(verbose_name="Шаблон")
    comment = models.TextField(blank=True, verbose_name="Комментарий")

    class Meta:
        verbose_name = "Поле ссылки"
        verbose_name_plural = "Поля ссылок"
        ordering = ['reference_type', 'order_index']

    def __str__(self):
        return f"{self.reference_type.name} - {self.label}"


class Reference(models.Model):
    """Библиографическая ссылка"""
    raw_text = models.TextField(verbose_name="Исходный текст")
    normalized_text = models.TextField(blank=True, verbose_name="Нормализованный текст")
    reference_type = models.ForeignKey(
        ReferenceType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='references',
        verbose_name="Тип ссылки"
    )
    parsed_data = models.JSONField(blank=True, null=True, verbose_name="Распарсенные данные")
    status = models.CharField(max_length=32, verbose_name="Статус")

    class Meta:
        verbose_name = "Ссылка"
        verbose_name_plural = "Ссылки"
        ordering = ['-id']

    def __str__(self):
        return self.raw_text[:50] + "..." if len(self.raw_text) > 50 else self.raw_text


class ReferenceIssue(models.Model):
    """Проблема/ошибка в библиографической ссылке"""
    reference = models.ForeignKey(
        Reference,
        on_delete=models.CASCADE,
        related_name='issues',
        verbose_name="Ссылка"
    )
    field_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Имя поля"
    )
    severity = models.CharField(max_length=16, verbose_name="Серьезность")
    message = models.TextField(verbose_name="Сообщение")

    class Meta:
        verbose_name = "Проблема ссылки"
        verbose_name_plural = "Проблемы ссылок"
        ordering = ['reference', '-severity']

    def __str__(self):
        return f"{self.reference} - {self.severity}: {self.message[:50]}"

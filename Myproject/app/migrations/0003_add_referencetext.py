# Generated manually for ReferenceText model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_init_reference_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReferenceText',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=255, verbose_name='Название')),
                ('input_text', models.TextField(verbose_name='Исходный текст')),
                ('intermediate_text', models.TextField(blank=True, verbose_name='Промежуточный текст')),
                ('output_text', models.TextField(blank=True, verbose_name='Итоговый текст')),
                ('status', models.CharField(default='new', max_length=32, verbose_name='Статус')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Текст списка ссылок',
                'verbose_name_plural': 'Тексты списков ссылок',
                'ordering': ['-created_at'],
            },
        ),
    ]



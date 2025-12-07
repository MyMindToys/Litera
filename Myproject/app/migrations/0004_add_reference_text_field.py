# Generated manually for Reference.reference_text field

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_add_referencetext'),
    ]

    operations = [
        migrations.AddField(
            model_name='reference',
            name='reference_text',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='references',
                to='app.referencetext',
                verbose_name='Текст списка ссылок'
            ),
        ),
    ]



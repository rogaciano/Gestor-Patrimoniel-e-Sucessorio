from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0008_pessoa_foto'),
    ]

    operations = [
        migrations.CreateModel(
            name='FamiliaAcesso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('familia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='acessos', to='core.familia')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='familia_access', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Acesso de FamÃ\xadlia',
                'verbose_name_plural': 'Acessos de FamÃ\xadlia',
            },
        ),
    ]

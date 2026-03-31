# Generated migration to handle Ativo.proprietario conversion
# This is a multi-step migration strategy:
# 1. Add content_type and object_id fields (nullable temporarily)
# 2. Data migration: copy Pessoa FK to GenericFK
# 3. Remove old proprietario FK
# 4. Make content_type/object_id non-nullable

from django.db import migrations, models
import django.db.models.deletion
from django.contrib.contenttypes.models import ContentType


def migrate_proprietario_to_generic(apps, schema_editor):
    """
    Data migration: Convert existing Ativo.proprietario (Pessoa FK) 
    to GenericForeignKey (content_type + object_id)
    """
    Ativo = apps.get_model('core', 'Ativo')
    Pessoa = apps.get_model('core', 'Pessoa')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    
    # Get ContentType for Pessoa
    pessoa_ct = ContentType.objects.get_for_model(Pessoa)
    
    # Update all existing Ativos
    for ativo in Ativo.objects.all():
        if hasattr(ativo, 'proprietario_old') and ativo.proprietario_old:
            ativo.content_type = pessoa_ct
            ativo.object_id = ativo.proprietario_old.id
            ativo.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),  # Replace with your actual last migration
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        # Step 1: Rename old FK temporarily
        migrations.RenameField(
            model_name='ativo',
            old_name='proprietario',
            new_name='proprietario_old',
        ),
        
        # Step 2: Add new GenericFK fields (nullable for now)
        migrations.AddField(
            model_name='ativo',
            name='content_type',
            field=models.ForeignKey(
                null=True,  # Temporary
                on_delete=django.db.models.deletion.CASCADE,
                to='contenttypes.contenttype'
            ),
        ),
        migrations.AddField(
            model_name='ativo',
            name='object_id',
            field=models.UUIDField(null=True),  # Temporary
        ),
        
        # Step 3: Data migration
        migrations.RunPython(migrate_proprietario_to_generic),
        
        # Step 4: Remove old FK
        migrations.RemoveField(
            model_name='ativo',
            name='proprietario_old',
        ),
        
        # Step 5: Make new fields non-nullable
        migrations.AlterField(
            model_name='ativo',
            name='content_type',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='contenttypes.contenttype'
            ),
        ),
        migrations.AlterField(
            model_name='ativo',
            name='object_id',
            field=models.UUIDField(),
        ),
    ]

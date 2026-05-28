from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('programaciones', '0002_alter_ejecucionprogramacion_fecha_ejecutada_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='EjecucionProgramacion',
        ),
    ]

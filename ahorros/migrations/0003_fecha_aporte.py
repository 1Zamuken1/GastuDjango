from datetime import date

from django.db import migrations, models


def rellenar_fecha_aporte(apps, schema_editor):
    """Estima la fecha de los aportes ya registrados.

    No hay un dato fiable del dia en que se pago cada cuota:
    - Los aportes extraordinarios se crean al pagarlos, asi que su
      fecha_registro es correcta.
    - Las cuotas regulares se crearon junto con la meta; se usa su fecha
      limite, sin pasar de hoy (una cuota se puede pagar antes de vencer).
    """
    AporteAhorro = apps.get_model('ahorros', 'AporteAhorro')
    hoy = date.today()
    pendientes = []
    for aporte in AporteAhorro.objects.filter(estado_ap='APORTADO', fecha_aporte__isnull=True):
        if aporte.es_extraordinario:
            aporte.fecha_aporte = aporte.fecha_registro
        else:
            aporte.fecha_aporte = min(aporte.fecha_limite, hoy)
        pendientes.append(aporte)
    AporteAhorro.objects.bulk_update(pendientes, ['fecha_aporte'], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('ahorros', '0002_aporteahorro_es_extraordinario'),
    ]

    operations = [
        migrations.AddField(
            model_name='aporteahorro',
            name='fecha_aporte',
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='ahorrometa',
            name='estado',
            field=models.CharField(choices=[('SIN_INICIAR', 'Sin iniciar'), ('ACTIVO', 'Activo'), ('COMPLETADO', 'Completado'), ('ABANDONADO', 'Abandonado')], default='SIN_INICIAR', max_length=25),
        ),
        migrations.RunPython(rellenar_fecha_aporte, migrations.RunPython.noop),
    ]

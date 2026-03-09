from decimal import Decimal


def crear_notificacion(usuario, tipo, titulo, descripcion):
    """
    Crea una notificación para el usuario si no existe una igual no leída.
    Evita duplicar notificaciones del mismo tipo en el mismo día.

    Args:
        usuario: instancia del usuario.
        tipo (str): tipo de notificación definido en Notificacion.Tipo.
        titulo (str): título corto de la notificación.
        descripcion (str): detalle de la notificación.
    """
    from .models import Notificacion
    from django.utils import timezone

    hoy = timezone.now().date()

    ya_existe = Notificacion.objects.filter(
        usuario=usuario,
        tipo=tipo,
        leida=False,
        fecha_creacion__date=hoy
    ).exists()

    if not ya_existe:
        Notificacion.objects.create(
            usuario=usuario,
            tipo=tipo,
            titulo=titulo,
            descripcion=descripcion
        )


def analizar_movimiento(usuario, mes, anio):
    """
    Analiza el estado financiero del usuario tras un movimiento
    y genera notificaciones según corresponda.

    Args:
        usuario: instancia del usuario.
        mes (int): mes del movimiento registrado.
        anio (int): año del movimiento registrado.
    """
    from dashboard.models import ResumenMensual
    from .models import Notificacion

    resumen = ResumenMensual.objects.filter(
        usuario=usuario,
        mes=mes,
        anio=anio
    ).first()

    if not resumen:
        return

    # Obtener preferencias del usuario
    try:
        preferencias = usuario.preferencias
    except Exception:
        return

    # Notificación: umbral mensual alcanzado
    if (preferencias.alerta_presupuesto
            and resumen.total_ingresos > 0):
        porcentaje_gastado = (resumen.total_egresos / resumen.total_ingresos) * 100
        if porcentaje_gastado >= preferencias.umbral_advertencia_porcentaje:
            crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.UMBRAL_MENSUAL,
                titulo='Umbral de gastos alcanzado',
                descripcion=(
                    f'Has gastado el {porcentaje_gastado:.1f}% de tus ingresos '
                    f'de este mes (${resumen.total_egresos:,.2f} de '
                    f'${resumen.total_ingresos:,.2f}).'
                )
            )

    # Notificación: déficit
    if preferencias.alerta_deficit and resumen.deficit:
        crear_notificacion(
            usuario=usuario,
            tipo=Notificacion.Tipo.DEFICIT,
            titulo='Balance en déficit',
            descripcion=(
                f'Tus egresos (${resumen.total_egresos:,.2f}) superan '
                f'tus ingresos (${resumen.total_ingresos:,.2f}) este mes.'
            )
        )

def analizar_movimiento(usuario, mes, anio, ultimo_egreso=None):
    """
    Analiza el estado financiero del usuario tras un movimiento
    y genera notificaciones según corresponda.

    Args:
        usuario: instancia del usuario.
        mes (int): mes del movimiento registrado.
        anio (int): año del movimiento registrado.
        ultimo_egreso (Decimal): monto del último egreso registrado, opcional.
    """
    from dashboard.models import ResumenMensual
    from .models import Notificacion

    resumen = ResumenMensual.objects.filter(
        usuario=usuario,
        mes=mes,
        anio=anio
    ).first()

    if not resumen:
        return

    try:
        preferencias = usuario.preferencias
    except Exception:
        return

    # Notificación: umbral mensual alcanzado
    if (preferencias.alerta_presupuesto
            and resumen.total_ingresos > 0):
        porcentaje_gastado = (resumen.total_egresos / resumen.total_ingresos) * 100
        if porcentaje_gastado >= preferencias.umbral_advertencia_porcentaje:
            crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.UMBRAL_MENSUAL,
                titulo='Umbral de gastos alcanzado',
                descripcion=(
                    f'Has gastado el {porcentaje_gastado:.1f}% de tus ingresos '
                    f'de este mes (${resumen.total_egresos:,.2f} de '
                    f'${resumen.total_ingresos:,.2f}).'
                )
            )

    # Notificación: déficit
    if preferencias.alerta_deficit and resumen.deficit:
        crear_notificacion(
            usuario=usuario,
            tipo=Notificacion.Tipo.DEFICIT,
            titulo='Balance en déficit',
            descripcion=(
                f'Tus egresos (${resumen.total_egresos:,.2f}) superan '
                f'tus ingresos (${resumen.total_ingresos:,.2f}) este mes.'
            )
        )

    # Notificación: egreso grande
    if (preferencias.alerta_egreso_grande
            and ultimo_egreso is not None
            and resumen.total_ingresos > 0):
        porcentaje_egreso = (ultimo_egreso / resumen.total_ingresos) * 100
        if porcentaje_egreso >= preferencias.egreso_grande_porcentaje:
            crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.EGRESO_GRANDE,
                titulo='Egreso grande registrado',
                descripcion=(
                    f'Registraste un egreso de ${ultimo_egreso:,.2f} que representa '
                    f'el {porcentaje_egreso:.1f}% de tus ingresos del mes.'
                )
            )
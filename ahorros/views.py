from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from categorias.models import Categoria
from .forms import AhorroMetaForm
from .models import AhorroMeta, AporteAhorro
from .services import (
    abandono_ahorro,
    actualizar_estados_usuario,
    calcular_campo_faltante,
    cuota_disponible_pago,
    find_cuota_disponible,
    generar_cuotas,
    hoy_local,
    pasar_cuotas_a_perdidas,
    recalcular_aportes,
    recalcular_aportes_restantes,
    recalcular_fechas_cuotas,
    resumen_meta,
)


def _pesos(valor):
    """Formatea un monto en pesos sin decimales y con punto de miles: $1.250.000."""
    return f"${valor:,.0f}".replace(',', '.')


# ── LISTAR AHORROS ──────────────────────────────────────────────────────────

@login_required
def listar(request):
    """Vista principal de ahorros: metas con su resumen, avisos y estadisticas.

    Antes de armar la vista pone al dia las cuotas vencidas, para que las
    cards y el detalle no muestren como pendiente una cuota que ya paso.
    Los filtros por estado y la busqueda se aplican en el navegador.
    """
    actualizar_estados_usuario(request.user)

    metas = list(
        AhorroMeta.objects.filter(usuario=request.user)
        .select_related('categoria')
        .prefetch_related(Prefetch('aporteahorro_set', queryset=AporteAhorro.objects.order_by('fecha_limite')))
        .order_by('-fecha_creacion')
    )
    hoy = hoy_local()
    for meta in metas:
        meta.resumen = resumen_meta(meta, list(meta.aporteahorro_set.all()), hoy)

    cerradas = (AhorroMeta.Estado.COMPLETADO.value, AhorroMeta.Estado.ABANDONADO.value)
    abiertas = [m for m in metas if m.estado not in cerradas]
    por_aportar = sorted(
        (m for m in abiertas if m.resumen['proxima_disponible']),
        key=lambda m: m.resumen['proxima'].fecha_limite,
    )
    con_proxima = sorted(
        (m for m in abiertas if m.resumen['proxima']),
        key=lambda m: m.resumen['proxima'].fecha_limite,
    )

    return render(request, "ahorros/lista.html", {
        "ahorros": metas,
        "total_ahorrado": sum((m.total_acumulado or Decimal('0')) for m in metas),
        "falta_abiertas": sum((m.resumen['restante'] for m in abiertas), Decimal('0')),
        "conteos": {
            'en_curso': len(abiertas),
            'completadas': sum(1 for m in metas if m.estado == AhorroMeta.Estado.COMPLETADO.value),
            'abandonadas': sum(1 for m in metas if m.estado == AhorroMeta.Estado.ABANDONADO.value),
            'todas': len(metas),
        },
        "por_aportar": por_aportar,
        "atrasadas": [m for m in abiertas if m.resumen['estado'] == 'atrasada'],
        "proxima_meta": con_proxima[0] if con_proxima else None,
    })


# ── CREAR AHORRO ────────────────────────────────────────────────────────────

@login_required
@transaction.atomic
def crear_ahorro(request):
    """Crea una nueva meta de ahorro con sus cuotas generadas."""
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == "POST":
        form = AhorroMetaForm(request.POST)

        if form.is_valid():
            ahorro = form.save(commit=False)
            ahorro.usuario = request.user

            fecha_meta, cuotas = calcular_campo_faltante(
                ahorro.fecha_meta,
                ahorro.cantidad_cuotas,
                ahorro.frecuencia,
                fecha_base=hoy_local(),
            )
            ahorro.fecha_meta = fecha_meta
            ahorro.cantidad_cuotas = cuotas
            ahorro.total_acumulado = Decimal('0.00')

            if not ahorro.estado:
                ahorro.estado = AhorroMeta.Estado.SIN_INICIAR.value

            ahorro.save()
            generar_cuotas(ahorro)

            if es_ajax:
                return JsonResponse({'ok': True, 'message': 'Meta creada'})
            return redirect("ahorros:listar_ahorros")

        if es_ajax:
            errores = {campo: list(errs) for campo, errs in form.errors.items()}
            return JsonResponse({'ok': False, 'errors': errores}, status=400)

    else:
        form = AhorroMetaForm()

    categorias_ahorro = Categoria.objects.filter(tipo=Categoria.TipoCategoria.AHORRO, activo=True)
    return render(request, "ahorros/crear.html", {"form": form, "categorias": categorias_ahorro})


# ── EDITAR AHORRO ───────────────────────────────────────────────────────────

@login_required
@transaction.atomic
def editar_ahorro(request, id):
    """Edita una meta existente y recalcula sus cuotas."""
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    ahorro = get_object_or_404(AhorroMeta, id=id, usuario=request.user)

    if request.method == "GET" and es_ajax:
        return JsonResponse({
            'ok': True,
            'ahorro': {
                'id': ahorro.id,
                'categoria_id': ahorro.categoria_id,
                'categoria_nombre': ahorro.categoria.nombre if ahorro.categoria else '',
                'monto_meta': str(ahorro.monto_meta),
                'total_acumulado': str(ahorro.total_acumulado),
                'frecuencia': ahorro.frecuencia,
                'fecha_meta': ahorro.fecha_meta.strftime('%Y-%m-%d') if ahorro.fecha_meta else '',
                'fecha_creacion': ahorro.fecha_creacion.strftime('%Y-%m-%d'),
                'cantidad_cuotas': ahorro.cantidad_cuotas,
                'cuotas_minimas': AporteAhorro.objects.filter(
                    ahorro=ahorro,
                    estado_ap=AporteAhorro.EstadoAp.APORTADO.value,
                    es_extraordinario=False
                ).count(),
                'descripcion': ahorro.descripcion or '',
            }
        })

    if request.method == "POST":
        form = AhorroMetaForm(request.POST, instance=ahorro)

        if form.is_valid():
            nuevo_monto_meta = form.cleaned_data['monto_meta']

            if nuevo_monto_meta < ahorro.total_acumulado:
                msg = (
                    f"El monto meta no puede ser menor a lo que ya ahorraste "
                    f"({_pesos(ahorro.total_acumulado)})."
                )
                return JsonResponse({'ok': False, 'errors': {'monto_meta': [msg]}}, status=400)

            cuotas_regulares_aportadas = AporteAhorro.objects.filter(
                ahorro=ahorro,
                estado_ap=AporteAhorro.EstadoAp.APORTADO.value,
                es_extraordinario=False
            ).count()

            ahorro = form.save(commit=False)
            ahorro.usuario = request.user

            fecha_meta, cuotas = calcular_campo_faltante(
                ahorro.fecha_meta,
                ahorro.cantidad_cuotas,
                ahorro.frecuencia,
                fecha_base=ahorro.fecha_creacion,
            )

            if cuotas < cuotas_regulares_aportadas:
                if request.POST.get('fecha_meta'):
                    msg = (
                        "La fecha es muy cercana: debe alcanzar al menos para los "
                        f"{cuotas_regulares_aportadas} aportes que ya hiciste."
                    )
                    error_key = 'fecha_meta'
                else:
                    msg = f"No puedes bajar de {cuotas_regulares_aportadas} cuotas porque ya las aportaste."
                    error_key = 'cantidad_cuotas'
                return JsonResponse({'ok': False, 'errors': {error_key: [msg]}}, status=400)

            ahorro.fecha_meta = fecha_meta
            ahorro.cantidad_cuotas = cuotas

            if ahorro.total_acumulado >= ahorro.monto_meta:
                ahorro.estado = AhorroMeta.Estado.COMPLETADO.value
            elif ahorro.estado == AhorroMeta.Estado.COMPLETADO.value:
                ahorro.estado = AhorroMeta.Estado.ACTIVO.value

            ahorro.save()
            recalcular_aportes(ahorro)
            recalcular_fechas_cuotas(ahorro)

            if es_ajax:
                return JsonResponse({'ok': True, 'message': 'Cambios guardados'})
            return redirect("ahorros:listar_ahorros")

        if es_ajax:
            errores = {campo: list(errs) for campo, errs in form.errors.items()}
            return JsonResponse({'ok': False, 'errors': errores}, status=400)

    else:
        form = AhorroMetaForm(instance=ahorro)

    categorias_ahorro = Categoria.objects.filter(tipo=Categoria.TipoCategoria.AHORRO, activo=True)
    return render(request, "ahorros/editar.html", {"form": form, "ahorro": ahorro, "categorias": categorias_ahorro})


# ── ELIMINAR AHORRO ─────────────────────────────────────────────────────────

@login_required
@transaction.atomic
def eliminar_ahorro(request, id):
    """Elimina una meta y todos sus aportes asociados."""
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    ahorro = get_object_or_404(AhorroMeta, id=id, usuario=request.user)

    if request.method == "POST":
        from dashboard.services import actualizar_resumen

        meses = {
            (f.month, f.year)
            for f in AporteAhorro.objects.filter(
                ahorro=ahorro, estado_ap=AporteAhorro.EstadoAp.APORTADO.value, fecha_aporte__isnull=False,
            ).values_list('fecha_aporte', flat=True)
        }
        AporteAhorro.objects.filter(ahorro=ahorro).delete()
        ahorro.delete()
        # El borrado en bloque no dispara las senales de AporteAhorro,
        # asi que el resumen de esos meses se recalcula aqui.
        for mes, anio in meses:
            actualizar_resumen(usuario=request.user, mes=mes, anio=anio)

        if es_ajax:
            return JsonResponse({'ok': True, 'message': 'Meta eliminada'})
        return redirect("ahorros:listar_ahorros")

    if es_ajax:
        return JsonResponse({
            'ok': True,
            'nombre': ahorro.categoria.nombre if ahorro.categoria else 'esta meta',
            'descripcion': ahorro.descripcion or '',
        })

    return render(request, "ahorros/eliminar.html", {"ahorro": ahorro})


# ── REGISTRAR APORTE ────────────────────────────────────────────────────────

def _error_aporte(mensaje):
    """Respuesta de error del registro de aportes, apta para mostrar al usuario."""
    return JsonResponse({"ok": False, "error": mensaje}, status=400)


@login_required
@transaction.atomic
def registrar_aporte(request, meta_id, aporte_id=None):
    """
    GET: Renderiza el parcial HTML de detalle de meta con sus cuotas.
    POST: Registra un aporte en una cuota (o uno extraordinario),
    actualiza el acumulado y el estado de la meta.
    """
    usuario = request.user
    ahorro = get_object_or_404(AhorroMeta.objects.select_related('categoria'), id=meta_id, usuario=usuario)

    if ahorro.estado != AhorroMeta.Estado.COMPLETADO.value:
        if pasar_cuotas_a_perdidas(ahorro):
            abandono_ahorro(ahorro)

    if request.method == "GET":
        cuotas_todas = list(AporteAhorro.objects.filter(ahorro=ahorro).order_by('fecha_limite'))
        resumen = resumen_meta(ahorro, cuotas_todas)
        proxima_id = resumen['proxima'].id if resumen['proxima'] else None

        numero = 0
        for c in cuotas_todas:
            if c.es_extraordinario:
                c.numero_real = None
            else:
                numero += 1
                c.numero_real = numero
            c.es_proxima = c.id == proxima_id

        def orden(c):
            """Cuotas por fecha limite; los aportes extra en la fecha en que se hicieron."""
            fecha = (c.fecha_aporte or c.fecha_registro) if c.es_extraordinario else c.fecha_limite
            return (fecha, c.es_extraordinario)
        cuotas_todas.sort(key=orden)

        idx = next((i for i, c in enumerate(cuotas_todas) if c.es_proxima), len(cuotas_todas) - 1)
        inicio = max(0, idx - 6)
        cuotas_a_mostrar = cuotas_todas[inicio:inicio + 16]

        return render(request, "ahorros/aporte.html", {
            "ahorro": ahorro,
            "resumen": resumen,
            "cuotas": cuotas_a_mostrar,
            "cuotas_antes": inicio,
            "cuotas_despues": max(0, len(cuotas_todas) - inicio - len(cuotas_a_mostrar)),
            "total_regulares": numero,
            "hoy": hoy_local(),
        })

    try:
        aporte_ingresado = Decimal((request.POST.get("aporte") or '0').strip().replace(',', '.'))
    except InvalidOperation:
        return _error_aporte("Escribe el monto del aporte solo con números.")
    if not aporte_ingresado.is_finite() or aporte_ingresado <= Decimal('0.00'):
        return _error_aporte("El monto del aporte debe ser mayor que cero.")

    if ahorro.estado == AhorroMeta.Estado.COMPLETADO.value:
        return _error_aporte("Esta meta de ahorro ya está completada.")
    if ahorro.categoria and not ahorro.categoria.activo:
        return _error_aporte("La categoría de esta meta está inactiva y no permite aportes.")

    monto_meta = ahorro.monto_meta or Decimal('0.00')
    acumulado_actual = ahorro.total_acumulado or Decimal('0.00')
    restante_meta = monto_meta - acumulado_actual
    if monto_meta > Decimal('0.00') and aporte_ingresado > restante_meta:
        return _error_aporte(f"El aporte supera lo que falta para la meta. Solo necesitas {_pesos(restante_meta)}.")

    hoy = hoy_local()

    from dashboard.services import obtener_disponible
    disponible_actual = obtener_disponible(usuario, hoy.month, hoy.year)
    if disponible_actual < aporte_ingresado:
        return _error_aporte(f"No tienes saldo suficiente para este aporte. Disponible: {_pesos(disponible_actual)}.")

    aporte_id = aporte_id or request.POST.get("aporte_id")
    es_extraordinario = request.POST.get('extraordinario') == 'true'

    if es_extraordinario:
        cuota = AporteAhorro(
            ahorro=ahorro,
            estado_ap=AporteAhorro.EstadoAp.PENDIENTE.value,
            fecha_limite=hoy,
            aporte_asignado=aporte_ingresado,
            es_extraordinario=True,
        )
    elif aporte_id:
        cuota = AporteAhorro.objects.select_for_update().filter(id=aporte_id, ahorro=ahorro).first()
        if cuota is None:
            return _error_aporte("No encontramos esa cuota.")
    else:
        cuota_temp = find_cuota_disponible(meta_id, usuario)
        if not cuota_temp:
            return _error_aporte("No hay una cuota disponible para aportar hoy.")
        cuota = AporteAhorro.objects.select_for_update().get(id=cuota_temp.id)

    if cuota.estado_ap == AporteAhorro.EstadoAp.PERDIDO.value:
        return _error_aporte(
            f"Esta cuota venció el {cuota.fecha_limite:%d/%m/%Y} y ya no se puede pagar. "
            "Puedes ponerte al día con un aporte extraordinario."
        )
    if cuota.estado_ap != AporteAhorro.EstadoAp.PENDIENTE.value or cuota.aporte is not None:
        return _error_aporte("Esta cuota ya tiene un aporte registrado.")
    if not es_extraordinario and not cuota_disponible_pago(cuota, ahorro.frecuencia):
        return _error_aporte("Esta cuota todavía no está habilitada para pago.")

    cuota.aporte = aporte_ingresado
    cuota.estado_ap = AporteAhorro.EstadoAp.APORTADO.value
    cuota.fecha_aporte = hoy
    cuota._es_extraordinario = es_extraordinario
    cuota.save()
    # La senal post_save de AporteAhorro actualiza el ResumenMensual del mes del aporte.

    total_acumulado = acumulado_actual + aporte_ingresado
    if monto_meta > Decimal('0.00'):
        total_acumulado = min(total_acumulado, monto_meta)
    ahorro.total_acumulado = total_acumulado

    if ahorro.estado in (AhorroMeta.Estado.SIN_INICIAR.value, AhorroMeta.Estado.ABANDONADO.value):
        ahorro.estado = AhorroMeta.Estado.ACTIVO.value

    completada = monto_meta > Decimal('0.00') and total_acumulado >= monto_meta
    if completada:
        ahorro.estado = AhorroMeta.Estado.COMPLETADO.value
        pendientes = AporteAhorro.objects.filter(
            ahorro=ahorro, estado_ap=AporteAhorro.EstadoAp.PENDIENTE.value, es_extraordinario=False,
        )
        cuotas_eliminadas = pendientes.count()
        if cuotas_eliminadas > 0:
            pendientes.delete()
            ahorro.cantidad_cuotas -= cuotas_eliminadas

    ahorro.save(update_fields=['total_acumulado', 'estado', 'cantidad_cuotas'])

    if not completada and (es_extraordinario or aporte_ingresado != (cuota.aporte_asignado or 0)):
        recalcular_aportes_restantes(ahorro)

    return JsonResponse({
        "ok": True,
        "message": "Meta completada. Lo lograste." if completada else "Aporte registrado",
        "completada": completada,
    })

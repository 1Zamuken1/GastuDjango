from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import AhorroMeta, AporteAhorro
from .forms import AhorroMetaForm, AporteAhorroForm
from decimal import Decimal
from django.db.models import Q, Sum
from dashboard.models import ResumenMensual
from categorias.models import Categoria
from datetime import date

from .services import (
    calcular_campo_faltante,
    generar_cuotas,
    recalcular_aportes,
    recalcular_aportes_restantes,
    recalcular_fechas_cuotas,
    pasar_cuotas_a_perdidas,
    abandono_ahorro,
    cuota_disponible_pago,
    find_cuota_disponible,
    obtener_aportes_por_meta,
)


# ── LISTAR AHORROS ──────────────────────────────────────────────────────────

@login_required
def listar(request):
    """Vista principal de ahorros: lista metas con estadisticas."""
    estado = request.GET.get("estado")
    texto = request.GET.get("texto")
    ahorros = AhorroMeta.objects.filter(usuario=request.user).select_related('categoria')
    
    if estado:
        ahorros = ahorros.filter(estado=estado)
        
    if texto:
        ahorros = ahorros.filter(
            Q(descripcion__icontains=texto) |
            Q(categoria__nombre__icontains=texto)
        ) 
           
    ahorros = ahorros.order_by('-fecha_creacion')
    
    total_ahorrado = ahorros.aggregate(total=Sum('total_acumulado'))['total'] or Decimal('0.00')
    cantidad_metas = ahorros.count()
    metas_completadas = ahorros.filter(estado=AhorroMeta.Estado.COMPLETADO.value).count()
    
    proxima_meta = AporteAhorro.objects.filter(
        ahorro__usuario=request.user, 
        estado_ap=AporteAhorro.EstadoAp.PENDIENTE.value
    ).order_by('fecha_limite').select_related('ahorro', 'ahorro__categoria').first()
    
    categorias_ahorro = Categoria.objects.filter(tipo=Categoria.TipoCategoria.AHORRO, activo=True)
    
    return render(request, "ahorros/lista.html", {
        "ahorros": ahorros,
        "estado": estado,
        "texto": texto,
        "total_ahorrado": total_ahorrado,
        "cantidad_metas": cantidad_metas,
        "metas_completadas": metas_completadas,
        "proxima_meta": proxima_meta,
        "categorias": categorias_ahorro,
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
                ahorro.frecuencia
            )
            ahorro.fecha_meta = fecha_meta
            ahorro.cantidad_cuotas = cuotas
            ahorro.total_acumulado = Decimal('0.00')

            if not ahorro.estado:
                ahorro.estado = AhorroMeta.Estado.SIN_INICIAR.value

            ahorro.save()
            generar_cuotas(ahorro)

            if es_ajax:
                return JsonResponse({'ok': True, 'message': 'Meta creada exitosamente'})
            return redirect("ahorros:listar_ahorros")

        else:
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

            # Validar que el nuevo monto meta no sea menor al total ya acumulado
            if nuevo_monto_meta < ahorro.total_acumulado:
                msg = (
                    f"El monto meta no puede ser menor al total ya acumulado "
                    f"(${ahorro.total_acumulado:,.0f}). "
                    f"Selecciona un monto mayor"
                )
                return JsonResponse({
                    'ok': False,
                    'errors': {'monto_meta': [msg]}
                }, status=400)

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
                ahorro.frecuencia
            )

            if cuotas < cuotas_regulares_aportadas:
                if request.POST.get('fecha_meta'):
                    msg = f"La fecha seleccionada es muy corta. Se requiere una fecha que permita abarcar al menos los {cuotas_regulares_aportadas} aportes ya realizados."
                    error_key = 'fecha_meta'
                else:
                    msg = f"No puedes reducir las cuotas a menos de {cuotas_regulares_aportadas} cuotas porque ya fueron aportadas."
                    error_key = 'cantidad_cuotas'

                return JsonResponse({
                    'ok': False,
                    'errors': {
                        error_key: [msg]
                    }
                }, status=400)

            ahorro.fecha_meta = fecha_meta
            ahorro.cantidad_cuotas = cuotas

            # Ajustar estado si el monto_meta editado altera el cumplimiento
            if ahorro.total_acumulado >= ahorro.monto_meta:
                ahorro.estado = AhorroMeta.Estado.COMPLETADO.value
            elif ahorro.estado == AhorroMeta.Estado.COMPLETADO.value and ahorro.total_acumulado < ahorro.monto_meta:
                ahorro.estado = AhorroMeta.Estado.ACTIVO.value

            ahorro.save()
            recalcular_aportes(ahorro)
            recalcular_fechas_cuotas(ahorro)

            if es_ajax:
                return JsonResponse({'ok': True, 'message': 'Meta actualizada exitosamente'})
            return redirect("ahorros:listar_ahorros")

        else:
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
        AporteAhorro.objects.filter(ahorro=ahorro).delete()
        ahorro.delete()
        if es_ajax:
            return JsonResponse({'ok': True, 'message': 'Meta eliminada exitosamente'})
        return redirect("ahorros:listar_ahorros")

    if es_ajax:
        return JsonResponse({
            'ok': True,
            'nombre': ahorro.categoria.nombre if ahorro.categoria else 'esta meta',
            'descripcion': ahorro.descripcion or '',
        })

    return render(request, "ahorros/eliminar.html", {"ahorro": ahorro})


# ── REGISTRAR APORTE ────────────────────────────────────────────────────────

@login_required
@transaction.atomic
def registrar_aporte(request, meta_id, aporte_id=None):
    """
    GET: Renderiza el parcial HTML de detalle de meta con tabla de cuotas.
    POST: Registra un aporte en una cuota, actualiza dashboard y estado.
    """
    usuario = request.user
    ahorro = get_object_or_404(AhorroMeta, id=meta_id, usuario=usuario)

    if request.method == "GET":
        
        cuotas_qs = AporteAhorro.objects.filter(ahorro=ahorro).order_by('fecha_limite')
        pagadas = cuotas_qs.filter(estado_ap=AporteAhorro.EstadoAp.APORTADO.value).count()
        perdidas = cuotas_qs.filter(estado_ap=AporteAhorro.EstadoAp.PERDIDO.value).count()
        pendientes = cuotas_qs.filter(estado_ap=AporteAhorro.EstadoAp.PENDIENTE.value).count()

        cuotas_todas = list(cuotas_qs)
        cuotas_totales = len(cuotas_todas)
        cuotas_regulares_total = cuotas_qs.filter(es_extraordinario=False).count()
        
        # Reordenar para la vista: Extraordinarios > APORTADOS > Resto
        def sort_key(c):
            return (
                not c.es_extraordinario,
                c.estado_ap != AporteAhorro.EstadoAp.APORTADO.value,
                c.fecha_limite
            )
        cuotas_todas.sort(key=sort_key)
        
        # Asignar numero_real DESPUÉS de reordenar para que los números sigan el orden visual
        numero_regular = 0
        for c in cuotas_todas:
            if not c.es_extraordinario:
                numero_regular += 1
                c.numero_real = numero_regular
            else:
                c.numero_real = None
        
        idx_pendiente = next((i for i, c in enumerate(cuotas_todas) if c.estado_ap == AporteAhorro.EstadoAp.PENDIENTE.value and not c.es_extraordinario), -1)
        
        if idx_pendiente != -1:
            start_idx = max(0, idx_pendiente - 5)
            end_idx = start_idx + 20
            if end_idx > cuotas_totales:
                end_idx = cuotas_totales
                start_idx = max(0, end_idx - 20)
            cuotas_a_mostrar = cuotas_todas[start_idx:end_idx]
        else:
            cuotas_a_mostrar = cuotas_todas[-20:] if cuotas_totales > 20 else cuotas_todas
            
        primera_pendiente = cuotas_todas[idx_pendiente] if idx_pendiente != -1 else None
        
        for c in cuotas_a_mostrar:
            c.is_disponible_pago = cuota_disponible_pago(c, ahorro.frecuencia, primera_pendiente=primera_pendiente)

        cuotas_ocultas = cuotas_totales - len(cuotas_a_mostrar)

        return render(request, "ahorros/aporte.html", {
            "ahorro": ahorro,
            "cuotas": cuotas_a_mostrar,
            "cuotas_totales": cuotas_regulares_total,
            "cuotas_ocultas": cuotas_ocultas,
            "pagadas": pagadas,
            "perdidas": perdidas,
            "pendientes": pendientes,
        })

    monto_input = request.POST.get("aporte")
    aporte_ingresado = Decimal(monto_input or '0.00')

    # Capturar aporte_id desde POST si viene de la tabla
    post_aporte_id = request.POST.get("aporte_id")
    if post_aporte_id and not aporte_id:
        aporte_id = post_aporte_id

    if aporte_ingresado <= Decimal('0.00'):
        return JsonResponse({"ok": False, "error": "El monto del aporte debe ser mayor que cero."})

    if ahorro.estado == AhorroMeta.Estado.COMPLETADO.value:
        return JsonResponse({"ok": False, "error": "Esta meta de ahorro ya ha sido completada."})

    monto_meta = ahorro.monto_meta or Decimal('0.00')
    total_acumulado_actual = ahorro.total_acumulado or Decimal('0.00')
    if monto_meta > Decimal('0.00'):
        restante_meta = monto_meta - total_acumulado_actual
        if aporte_ingresado > restante_meta:
            return JsonResponse({
                "ok": False,
                "error": f"El aporte supera el restante de la meta. Solo necesitas aportar ${restante_meta:,.2f}."
            })

    hoy = date.today()

    from dashboard.services import obtener_disponible
    disponible_actual = obtener_disponible(usuario, hoy.month, hoy.year)

    if disponible_actual < aporte_ingresado:
        return JsonResponse({"ok": False, "error": f"No tienes saldo disponible suficiente para realizar este aporte. Disponible actual: ${disponible_actual:,.2f}."})

    pasar_cuotas_a_perdidas(ahorro)

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
        cuota = AporteAhorro.objects.select_for_update().get(
            id=aporte_id, ahorro=ahorro
        )
    else:
        cuota_temp = find_cuota_disponible(meta_id, usuario)

        if not cuota_temp:
            return JsonResponse({"ok": False, "error": "No hay cuota disponible para aportar hoy."})

        cuota = AporteAhorro.objects.select_for_update().get(id=cuota_temp.id)

    if cuota.estado_ap != AporteAhorro.EstadoAp.PENDIENTE.value:
        return JsonResponse({"ok": False, "error": f"La cuota no esta disponible (estado={cuota.estado_ap})"})

    if cuota.aporte is not None:
        return JsonResponse({"ok": False, "error": "Esta cuota ya tiene un aporte registrado."})

    if not es_extraordinario and not cuota_disponible_pago(cuota, ahorro.frecuencia):
        return JsonResponse({"ok": False, "error": "La cuota no esta disponible para pago todavia."})

    # Registrar aporte
    cuota.aporte = aporte_ingresado
    cuota.estado_ap = AporteAhorro.EstadoAp.APORTADO.value
    cuota._es_extraordinario = es_extraordinario
    cuota.save()
    # El signal post_save de AporteAhorro se encarga de actualizar
    # el ResumenMensual (ingreso_neto, disponible, ganancia_acumulada, etc.)

    # Actualizar acumulado del ahorro
    total_acumulado = ahorro.total_acumulado or Decimal('0.00')
    total_acumulado += aporte_ingresado

    monto_meta = ahorro.monto_meta or Decimal('0.00')

    if monto_meta > Decimal('0.00') and total_acumulado > monto_meta:
        total_acumulado = monto_meta

    ahorro.total_acumulado = total_acumulado

    if ahorro.estado in [
        AhorroMeta.Estado.SIN_INICIAR.value,
        AhorroMeta.Estado.ABANDONADO.value,
    ]:
        ahorro.estado = AhorroMeta.Estado.ACTIVO.value

    if monto_meta > Decimal('0.00') and total_acumulado >= monto_meta:
        ahorro.estado = AhorroMeta.Estado.COMPLETADO.value
        pendientes = AporteAhorro.objects.filter(ahorro=ahorro, estado_ap=AporteAhorro.EstadoAp.PENDIENTE.value, es_extraordinario=False)
        cuotas_eliminadas = pendientes.count()
        if cuotas_eliminadas > 0:
            pendientes.delete()
            ahorro.cantidad_cuotas -= cuotas_eliminadas

    asignado = cuota.aporte_asignado or Decimal('0.00')
    if es_extraordinario or aporte_ingresado != asignado:
        recalcular_aportes_restantes(ahorro)

    abandono_ahorro(ahorro)

    ahorro.save(update_fields=['total_acumulado', 'estado', 'cantidad_cuotas'])

    return JsonResponse({"ok": True, "message": "Aporte registrado exitosamente"})
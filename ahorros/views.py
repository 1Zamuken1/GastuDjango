from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import AhorroMeta, AporteAhorro
from .forms import AhorroMetaForm, AporteAhorroForm
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta #pip install python-dateutil
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
import math
from django.db.models import Q, Sum
from dashboard.models import ResumenMensual
from categorias.models import Categoria

# LISTAR AHORROS

@login_required
def listar(request):
    estado = request.GET.get("estado")
    texto = request.GET.get("texto")
    ahorros = AhorroMeta.objects.filter(usuario=request.user)
    
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
    metas_completadas = ahorros.filter(estado=AhorroMeta.Estado.COMPLETADO).count()
    
    # Calcular la proxima_meta basándose en los aportes pendientes
    proxima_meta = AporteAhorro.objects.filter(
        ahorro__usuario=request.user, 
        estado_ap=AporteAhorro.EstadoAp.PENDIENTE
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
    

#validaciones para crear ahorro
def calcular_periodo(frecuencia):
    mapa = {
        'DIARIA': 1,
        'SEMANAL': 7,
        'QUINCENAL': 15,
        'MENSUAL': 30,
        'TRIMESTRAL': 90,
        'SEMESTRAL': 180,
        'ANUAL': 365
    }

    return mapa.get(frecuencia, 30)  # default mensual

def sumar_frecuencia(fecha, frecuencia):
    dias = calcular_periodo(frecuencia)
    return fecha + timedelta(days=dias)

def calcular_campo_faltante(fecha_meta, cuotas, frecuencia):
    hoy = date.today()

    if not fecha_meta and not cuotas:
        raise ValueError("Debes enviar fecha_meta o cuotas")

    #calcular cuotas
    if not cuotas:
        dias = max(1, (fecha_meta - hoy).days)
        periodo = calcular_periodo(frecuencia)
        cuotas = max(1, dias // periodo)

    #calcular fecha
    if not fecha_meta:
        fecha_calculada = hoy
        for _ in range(cuotas):
            fecha_calculada = sumar_frecuencia(fecha_calculada, frecuencia)
        return fecha_calculada, cuotas

    return fecha_meta, cuotas


def generar_cuotas_preview(ahorro):
    if ahorro.cantidad_cuotas <= 0:
        raise ValueError("La cantidad de cuotas debe ser mayor a 0")

    cuotas = []
    fecha = ahorro.fecha_creacion + timedelta(days=1)

    monto_total = ahorro.monto_meta or Decimal('0.00')
    cantidad = ahorro.cantidad_cuotas

    monto_base = Decimal('0.00')
    resto = Decimal('0.00')

    if monto_total > 0:
        monto_base = (monto_total / cantidad).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        total_calculado = monto_base * cantidad
        resto = monto_total - total_calculado

    for i in range(cantidad):
        if i > 0:
            fecha = sumar_frecuencia(fecha, ahorro.frecuencia)

        cuota = AporteAhorro(
            ahorro=ahorro,
            estado_ap=AporteAhorro.EstadoAp.PENDIENTE,
            fecha_limite=fecha,
            aporte_asignado=(
                monto_base + resto if i == cantidad - 1 else monto_base
            )
        )

        cuotas.append(cuota)

    return cuotas

def generar_cuotas(ahorro):
    cuotas = generar_cuotas_preview(ahorro)
    #  Asegurar relación 
    for c in cuotas:
        c.ahorro = ahorro
    # Guardar en BD
    AporteAhorro.objects.bulk_create(cuotas)
    return cuotas

# CREAR AHORRO

@login_required
@transaction.atomic
def crear_ahorro(request):

    if request.method == "POST":
        form = AhorroMetaForm(request.POST)

        if form.is_valid():

            #Crear entidad sin guardar 
            ahorro = form.save(commit=False)

            #Asignar usuario
            ahorro.usuario = request.user

            #calcular campo faltante 
            if ahorro.fecha_meta and ahorro.fecha_meta < date.today():
                raise ValueError("La fecha meta no puede ser pasada")
            
            fecha_meta, cuotas = calcular_campo_faltante(
                ahorro.fecha_meta,
                ahorro.cantidad_cuotas,
                ahorro.frecuencia
            )
            ahorro.fecha_meta = fecha_meta
            ahorro.cantidad_cuotas = cuotas

            # valores por defecto 
            ahorro.total_acumulado = Decimal('0.00')

            if not ahorro.estado:
                ahorro.estado = AhorroMeta.Estado.SIN_INICIAR

            ahorro.save()

            generar_cuotas(ahorro)

            return redirect("ahorros:listar_ahorros")

    else:
        form = AhorroMetaForm()

    return render(request, "ahorros/crear.html", {"form": form})


#validaciones para editar ahorro
def recalcular_aportes_restantes(ahorro):
    aportes = list(AporteAhorro.objects.filter(ahorro=ahorro).order_by('fecha_limite'))
    # sumar aportado
    aportado = sum(
        (a.aporte if a.aporte else Decimal('0.00'))
        for a in aportes
        if a.estado_ap == AporteAhorro.EstadoAp.APORTADO
    )
    monto_meta = ahorro.monto_meta or Decimal('0.00')
    restante = monto_meta - aportado

    if restante <= Decimal('0.00'):
        return
    
    # pendientes
    pendientes = [
        a for a in aportes
        if a.estado_ap == AporteAhorro.EstadoAp.PENDIENTE
    ]

    cuotas_faltantes = len(pendientes)

    if cuotas_faltantes == 0:
        return

    # base
    asignado_base = (restante / cuotas_faltantes).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    # asignar
    for p in pendientes:
        p.aporte_asignado = asignado_base

    AporteAhorro.objects.bulk_update(pendientes, ['aporte_asignado'])

    #corregir diferencia
    suma_asignados = sum(
        (p.aporte_asignado or Decimal('0.00'))
        for p in pendientes
    )

    diff = (restante - suma_asignados).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    if diff != Decimal('0.00') and pendientes:
        ultima = pendientes[-1]
        ultima.aporte_asignado = (ultima.aporte_asignado or Decimal('0.00')) + diff
        ultima.save()
        

def recalcular_aportes(ahorro):
    todas = list(AporteAhorro.objects.filter(ahorro=ahorro).order_by('fecha_limite'))
    # separar
    aportadas = [
        a for a in todas
        if a.estado_ap == AporteAhorro.EstadoAp.APORTADO
    ]
    pendientes = [
        a for a in todas
        if a.estado_ap in [
            AporteAhorro.EstadoAp.PENDIENTE,
            AporteAhorro.EstadoAp.PERDIDO
        ]
    ]
    # eliminar pendientes/perdidas
    if pendientes:
        AporteAhorro.objects.filter(id__in=[p.id for p in pendientes]).delete()
    # generar TODAS las cuotas nuevas
    cuotas_nuevas = generar_cuotas_preview(ahorro)
    cuotas_aportadas_count = len(aportadas)
    
    if len(cuotas_nuevas) < cuotas_aportadas_count:
        raise ValueError(
            "No se puede reducir cuotas por debajo de las ya aportadas"
        )

    # solo nuevas
    cuotas_a_registrar = cuotas_nuevas[cuotas_aportadas_count:]
    #asignar ahorro
    for c in cuotas_a_registrar:
        c.ahorro = ahorro
        
    if cuotas_a_registrar:
        AporteAhorro.objects.bulk_create(cuotas_a_registrar)

    recalcular_aportes_restantes(ahorro)


def recalcular_fechas_cuotas(ahorro):
    cuotas = list(
        AporteAhorro.objects
        .filter(ahorro=ahorro)
        .order_by('fecha_limite'))

    nuevas = generar_cuotas_preview(ahorro)

    if len(nuevas) < len(cuotas):
        raise ValueError("No hay suficientes cuotas nuevas para reasignar fechas")

    for i, cuota in enumerate(cuotas):
        if cuota.estado_ap == AporteAhorro.EstadoAp.APORTADO:
            continue 

        cuota.fecha_limite = nuevas[i].fecha_limite

    AporteAhorro.objects.bulk_update(cuotas, ['fecha_limite'])  
#  EDITAR AHORRO
@login_required
@transaction.atomic
def editar_ahorro(request, id):
    ahorro = get_object_or_404(AhorroMeta,id=id,usuario=request.user)

    if request.method == "POST":
        form = AhorroMetaForm(request.POST, instance=ahorro)

        if form.is_valid():
            ahorro = form.save(commit=False)
            ahorro.usuario = request.user
            
            if ahorro.frecuencia is None:
                raise ValueError("La frecuencia es obligatoria")
            
            fecha_meta, cuotas = calcular_campo_faltante(
                ahorro.fecha_meta,
                ahorro.cantidad_cuotas,
                ahorro.frecuencia
            )
            ahorro.fecha_meta = fecha_meta
            ahorro.cantidad_cuotas = cuotas
            
            ahorro.save()
            recalcular_aportes(ahorro)
            recalcular_fechas_cuotas(ahorro)
            return redirect("ahorros:listar_ahorros")
    else:
        form = AhorroMetaForm(instance=ahorro)

    return render(request, "ahorros/editar.html", {"form": form,"ahorro": ahorro})
    
    
# ELIMINAR AHORRO
@login_required
@transaction.atomic
def eliminar_ahorro(request, id):
    ahorro = get_object_or_404(AhorroMeta,id=id,usuario=request.user)
    
    if request.method == "POST":
        # eliminar aportes relacionados
        AporteAhorro.objects.filter(ahorro=ahorro).delete()
        # eliminar ahorro
        ahorro.delete()
        return redirect("ahorros:listar_ahorros")
        
    return render(request, "ahorros/eliminar.html", {"ahorro": ahorro})


#   APORTES

#listas aportes de un ahorro
def obtener_aportes_por_meta(meta_id, usuario):
    
    meta = get_object_or_404(AhorroMeta,id=meta_id,usuario=usuario)
    aportes = AporteAhorro.objects.filter(ahorro=meta).order_by('fecha_limite')
    return aportes

#pasar cuotas a perdidas
def pasar_cuotas_a_perdidas(ahorro):
   # Busca todas las cuotas pendientes cuya fecha límite es menor a hoy y las marca como PERDIDO
    hoy = date.today()
   # Filtramos: mismo ahorro, estado pendiente y fecha ya pasada
    cuotas_vencidas = AporteAhorro.objects.filter(
        ahorro=ahorro,
        estado_ap=AporteAhorro.EstadoAp.PENDIENTE,
        fecha_limite__lt=hoy
        )
    cuotas_vencidas.update(estado_ap=AporteAhorro.EstadoAp.PERDIDO)
    
def cuota_disponible_pago(cuota, frecuencia):
    
    if cuota is None:
        return False
    
    hoy = date.today()
    limite = cuota.fecha_limite
    if frecuencia == AhorroMeta.Frecuencia.DIARIA:
        return limite <= hoy + timedelta(days=3)
    elif frecuencia == AhorroMeta.Frecuencia.SEMANAL:
        return limite <= hoy + timedelta(days=7)
    elif frecuencia == AhorroMeta.Frecuencia.QUINCENAL:
        return limite <= hoy + timedelta(days=15)
    elif frecuencia == AhorroMeta.Frecuencia.MENSUAL:
        return limite <= hoy + relativedelta(months=1)
    elif frecuencia == AhorroMeta.Frecuencia.TRIMESTRAL:
        return limite <= hoy + relativedelta(months=3)
    elif frecuencia == AhorroMeta.Frecuencia.SEMESTRAL:
        return limite <= hoy + relativedelta(months=6)
    elif frecuencia == AhorroMeta.Frecuencia.ANUAL:
        return limite <= hoy + relativedelta(years=1)
    return limite <= hoy + timedelta(days=3) 

def abandono_ahorro(ahorro):
    todas = list(AporteAhorro.objects.filter(ahorro=ahorro).order_by('fecha_limite'))
    
    if len(todas) < 3:
        return
    
    ultimas_3 = todas[-3:]
    if all(a.estado_ap == AporteAhorro.EstadoAp.PERDIDO for a in ultimas_3):
        ahorro.estado = AhorroMeta.Estado.ABANDONADO
        
def find_cuota_disponible(meta_id, usuario):
    meta = get_object_or_404(AhorroMeta,id=meta_id,usuario=usuario)
    cuotas = AporteAhorro.objects.filter(ahorro=meta).order_by('fecha_limite')

    for c in cuotas:
        if c.estado_ap == AporteAhorro.EstadoAp.PENDIENTE:
            if cuota_disponible_pago(c, meta.frecuencia):
                return c
    return None

def obtener_cuota_disponible(meta_id, usuario):
    cuota = find_cuota_disponible(meta_id, usuario)
    return cuota 


# REGISTRAR APORTE
@login_required
@transaction.atomic
def registrar_aporte(request, meta_id, aporte_id=None):
    usuario = request.user
    ahorro = get_object_or_404(AhorroMeta, id=meta_id, usuario=usuario)

    if request.method == "GET":
        cuotas = AporteAhorro.objects.filter(ahorro=ahorro).order_by('fecha_limite')
        pagadas = cuotas.filter(estado_ap=AporteAhorro.EstadoAp.APORTADO).count()
        perdidas = cuotas.filter(estado_ap=AporteAhorro.EstadoAp.PERDIDO).count()
        pendientes = cuotas.filter(estado_ap=AporteAhorro.EstadoAp.PENDIENTE).count()

        return render(request, "ahorros/aporte.html", {
            "ahorro": ahorro,
            "cuotas": cuotas,
            "pagadas": pagadas,
            "perdidas": perdidas,
            "pendientes": pendientes
        })

    monto_input = request.POST.get("aporte")
    aporte_ingresado = Decimal(monto_input or '0.00')
    
    # Capturar aporte_id desde POST si viene de la tabla
    post_aporte_id = request.POST.get("aporte_id")
    if post_aporte_id and not aporte_id:
        aporte_id = post_aporte_id

    # Preparar el contexto base en caso de error
    cuotas = AporteAhorro.objects.filter(ahorro=ahorro).order_by('fecha_limite')
    pagadas = cuotas.filter(estado_ap=AporteAhorro.EstadoAp.APORTADO).count()
    perdidas = cuotas.filter(estado_ap=AporteAhorro.EstadoAp.PERDIDO).count()
    pendientes = cuotas.filter(estado_ap=AporteAhorro.EstadoAp.PENDIENTE).count()
    ctx_error = {
        "ahorro": ahorro,
        "cuotas": cuotas,
        "pagadas": pagadas,
        "perdidas": perdidas,
        "pendientes": pendientes
    }

    if aporte_ingresado <= Decimal('0.00'):
        ctx_error["error"] = "El monto del aporte debe ser mayor que cero."
        return render(request, "ahorros/aporte.html", ctx_error)

    hoy = date.today()

    resumen = ResumenMensual.objects.filter(
        usuario=usuario,
        mes=hoy.month,
        anio=hoy.year
    ).select_for_update().first()

    if not resumen:
        ctx_error["error"] = "No existe un resumen mensual"
        return render(request, "ahorros/aporte.html", ctx_error)

    if resumen.disponible <= Decimal('0.00'):
        ctx_error["error"] = "No tienes saldo disponible para realizar aportes."
        return render(request, "ahorros/aporte.html", ctx_error)

    pasar_cuotas_a_perdidas(ahorro)

    if aporte_id:
        cuota = AporteAhorro.objects.select_for_update().get(
            id=aporte_id, ahorro=ahorro
        )
    else:
        cuota_temp = find_cuota_disponible(meta_id, usuario)

        if not cuota_temp:
            ctx_error["error"] = "No hay cuota disponible para aportar hoy."
            return render(request, "ahorros/aporte.html", ctx_error)

        cuota = AporteAhorro.objects.select_for_update().get(id=cuota_temp.id)

    if cuota.estado_ap != AporteAhorro.EstadoAp.PENDIENTE:
        ctx_error["error"] = f"La cuota no está disponible (estado={cuota.estado_ap})"
        return render(request, "ahorros/aporte.html", ctx_error)

    if cuota.aporte is not None:
        ctx_error["error"] = "Esta cuota ya tiene un aporte registrado."
        return render(request, "ahorros/aporte.html", ctx_error)

    if not cuota_disponible_pago(cuota, ahorro.frecuencia):
        ctx_error["error"] = "La cuota no está disponible para pago todavía."
        return render(request, "ahorros/aporte.html", ctx_error)
        
    # registrar aporte
    cuota.aporte = aporte_ingresado
    cuota.estado_ap = AporteAhorro.EstadoAp.APORTADO
    cuota.save()

    # ACTUALIZAR DASHBOARD
    resumen.disponible -= aporte_ingresado
    resumen.total_ahorros += aporte_ingresado
    resumen.save()

    # actualizar acumulado ahorro
    total_acumulado = ahorro.total_acumulado or Decimal('0.00')
    total_acumulado += aporte_ingresado

    monto_meta = ahorro.monto_meta or Decimal('0.00')

    if monto_meta > Decimal('0.00') and total_acumulado > monto_meta:
        total_acumulado = monto_meta

    ahorro.total_acumulado = total_acumulado

    if ahorro.estado in [
        AhorroMeta.Estado.SIN_INICIAR,
        AhorroMeta.Estado.ABANDONADO
    ]:
        ahorro.estado = AhorroMeta.Estado.ACTIVO

    if monto_meta > Decimal('0.00') and total_acumulado >= monto_meta:
        ahorro.estado = AhorroMeta.Estado.COMPLETADO

    asignado = cuota.aporte_asignado or Decimal('0.00')
    if aporte_ingresado != asignado:
        recalcular_aportes_restantes(ahorro)

    abandono_ahorro(ahorro)

    ahorro.save()

    return redirect("ahorros:listar_ahorros")
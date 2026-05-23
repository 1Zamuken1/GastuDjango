from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Max, Sum
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from categorias.models import Categoria
from dashboard.services import obtener_disponible
from gastu_django.constants import MESES_ES
from .forms import MovimientoForm
from .models import Movimiento


def _build_categorias_con_totales(usuario, tipo, mes, anio):
    """
    Calcula las categorías con sus totales para un usuario, tipo y mes dados.

    Devuelve una tupla (categorias_con_totales, total_mes) donde
    categorias_con_totales es una lista de dicts con:
    - categoria: instancia de Categoria
    - total: Decimal
    - cantidad: int
    - porcentaje: float (0-100, redondeado a 1 decimal)
    - ultimo_registro: date
    """
    total_mes = (
        Movimiento.objects
        .filter(usuario=usuario, tipo=tipo, fecha_registro__month=mes, fecha_registro__year=anio)
        .aggregate(total=Sum('monto'))['total'] or Decimal('0')
    )

    cats_qs = (
        Movimiento.objects
        .filter(usuario=usuario, tipo=tipo, fecha_registro__month=mes, fecha_registro__year=anio)
        .values('categoria')
        .annotate(total=Sum('monto'), cantidad=Count('id'), ultimo_registro=Max('fecha_registro'))
        .order_by('-total')
    )

    cat_ids = [cd['categoria'] for cd in cats_qs]
    cats_map = {c.pk: c for c in Categoria.objects.filter(pk__in=cat_ids)}

    resultado = []
    for cd in cats_qs:
        porcentaje = round(float(cd['total'] / total_mes * 100), 1) if total_mes > 0 else 0.0
        resultado.append({
            'categoria': cats_map[cd['categoria']],
            'total': cd['total'],
            'cantidad': cd['cantidad'],
            'porcentaje': porcentaje,
            'ultimo_registro': cd['ultimo_registro'],
        })

    return resultado, total_mes


@login_required
def lista_ingresos(request):
    """Lista de ingresos del mes actual u opcionalmente del mes seleccionado agrupados por categoría."""
    hoy = timezone.localdate()
    try:
        mes = int(request.GET.get('mes', hoy.month))
        anio = int(request.GET.get('anio', hoy.year))
        if mes < 1 or mes > 12:
            mes = hoy.month
    except (ValueError, TypeError):
        mes, anio = hoy.month, hoy.year

    categorias_con_totales, total_mes = _build_categorias_con_totales(
        request.user, 'INGRESO', mes, anio
    )

    cantidad_mes = sum(cd['cantidad'] for cd in categorias_con_totales)
    promedio_mes = (
        round(total_mes / cantidad_mes, 2)
        if cantidad_mes > 0
        else Decimal('0')
    )

    return render(request, 'movimientos/ingresos.html', {
        'categorias_con_totales': categorias_con_totales,
        'total_mes': total_mes,
        'cantidad_mes': cantidad_mes,
        'promedio_mes': promedio_mes,
        'categorias_disponibles': Categoria.objects.filter(activo=True, tipo='INGRESO', es_sistema=False).order_by('nombre'),
        'mes_nombre': MESES_ES[mes],
        'mes_numero': mes,
        'anio': anio,
        'hoy': hoy,
    })


@login_required
def lista_egresos(request):
    """Lista de egresos del mes actual u opcionalmente del mes seleccionado agrupados por categoría."""
    hoy = timezone.localdate()
    try:
        mes = int(request.GET.get('mes', hoy.month))
        anio = int(request.GET.get('anio', hoy.year))
        if mes < 1 or mes > 12:
            mes = hoy.month
    except (ValueError, TypeError):
        mes, anio = hoy.month, hoy.year

    categorias_con_totales, total_mes = _build_categorias_con_totales(
        request.user, 'EGRESO', mes, anio
    )

    cantidad_mes = sum(cd['cantidad'] for cd in categorias_con_totales)
    promedio_mes = (
        round(total_mes / cantidad_mes, 2)
        if cantidad_mes > 0
        else Decimal('0')
    )

    disponible = obtener_disponible(request.user, mes, anio)

    return render(request, 'movimientos/egresos.html', {
        'categorias_con_totales': categorias_con_totales,
        'total_mes': total_mes,
        'cantidad_mes': cantidad_mes,
        'promedio_mes': promedio_mes,
        'disponible': disponible,
        'categorias_disponibles': Categoria.objects.filter(activo=True, tipo='EGRESO', es_sistema=False).order_by('nombre'),
        'mes_nombre': MESES_ES[mes],
        'mes_numero': mes,
        'anio': anio,
        'hoy': hoy,
    })


@login_required
@require_POST
def guardar_movimiento(request, pk=None):
    """
    Crea o edita un movimiento según si se recibe pk.

    Detecta el tipo desde el POST para filtrar las categorías correctas
    en la validación del form.

    Para egresos calcula el disponible del mes actual (ingresos - egresos) y lo
    pasa al form para que valide que el monto no lo supere. En edición, el monto
    original del egreso se descuenta del total antes de comparar, para que editar
    un egreso existente no bloquee falsamente la validación.
    """
    instancia = get_object_or_404(Movimiento, pk=pk, usuario=request.user) if pk else None
    tipo_movimiento = request.POST.get('tipo')

    disponible = None
    if tipo_movimiento == 'EGRESO':
        hoy = timezone.localdate()
        mes, anio = hoy.month, hoy.year
        monto_original = instancia.monto if instancia and instancia.tipo == 'EGRESO' else None
        disponible = obtener_disponible(request.user, mes, anio, monto_original=monto_original)

    form = MovimientoForm(
        request.POST,
        instance=instancia,
        tipo_movimiento=tipo_movimiento,
        disponible=disponible,
    )

    if form.is_valid():
        mov = form.save(commit=False)
        mov.usuario = request.user
        mov.save()
        return JsonResponse({
            'ok': True,
            'id': mov.id,
            'descripcion': mov.descripcion,
            'monto': str(mov.monto),
            'monto_fmt': f"${mov.monto:,.0f}",
            'fecha': mov.fecha_registro.strftime('%d %b %Y'),
            'fecha_raw': mov.fecha_registro.isoformat(),
            'categoria_id': mov.categoria_id,
            'categoria_nombre': mov.categoria.nombre,
            'tipo': mov.tipo,
        })

    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def eliminar_movimiento(request, pk):
    """Elimina un movimiento. Solo el dueño puede eliminarlo."""
    try:
        mov = Movimiento.objects.get(pk=pk, usuario=request.user)
    except Movimiento.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Movimiento no encontrado'}, status=404)
    
    mov.delete()
    return JsonResponse({'ok': True, 'id': pk})


@login_required
def registros_por_categoria(request):
    categoria_id = request.GET.get('categoria')
    
    # Guard: categoria_id obligatorio
    if not categoria_id:
        return JsonResponse({'error': 'categoria requerida'}, status=400)
    
    try:
        pagina = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        pagina = 1
    
    PER_PAGE = 10

    qs = Movimiento.objects.filter(
        usuario=request.user,
        categoria_id=categoria_id,
    ).order_by('-fecha_registro')

    paginator = Paginator(qs, PER_PAGE)
    page = paginator.get_page(pagina)

    return JsonResponse({
        'registros': [
            {
                'id': m.id,
                'descripcion': m.descripcion or 'Sin descripción',
                'fecha': m.fecha_registro.strftime('%d %b %Y'),
                'fecha_raw': m.fecha_registro.isoformat(),
                'monto': str(m.monto),
                'monto_fmt': f"${m.monto:,.0f}",
                'tipo': m.tipo,
                'categoria_id': m.categoria_id,
            }
            for m in page
        ],
        'total': paginator.count,
        'total_paginas': paginator.num_pages,
        'desde': page.start_index(),
        'hasta': page.end_index(),
    })


@login_required
def resumen_movimientos(request):
    """
    Devuelve JSON con los totales y categorías del mes actual para un tipo dado.

    GET param: tipo — 'INGRESO' o 'EGRESO'

    Usado por el frontend para actualizar el grid de categorías y el hero
    después de un CRUD sin recargar la página.
    """
    tipo = request.GET.get('tipo', '').upper()
    if tipo not in ('INGRESO', 'EGRESO'):
        return JsonResponse({'ok': False, 'error': 'tipo inválido'}, status=400)

    hoy = timezone.localdate()
    mes, anio = hoy.month, hoy.year

    categorias_con_totales, total_mes = _build_categorias_con_totales(
        request.user, tipo, mes, anio
    )

    cantidad_mes = sum(cd['cantidad'] for cd in categorias_con_totales)
    promedio_mes = round(total_mes / cantidad_mes, 2) if cantidad_mes > 0 else 0

    return JsonResponse({
        'ok': True,
        'total_mes': str(total_mes),
        'cantidad_mes': cantidad_mes,
        'promedio_mes': str(promedio_mes),
        'categorias': [
            {
                'id': cd['categoria'].id,
                'nombre': cd['categoria'].nombre,
                'total': str(cd['total']),
                'total_fmt': f"${cd['total']:,.0f}",
                'cantidad': cd['cantidad'],
                'porcentaje': cd['porcentaje'],
                'ultimo_registro': cd['ultimo_registro'].strftime('%d %b %Y'),
            }
            for cd in categorias_con_totales
        ],
    })


def _detectar_tipo_query(q):
    """
    Clasifica el texto de busqueda en uno de tres tipos:
      ('fecha', date)     — si q coincide con dd/mm/aaaa o dd/mm/aa
      ('monto', Decimal)  — si q es un numero positivo
      ('texto', str)      — cualquier otro texto libre

    Centraliza la deteccion para que sea facil de testear y extender.
    """
    from datetime import datetime
    from decimal import Decimal, InvalidOperation

    for fmt in ('%d/%m/%Y', '%d/%m/%y'):
        try:
            return ('fecha', datetime.strptime(q, fmt).date())
        except ValueError:
            pass

    try:
        val = Decimal(q.replace(',', '.'))
        if val > 0:
            return ('monto', val)
    except InvalidOperation:
        pass

    return ('texto', q)


@login_required
def buscar_registros(request):
    """
    Busca movimientos del usuario por descripcion, monto o fecha.

    GET params:
    - q    : texto de busqueda
    - tipo : INGRESO o EGRESO

    Formatos de fecha aceptados: dd/mm/aaaa o dd/mm/aa
    Para monto busca coincidencia exacta como Decimal.
    Para fecha usa __date= para compatibilidad con DateTimeField.
    Para texto usa icontains en descripcion.
    """
    from django.db.models import Q

    q    = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '').upper()

    if not q or tipo not in ('INGRESO', 'EGRESO'):
        return JsonResponse({'ok': False, 'error': 'parametros invalidos'}, status=400)

    qs = Movimiento.objects.filter(
        usuario=request.user, tipo=tipo
    ).select_related('categoria')

    tipo_query, valor = _detectar_tipo_query(q)

    if tipo_query == 'fecha':
        # __date= funciona tanto en DateField como DateTimeField
        qs = qs.filter(fecha_registro__date=valor)
    elif tipo_query == 'monto':
        qs = qs.filter(Q(monto=valor) | Q(descripcion__icontains=q))
    else:
        qs = qs.filter(descripcion__icontains=valor)

    # Agrupar resultados por categoria
    categorias_map = {}
    for m in qs.order_by('-fecha_registro'):
        cid = m.categoria_id
        if cid not in categorias_map:
            categorias_map[cid] = {
                'categoria_id': cid,
                'categoria_nombre': m.categoria.nombre,
                'registros': [],
            }
        categorias_map[cid]['registros'].append({
            'id': m.id,
            'descripcion': m.descripcion,
            'fecha': m.fecha_registro.strftime('%d %b %Y'),
            'fecha_raw': m.fecha_registro.date().isoformat(),
            'monto': str(m.monto),
            'monto_fmt': f"${m.monto:,.0f}",
            'categoria_id': m.categoria_id,
        })

    return JsonResponse({
        'ok': True,
        'categoria_ids': list(categorias_map.keys()),
        'resultados': list(categorias_map.values()),
    })
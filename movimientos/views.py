from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q, Sum

from .models import Movimiento
from .forms import MovimientoForm
from categorias.models import Categoria   # ← FIX: import correcto desde categorias


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _movimiento_dict(mov):
    """Serializa un Movimiento para respuestas JSON."""
    return {
        'id':               mov.id,
        'monto':            str(mov.monto),
        'monto_fmt':        f"${mov.monto:,.0f}",
        'descripcion':      mov.descripcion or '',
        'categoria_id':     mov.categoria.id,
        'categoria_nombre': mov.categoria.nombre,
        'fecha':            mov.fecha_registro.strftime('%d/%m/%Y'),
        'tipo':             mov.tipo,
    }


def _total_categoria(user, categoria, tipo):
    """Total activo de una categoría para el usuario."""
    return Movimiento.objects.filter(
        usuario=user, categoria=categoria, tipo=tipo, activo=True,
    ).aggregate(t=Sum('monto'))['t'] or 0


# ─────────────────────────────────────────────────────────────
# Listas
# ─────────────────────────────────────────────────────────────

@login_required
def lista_ingresos(request):
    categorias = Categoria.objects.filter(
        tipo='INGRESO',
        activo=True,
        movimientos__usuario=request.user,
        movimientos__activo=True,
    ).annotate(
        total_registros=Count(
            'movimientos',
            filter=Q(movimientos__usuario=request.user, movimientos__activo=True),
        )
    ).distinct()

    todas_categorias = Categoria.objects.filter(tipo='INGRESO', activo=True)

    return render(request, 'movimientos/ingresos.html', {
        'categorias':       categorias,
        'todas_categorias': todas_categorias,
        'tipo':             'INGRESO',
    })


@login_required
def lista_egresos(request):
    categorias = Categoria.objects.filter(
        tipo='EGRESO',
        activo=True,
        movimientos__usuario=request.user,
        movimientos__activo=True,
    ).annotate(
        total_registros=Count(
            'movimientos',
            filter=Q(movimientos__usuario=request.user, movimientos__activo=True),
        )
    ).distinct()

    todas_categorias = Categoria.objects.filter(tipo='EGRESO', activo=True)

    return render(request, 'movimientos/egresos.html', {
        'categorias':       categorias,
        'todas_categorias': todas_categorias,
        'tipo':             'EGRESO',
    })


# ─────────────────────────────────────────────────────────────
# Detalle de categoría
# ─────────────────────────────────────────────────────────────

@login_required
def detalle_categoria(request, categoria_id, tipo):
    categoria = get_object_or_404(Categoria, pk=categoria_id, activo=True)
    movimientos = (
        Movimiento.objects
        .filter(usuario=request.user, categoria=categoria, activo=True)
        .order_by('-fecha_registro')
    )
    total = sum(m.monto for m in movimientos)
    todas_categorias = Categoria.objects.filter(tipo=tipo, activo=True)

    return render(request, 'movimientos/detalle_categoria.html', {
        'categoria':        categoria,
        'movimientos':      movimientos,
        'total':            total,
        'tipo':             tipo,
        'todas_categorias': todas_categorias,
    })


# ─────────────────────────────────────────────────────────────
# CRUD — AJAX (JsonResponse) o POST tradicional como fallback
# ─────────────────────────────────────────────────────────────

@login_required
def crear_movimiento(request, tipo):
    """
    Crea un movimiento.

    AJAX success → { ok, movimiento, total_cat, cat_registros, cat_id,
                     cat_nombre, cat_nueva }
    AJAX error  → { ok: false, errors: {campo: [msg]} }
    """
    if request.method != 'POST':
        return redirect(
            'movimientos:lista_ingresos' if tipo == 'INGRESO'
            else 'movimientos:lista_egresos'
        )

    form = MovimientoForm(tipo=tipo, usuario=request.user, data=request.POST)

    if form.is_valid():
        mov = form.save(commit=False)
        mov.usuario = request.user
        mov.save()

        if _is_ajax(request):
            total_cat  = _total_categoria(request.user, mov.categoria, tipo)
            count_cat  = Movimiento.objects.filter(
                usuario=request.user, categoria=mov.categoria, activo=True,
            ).count()
            return JsonResponse({
                'ok':            True,
                'movimiento':    _movimiento_dict(mov),
                'total_cat':     f"${total_cat:,.0f}",
                'cat_registros': count_cat,
                'cat_id':        mov.categoria.id,
                'cat_nombre':    mov.categoria.nombre,
                'cat_nueva':     count_cat == 1,
            })

        messages.success(request, f'{"Ingreso" if tipo == "INGRESO" else "Egreso"} registrado.')
        return redirect(
            'movimientos:detalle_categoria_ingreso' if tipo == 'INGRESO'
            else 'movimientos:detalle_categoria_egreso',
            categoria_id=mov.categoria.id,
        )

    if _is_ajax(request):
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    messages.error(request, 'Corrige los errores del formulario.')
    return redirect(
        'movimientos:lista_ingresos' if tipo == 'INGRESO'
        else 'movimientos:lista_egresos'
    )


@login_required
def editar_movimiento(request, movimiento_id):
    """
    GET AJAX → devuelve datos del movimiento para pre-poblar el modal.
    POST AJAX → guarda y devuelve movimiento actualizado + totales.
    """
    mov = get_object_or_404(
        Movimiento, pk=movimiento_id, usuario=request.user, activo=True,
    )
    tipo = mov.tipo

    if request.method == 'POST':
        form = MovimientoForm(
            tipo=tipo, usuario=request.user, data=request.POST, instance=mov,
        )
        if form.is_valid():
            mov = form.save()

            if _is_ajax(request):
                total_cat = _total_categoria(request.user, mov.categoria, tipo)
                count_cat = Movimiento.objects.filter(
                    usuario=request.user, categoria=mov.categoria, activo=True,
                ).count()
                return JsonResponse({
                    'ok':            True,
                    'movimiento':    _movimiento_dict(mov),
                    'total_cat':     f"${total_cat:,.0f}",
                    'cat_registros': count_cat,
                })

            messages.success(request, 'Movimiento actualizado.')
            return redirect(
                'movimientos:detalle_categoria_ingreso' if tipo == 'INGRESO'
                else 'movimientos:detalle_categoria_egreso',
                categoria_id=mov.categoria.id,
            )

        if _is_ajax(request):
            return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

        messages.error(request, 'Corrige los errores del formulario.')

    # GET — devuelve datos para el modal
    if _is_ajax(request):
        return JsonResponse({'ok': True, 'movimiento': _movimiento_dict(mov)})

    form = MovimientoForm(tipo=tipo, usuario=request.user, instance=mov)
    return render(request, 'movimientos/form_movimiento.html', {
        'form': form, 'tipo': tipo, 'movimiento': mov,
    })


@login_required
def eliminar_movimiento(request, movimiento_id):
    """Soft delete. AJAX → JSON; tradicional → redirect."""
    mov = get_object_or_404(
        Movimiento, pk=movimiento_id, usuario=request.user, activo=True,
    )
    tipo         = mov.tipo
    categoria_id = mov.categoria.id

    if request.method == 'POST':
        mov.activo = False
        mov.save()

        if _is_ajax(request):
            total_cat = _total_categoria(request.user, mov.categoria, tipo)
            count_cat = Movimiento.objects.filter(
                usuario=request.user, categoria=mov.categoria, activo=True,
            ).count()
            return JsonResponse({
                'ok':            True,
                'id':            movimiento_id,
                'total_cat':     f"${total_cat:,.0f}",
                'cat_registros': count_cat,
                'cat_vacia':     count_cat == 0,
                'cat_id':        categoria_id,
            })

        messages.success(request, 'Movimiento eliminado.')
        return redirect(
            'movimientos:detalle_categoria_ingreso' if tipo == 'INGRESO'
            else 'movimientos:detalle_categoria_egreso',
            categoria_id=categoria_id,
        )

    if _is_ajax(request):
        return JsonResponse({'ok': True, 'movimiento': _movimiento_dict(mov)})

    return render(request, 'movimientos/confirmar_eliminar.html', {
        'movimiento': mov, 'tipo': tipo,
    })
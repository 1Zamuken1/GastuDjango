from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Movimiento, Categoria
from .forms import MovimientoForm


@login_required
def lista_ingresos(request):
    """
    Muestra las categorías de ingreso que tienen al menos
    un movimiento activo del usuario autenticado.
    """
    categorias = Categoria.objects.filter(
        tipo=Categoria.TipoCategoria.INGRESO,
        activo=True,
        movimientos__usuario=request.user,
        movimientos__activo=True
    ).distinct()

    return render(request, 'movimientos/ingresos.html', {
        'categorias': categorias,
        'tipo': 'INGRESO'
    })


@login_required
def lista_egresos(request):
    """
    Muestra las categorías de egreso que tienen al menos
    un movimiento activo del usuario autenticado.
    """
    categorias = Categoria.objects.filter(
        tipo=Categoria.TipoCategoria.EGRESO,
        activo=True,
        movimientos__usuario=request.user,
        movimientos__activo=True
    ).distinct()

    return render(request, 'movimientos/egresos.html', {
        'categorias': categorias,
        'tipo': 'EGRESO'
    })


@login_required
def detalle_categoria(request, categoria_id, tipo):
    """
    Muestra todos los movimientos activos de una categoría específica
    para el usuario autenticado.

    Args:
        categoria_id (int): ID de la categoría a detallar.
        tipo (str): 'INGRESO' o 'EGRESO' — para contexto del template.
    """
    categoria = get_object_or_404(Categoria, pk=categoria_id, activo=True)
    movimientos = Movimiento.objects.filter(
        usuario=request.user,
        categoria=categoria,
        activo=True
    )
    total = sum(m.monto for m in movimientos)
    form = MovimientoForm(tipo=tipo, initial={'categoria': categoria, 'tipo': tipo})

    return render(request, 'movimientos/detalle_categoria.html', {
        'categoria': categoria,
        'movimientos': movimientos,
        'total': total,
        'form': form,
        'tipo': tipo
    })


@login_required
def crear_movimiento(request, tipo):
    """
    Crea un nuevo movimiento del tipo indicado.

    Args:
        tipo (str): 'INGRESO' o 'EGRESO' — viene de la URL.
    """
    if request.method == 'POST':
        form = MovimientoForm(tipo=tipo, data=request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.usuario = request.user
            movimiento.save()
            messages.success(request, f'{"Ingreso" if tipo == "INGRESO" else "Egreso"} registrado exitosamente.')
            return redirect('movimientos:detalle_categoria_ingreso' if tipo == 'INGRESO' else 'movimientos:detalle_categoria_egreso', categoria_id=movimiento.categoria.id)
        messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = MovimientoForm(tipo=tipo)

    return render(request, 'movimientos/form_movimiento.html', {
        'form': form,
        'tipo': tipo
    })


@login_required
def editar_movimiento(request, movimiento_id):
    """
    Edita un movimiento existente del usuario autenticado.

    Args:
        movimiento_id (int): ID del movimiento a editar.
    """
    movimiento = get_object_or_404(Movimiento, pk=movimiento_id, usuario=request.user, activo=True)
    tipo = movimiento.tipo

    if request.method == 'POST':
        form = MovimientoForm(tipo=tipo, data=request.POST, instance=movimiento)
        if form.is_valid():
            form.save()
            messages.success(request, f'{"Ingreso" if tipo == "INGRESO" else "Egreso"} actualizado exitosamente.')
            return redirect('movimientos:detalle_categoria_ingreso' if tipo == 'INGRESO' else 'movimientos:detalle_categoria_egreso', categoria_id=movimiento.categoria.id)

        messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = MovimientoForm(tipo=tipo, instance=movimiento)

    return render(request, 'movimientos/form_movimiento.html', {
        'form': form,
        'tipo': tipo,
        'movimiento': movimiento
    })


@login_required
def eliminar_movimiento(request, movimiento_id):
    """
    Realiza soft delete de un movimiento del usuario autenticado.

    Args:
        movimiento_id (int): ID del movimiento a eliminar.
    """
    movimiento = get_object_or_404(Movimiento, pk=movimiento_id, usuario=request.user, activo=True)
    tipo = movimiento.tipo
    categoria_id = movimiento.categoria.id

    if request.method == 'POST':
        movimiento.activo = False
        movimiento.save()
        messages.success(request, f'{"Ingreso" if tipo == "INGRESO" else "Egreso"} eliminado exitosamente.')
        return redirect('movimientos:detalle_categoria_ingreso' if tipo == 'INGRESO' else 'movimientos:detalle_categoria_egreso', categoria_id=categoria_id)

    return render(request, 'movimientos/confirmar_eliminar.html', {
        'movimiento': movimiento,
        'tipo': tipo
    })
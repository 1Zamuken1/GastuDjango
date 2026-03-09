from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Categoria
from .forms import CategoriaForm


@login_required
def lista_categorias(request):
    """
    Muestra todas las categorías activas.
    Destino: vista principal de categorías.
    """
    categorias = Categoria.objects.filter(activo=True)
    return render(request, 'categorias/lista.html', {
        'categorias': categorias
    })


@staff_member_required
def crear_categoria(request):
    """
    Crea una nueva categoría. Solo accesible por Admin.
    """
    if request.method == 'POST':
        form = CategoriaForm(data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría creada exitosamente.')
            return redirect('categorias:lista_categorias')
        messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = CategoriaForm()

    return render(request, 'categorias/form.html', {
        'form': form,
        'accion': 'Crear'
    })


@staff_member_required
def editar_categoria(request, categoria_id):
    """
    Edita una categoría existente. Solo accesible por Admin.

    Args:
        categoria_id (int): ID de la categoría a editar.
    """
    categoria = get_object_or_404(Categoria, pk=categoria_id)

    if request.method == 'POST':
        form = CategoriaForm(data=request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría actualizada exitosamente.')
            return redirect('categorias:lista_categorias')
        messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = CategoriaForm(instance=categoria)

    return render(request, 'categorias/form.html', {
        'form': form,
        'accion': 'Editar',
        'categoria': categoria
    })


@staff_member_required
def eliminar_categoria(request, categoria_id):
    """
    Realiza soft delete de una categoría. Solo accesible por Admin.

    Args:
        categoria_id (int): ID de la categoría a eliminar.
    """
    categoria = get_object_or_404(Categoria, pk=categoria_id, activo=True)

    if request.method == 'POST':
        categoria.activo = False
        categoria.save()
        messages.success(request, 'Categoría eliminada exitosamente.')
        return redirect('categorias:lista_categorias')

    return render(request, 'categorias/confirmar_eliminar.html', {
        'categoria': categoria
    })
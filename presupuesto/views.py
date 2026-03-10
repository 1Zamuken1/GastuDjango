from django.shortcuts import render, redirect
from .models import Presupuesto
from categorias.models import Categoria


def home(request):
    return render(request, 'base.html')


def listar_presupuestos(request):
    presupuestos = Presupuesto.objects.all()
    return render(request, 'presupuesto/listar_presupuestos.html', {
        "presupuestos": presupuestos
    })


def crear_presupuesto(request):

    if request.method == "POST":

        limite = request.POST.get("limite")
        fecha_inicio = request.POST.get("fecha_inicio")
        fecha_fin = request.POST.get("fecha_fin")
        categoria_id = request.POST.get("categoria")
        isActivo = request.POST.get("isActivo")

        categoria = Categoria.objects.get(id=categoria_id)

        Presupuesto.objects.create(
            limite=limite,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            categoria=categoria,
            usuario=request.user,
            isActivo=True if isActivo else False
        )

        return redirect("listar_presupuestos")

    categorias = Categoria.objects.all()

    return render(request, "presupuesto/crear_presupuesto.html", {
        "categorias": categorias
    })


def editar_presupuesto(request, id):

    presupuesto = Presupuesto.objects.get(id=id)
    categorias = Categoria.objects.all()

    return render(request, "presupuesto/editar_presupuesto.html", {
        "presupuesto": presupuesto,
        "categorias": categorias
    })


def confirmar_editar_presupuesto(request, id):

    presupuesto = Presupuesto.objects.get(id=id)

    if request.method == "POST":

        presupuesto.limite = request.POST.get("limite")
        presupuesto.fecha_inicio = request.POST.get("fecha_inicio")
        presupuesto.fecha_fin = request.POST.get("fecha_fin")

        categoria_id = request.POST.get("categoria")
        categoria = Categoria.objects.get(id=categoria_id)

        presupuesto.categoria = categoria
        presupuesto.isActivo = True if request.POST.get("isActivo") else False

        presupuesto.save()

        return redirect("listar_presupuestos")

    categorias = Categoria.objects.all()

    return render(request, "presupuesto/editar_presupuesto.html", {
        "presupuesto": presupuesto,
        "categorias": categorias
    })


def eliminar_presupuesto(request, id):

    presupuesto = Presupuesto.objects.get(id=id)
    presupuesto.delete()

    return redirect("listar_presupuestos")
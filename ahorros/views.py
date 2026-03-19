from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import AhorroMeta
from .forms import AhorroMetaForm, AporteAhorroForm


# 🔹 LISTAR AHORROS
@login_required
def ver_todos_ahorros(request):
    ahorros = AhorroMeta.objects.filter(usuario=request.user)
    return render(request, "ahorros/lista.html", {"ahorros": ahorros})


# 🔹 CREAR AHORRO
@login_required
def crear_ahorro(request):
    if request.method == "POST":
        form = AhorroMetaForm(request.POST)
        if form.is_valid():
            ahorro = form.save(commit=False)
            ahorro.usuario = request.user
            ahorro.total_acumulado = 0
            ahorro.estado = 'SIN_INICIAR'
            ahorro.save()
            return redirect('ver_todos_ahorros')
    else:
        form = AhorroMetaForm()

    return render(request, "ahorros/crear.html", {"form": form})


# 🔹 EDITAR AHORRO
@login_required
def editar_ahorro(request, id):
    ahorro = get_object_or_404(AhorroMeta, id=id, usuario=request.user)

    if request.method == "POST":
        form = AhorroMetaForm(request.POST, instance=ahorro)
        if form.is_valid():
            form.save()
            return redirect('ver_todos_ahorros')
    else:
        form = AhorroMetaForm(instance=ahorro)

    return render(request, "ahorros/editar.html", {"form": form})


# 🔹 ELIMINAR AHORRO
@login_required
def eliminar_ahorro(request, id):
    ahorro = get_object_or_404(AhorroMeta, id=id, usuario=request.user)

    if request.method == "POST":
        ahorro.delete()
        return redirect('ver_todos_ahorros')

    return render(request, "ahorros/eliminar.html", {"ahorro": ahorro})


# 🔹 REGISTRAR APORTE
@login_required
def registrar_aporte(request, ahorro_id):
    ahorro = get_object_or_404(AhorroMeta, id=ahorro_id, usuario=request.user)

    if request.method == "POST":
        form = AporteAhorroForm(request.POST)
        if form.is_valid():
            aporte = form.save(commit=False)
            aporte.ahorro = ahorro
            aporte.estado_ap = 'APORTADO'
            aporte.save()

            ahorro.total_acumulado += aporte.aporte
            ahorro.save()

            return redirect('ver_todos_ahorros')
    else:
        form = AporteAhorroForm()

    return render(request, "ahorros/aporte.html", {
        "form": form,
        "ahorro": ahorro
    })
    
    
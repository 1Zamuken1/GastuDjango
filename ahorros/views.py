from django.http import JsonResponse
from django.shortcuts import render, redirect, get_list_or_404, get_object_or_404
from . models import AhorroMeta, AporteAhorro
from . forms import AhorroMetaForm, AporteAhorroForm
from categorias.models import Categoria
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

# Create your views here.
# request en NestJS es el objeto @Req()

@login_required # obliga a que el usuario este logueado
@require_http_methods(["GET"])
def ver_todos_ahorros(request):
    ahorros=AhorroMeta.objects.filter(usuario=request.user)
    
    info = [
        {
            "id": a.id,
            "categoria": a.categoria.nombre,
            "monto_meta": str(a.monto_meta),
            "total_acumulado": str(a.total_acumulado),
            "frecuencia": a.frecuencia,
            "fecha_meta": a.fecha_meta,
            "estado": a.estado,
            "cantidad_cuotas": a.cantidad_cuotas,
            "descripcion": a.descripcion,
        }
        for a in ahorros
    ]
    # return render(request, "ahorro.html", info)
    return JsonResponse({"ok": True, "ahorros": info})


# def ver_por_categoria(request, nom_categoria):
#     ahorro=get_list_or_404(AhorroMeta, categoria__nombre=nom_categoria)
    
#     info={
#          'ahorroPorCategoria': ahorro
#      }
#     return render(request, "ahorro.html", info)

@login_required
@require_http_methods(["POST"])
def crear_ahorro(request):
    form_crear = AhorroMetaForm(request.POST)
    
    if form_crear.is_valid():
        crear_ahorro = form_crear.save(commit=False) #pausamos el guardado 

        # Campos internos
        crear_ahorro.usuario = request.user
        crear_ahorro.total_acumulado = 0
        crear_ahorro.estado = 'SIN_INICIAR'

        crear_ahorro.save()
        
        return JsonResponse({
            "ok": True,
            "id": crear_ahorro.id,
            "mensaje": "Ahorro creado correctamente"
        })

    return JsonResponse({
        "ok": False,
        "errores": form_crear.errors
    }, status=400)


@login_required
@require_http_methods(["PUT", "PATCH"])
def editar_ahorro(request, id):
    #  Buscamos el objeto que vamos a editar
    editar_ahorro=get_object_or_404(AhorroMeta, id=id, usuario=request.user)
    form_editar = AhorroMetaForm(request.POST, instance=editar_ahorro)
    
    if form_editar.is_valid():
        form_editar.save()
        return JsonResponse({
            "ok": True,
            "mensaje": "Ahorro actualizado"
        })

    return JsonResponse({
        "ok": False,
        "errores": form_editar.errors
    }
    , status=400)

@login_required
@require_http_methods(["DELETE"])
def eliminar_ahorro(request, id):
    #busco si existe el ahorro, si no lanza 404, si si lo elimina y me devuelve a la pagina principal
    eliminarahorro=get_object_or_404(AhorroMeta, id=id, usuario=request.user)
    eliminarahorro.delete()
    
    return JsonResponse({
        "ok": True,
        "mensaje": "Ahorro eliminado"
    })



#aportes de ahorro
@login_required
@require_http_methods(["POST"])
def registrar_aporte(request, ahorro_id):
    existe_ahorro = get_object_or_404(AhorroMeta, id=ahorro_id, usuario=request.user)

    form_aporte = AporteAhorroForm(request.POST)

    if form_aporte.is_valid():
        aporte = form_aporte.save(commit=False)

        aporte.ahorro = existe_ahorro
        aporte.estado_ap = 'APORTADO'

        aporte.save()

        # actualizar total acumulado
        existe_ahorro.total_acumulado += aporte.aporte
        existe_ahorro.save()

        return JsonResponse({
            "ok": True,
            "mensaje": "Aporte registrado",
            "total_acumulado": str(existe_ahorro.total_acumulado)
        })

    return JsonResponse({
        "ok": False,
        "errores": form_aporte.errors
    }, status=400)

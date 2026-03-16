from django.shortcuts import render, redirect, get_list_or_404, get_object_or_404
from . models import AhorroMeta, AporteAhorro
from categorias.models import Categoria

# Create your views here.
# request en NestJS es el objeto @Req()

def ver_todos_ahorros(request):
    ahorros=AhorroMeta.objects.all()
    
    info={
        'Ahorros': ahorros
    }
    return render(request, "ahorro.html", info)


def ver_por_categoria(request, nom_categoria):
    ahorro=get_list_or_404(AhorroMeta, categoria__nombre=nom_categoria)
    
    info={
         'ahorroPorCategoria': ahorro
     }
    return render(request, "ahorro.html", info)


def crear_ahorro(request):
    if request.method=='POST':
        categoria=request.POST.get('categoria')
        montometa=request.POST.get('montoMeta')
        frecuencia=request.POST.get('frecuencia')
        fechameta=request.POST.get('fechameta')
        cantidadcuotas=request.POST.get('cantidadcuotas')
        descripcion=request.POST.get('descripcion')

        
        nuevoahorro = AhorroMeta(
            montoMeta=montometa,
            frecuencia=frecuencia,
            fechaMeta=fechameta,
            cantidadCuotas=cantidadcuotas,
            descripcion=descripcion,
            categoria=Categoria.objects.get(id=categoria),
            totalAcumulado=0,
            estado=True,
            usuario=request.usuario 
            )
        nuevoahorro.save()
        return redirect('ahorros') 
    return redirect('ahorros') 
    
def editar_ahorro(request, id):
    #  Buscamos el objeto que vamos a editar
    if request.method=='POST':
        editarahorro=get_object_or_404(AhorroMeta, id=id)
        
        editarahorro.montoMeta=request.POST.get('montometa')  
        editarahorro.frecuencia=request.POST.get('frecuencia')
        editarahorro.fechaMeta=request.POST.get('fechaMeta')
        editarahorro.cantidadCuotas=request.POST.get('cantidadcuotas')      
        editarahorro.descripcion=request.POST.get('descripcion')
        categoria= request.POST.get('categoria')
        editarahorro.categoria=get_object_or_404(Categoria, id=categoria)
        
        editarahorro.save()
        return redirect('ahorros')
    return redirect('ahorros')

def eliminar(request, id):
    #busco si existe el ahorro, si no lanza 404, si si lo elimina y me devuelve a la pagina principal
    eliminarahorro=get_object_or_404(AhorroMeta, id=id)
    eliminarahorro.delete()
    return redirect('ahorros')


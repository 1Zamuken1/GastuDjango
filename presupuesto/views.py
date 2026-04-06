from django.shortcuts import render

def base_presupuesto(request):
    return render(request, 'presupuesto/listar_presupuestos.html')
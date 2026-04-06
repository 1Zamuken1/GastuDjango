from django.shortcuts import render

def base_programaciones(request):
    return render(request, 'programaciones/listar_programaciones.html')
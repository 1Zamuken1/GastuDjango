from django.shortcuts import render


def base_programaciones(request):
    """Renderiza la vista principal de programaciones."""
    return render(request, 'programaciones/listar_programaciones.html')
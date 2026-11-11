from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def base_programaciones(request):
    """Renderiza la vista principal de programaciones."""
    return render(request, 'programaciones/listar_programaciones.html')
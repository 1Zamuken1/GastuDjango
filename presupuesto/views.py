from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def base_presupuesto(request):
    """Renderiza la vista principal de presupuestos."""
    return render(request, 'presupuesto/listar_presupuestos.html')
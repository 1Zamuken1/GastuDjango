from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def agente_financiero(request):
    return render(request, 'agente_financiero/agente_financiero.html')
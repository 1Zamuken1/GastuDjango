from django.shortcuts import render

# Create your views here.
def agente_financiero(request):
    return render (request, 'agente_financiero/agente_financiero.html')
from django.shortcuts import render


def home(request):
    """Vista principal — landing page pública."""
    return render(request, 'landing/landing.html')
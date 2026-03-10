from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import UsuarioCreationForm


def register_view(request):
    """
    Registro de nuevos usuarios. Guarda en usuarios_usuario.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = UsuarioCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard:home')
    else:
        form = UsuarioCreationForm()

    return render(request, 'usuarios/register.html', {'form': form})


def login_view(request):
    """
    Login de usuarios. Autentica contra usuarios_usuario.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next')
            return redirect(next_url if next_url else 'dashboard:home')
    else:
        form = AuthenticationForm()

    return render(request, 'usuarios/login.html', {'form': form})


def logout_view(request):
    """
    Cierra la sesión y redirige al home.
    """
    logout(request)
    return redirect('landing:home')
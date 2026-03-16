from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.conf import settings

from .forms import UsuarioCreationForm, LoginForm


# ──────────────────────────────────────────────────────────────
#  REGISTER
# ──────────────────────────────────────────────────────────────

def register_view(request):
    """
    Registro de nuevos usuarios. Guarda en usuarios_usuario.
    Siempre muestra el formulario, independiente del estado de sesión.
    """
    if request.method == 'POST':
        form = UsuarioCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Bienvenido, {user.username}! Tu cuenta ha sido creada.')
            return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        form = UsuarioCreationForm()

    return render(request, 'usuarios/register.html', {'form': form})


# ──────────────────────────────────────────────────────────────
#  LOGIN
# ──────────────────────────────────────────────────────────────

def login_view(request):
    """
    Login de usuarios. Autentica contra usuarios_usuario.
    Redirige al dashboard si el usuario ya está autenticado.
    Respeta el parámetro ?next= para redirección post-login.
    """
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next')
            return redirect(next_url if next_url else settings.LOGIN_REDIRECT_URL)
    else:
        form = LoginForm(request)

    return render(request, 'usuarios/login.html', {'form': form})


# ──────────────────────────────────────────────────────────────
#  LOGOUT
# ──────────────────────────────────────────────────────────────

def logout_view(request):
    """
    Cierra la sesión y redirige al home de la landing.
    """
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)
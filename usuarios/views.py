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
    La cuenta se identifica por EMAIL (unico), no por username.
    Siempre muestra el formulario, independiente del estado de sesion.
    """
    if request.method == 'POST':
        form = UsuarioCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Bienvenido, {user.nombre_usuario}. Tu cuenta ha sido creada.')
            return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        form = UsuarioCreationForm()

    return render(request, 'usuarios/register.html', {'form': form})


# ──────────────────────────────────────────────────────────────
#  LOGIN
# ──────────────────────────────────────────────────────────────

def login_view(request):
    """
    Login de usuarios por EMAIL + contrasena.
    Redirige al dashboard si el usuario ya esta autenticado.
    Respeta el parametro ?next= para redireccion post-login.
    """
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            if user.rol == 'ADMIN' or user.is_staff:
                return redirect('/admin-panel/')
            return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        form = LoginForm(request)

    return render(request, 'usuarios/login.html', {'form': form})


# ──────────────────────────────────────────────────────────────
#  LOGOUT
# ──────────────────────────────────────────────────────────────

def logout_view(request):
    """
    Cierra la sesion y redirige al home de la landing.
    """
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)
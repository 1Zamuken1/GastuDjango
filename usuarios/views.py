from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings

from .forms import UsuarioCreationForm, LoginForm, PerfilForm, PreferenciasForm
from .models import Preferencias


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


# ──────────────────────────────────────────────────────────────
#  PERFIL
# ──────────────────────────────────────────────────────────────

@login_required
def perfil_view(request):
    """
    Vista de perfil con 4 tabs.
    Para AJAX (X-Requested-With: XMLHttpRequest) responde JSON.
    Para navegacion normal responde HTML.
    """
    perfil_form = PerfilForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)

    preferencias, _ = Preferencias.objects.get_or_create(
        usuario=request.user,
    )
    preferencias_form = PreferenciasForm(instance=preferencias)

    tab_activo = request.GET.get('tab', 'datos')
    tabs_validas = {'datos', 'preferencias', 'notificaciones'}
    if tab_activo not in tabs_validas:
        tab_activo = 'datos'

    # AJAX POST — devuelve JSON en lugar de redirect
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if 'eliminar_cuenta' in request.POST:
            try:
                password = request.POST.get('password_confirmacion', '')
                if request.user.has_usable_password() and not request.user.check_password(password):
                    if is_ajax:
                        return JsonResponse({'ok': False, 'msg': 'La contrasena es incorrecta.'})
                    messages.error(request, 'La contrasena es incorrecta.')
                    return redirect('perfil')

                # Desconectar signals de movimientos para evitar errores
                # durante el CASCADE delete del usuario
                from django.db.models.signals import post_save, post_delete
                from movimientos.models import Movimiento
                from movimientos.signals import (
                    actualizar_resumen_al_guardar,
                    actualizar_resumen_al_eliminar,
                )
                post_save.disconnect(actualizar_resumen_al_guardar, sender=Movimiento)
                post_delete.disconnect(actualizar_resumen_al_eliminar, sender=Movimiento)

                try:
                    request.user.delete()
                finally:
                    post_save.connect(actualizar_resumen_al_guardar, sender=Movimiento)
                    post_delete.connect(actualizar_resumen_al_eliminar, sender=Movimiento)

                logout(request)
                if is_ajax:
                    return JsonResponse({'ok': True, 'redirect': '/'})
                messages.success(request, 'Tu cuenta ha sido eliminada permanentemente.')
                return redirect('/')
            except Exception as e:
                if is_ajax:
                    return JsonResponse({'ok': False, 'msg': f'Error al eliminar: {str(e)}'})
                raise


        if 'actualizar_datos' in request.POST:
            perfil_form = PerfilForm(request.POST, instance=request.user)
            if perfil_form.is_valid():
                perfil_form.save()
                if is_ajax:
                    return JsonResponse({'ok': True, 'mensaje': 'Datos personales actualizados.'})
                messages.success(request, 'Datos personales actualizados correctamente.')
                return redirect('perfil')
            if is_ajax:
                return JsonResponse({'ok': False, 'errors': perfil_form.errors})

        elif 'cambiar_password' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, request.user)
                if is_ajax:
                    return JsonResponse({'ok': True, 'mensaje': 'Contrasena actualizada.'})
                messages.success(request, 'Contrasena actualizada correctamente.')
                return redirect('perfil')
            if is_ajax:
                return JsonResponse({'ok': False, 'errors': password_form.errors})

        elif 'guardar_preferencias' in request.POST:
            preferencias_form = PreferenciasForm(request.POST, instance=preferencias)
            if preferencias_form.is_valid():
                pref = preferencias_form.save(commit=False)
                pref.usuario = request.user
                pref.save()
                if is_ajax:
                    return JsonResponse({'ok': True, 'mensaje': 'Preferencias de alertas actualizadas.'})
                messages.success(request, 'Preferencias de alertas actualizadas.')
                return redirect('perfil')
            if is_ajax:
                return JsonResponse({'ok': False, 'errors': preferencias_form.errors})

    # Conteos de notificaciones
    from notificaciones.models import Notificacion

    total_no_leidas = Notificacion.objects.filter(
        usuario=request.user, leida=False
    ).count()
    recuentos_modulos = {}
    for choice in Notificacion.Modulo.choices:
        recuentos_modulos[choice[0]] = Notificacion.objects.filter(
            usuario=request.user, leida=False, modulo=choice[0]
        ).count()

    return render(request, 'usuarios/perfil.html', {
        'perfil_form': perfil_form,
        'password_form': password_form,
        'preferencias_form': preferencias_form,
        'tab_activo': tab_activo,
        'total_no_leidas': total_no_leidas,
        'recuentos_modulos': recuentos_modulos,
        'notificaciones_modulo_choices': Notificacion.Modulo.choices,
    })

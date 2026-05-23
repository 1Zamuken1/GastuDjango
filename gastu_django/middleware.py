"""
Middleware de separación de contextos para GastuApp.

AdminAreaMiddleware:
    Si el usuario autenticado tiene rol ADMIN o is_staff=True,
    solo puede acceder a las URLs del panel admin y rutas de soporte
    (login, logout, static, etc.).
    Cualquier intento de acceder al área de usuario es redirigido
    automáticamente a /admin-panel/.
"""
from django.shortcuts import redirect

# Prefijos de URL que el admin SÍ puede visitar sin restricción
ADMIN_ALLOWED_PREFIXES = (
    '/admin-panel/',   # su área propia
    '/admin/',         # Django admin nativo (por si acaso)
    '/login/',
    '/logout/',
    '/static/',
    '/media/',
    '/__reload__/',    # Tailwind hot-reload (solo en DEBUG)
    '/accounts/',      # allauth
)


class AdminAreaMiddleware:
    """
    Redirige a los usuarios con rol ADMIN al panel de administración
    cuando intentan navegar por el área de usuario normal.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        if user.is_authenticated and (getattr(user, 'rol', None) == 'ADMIN' or user.is_staff):
            path = request.path

            # Si la URL actual NO está en la lista de permitidos para admin → redirigir
            if not any(path.startswith(prefix) for prefix in ADMIN_ALLOWED_PREFIXES):
                return redirect('/admin-panel/')

        return self.get_response(request)

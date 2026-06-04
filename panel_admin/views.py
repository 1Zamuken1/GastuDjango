import json
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone

from categorias.models import Categoria
from movimientos.models import Movimiento

Usuario = get_user_model()


# ──────────────────────────────────────────────────────────────
#  DECORADOR
# ──────────────────────────────────────────────────────────────

def admin_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.rol == 'ADMIN' or request.user.is_staff):
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


# ──────────────────────────────────────────────────────────────
#  HOME
# ──────────────────────────────────────────────────────────────

@admin_required
def admin_home(request):
    hoy  = timezone.now()
    mes  = hoy.month
    anio = hoy.year

    total_usuarios     = Usuario.objects.count()
    usuarios_activos   = Usuario.objects.filter(is_active=True).count()
    usuarios_inactivos = Usuario.objects.filter(is_active=False).count()
    admins             = Usuario.objects.filter(rol='ADMIN').count()

    total_movimientos = Movimiento.objects.filter(activo=True).count()
    mov_este_mes      = Movimiento.objects.filter(activo=True, fecha_registro__month=mes, fecha_registro__year=anio).count()
    total_categorias  = Categoria.objects.filter(activo=True).count()

    top_usuarios = (
        Usuario.objects
        .annotate(num_mov=Count('movimientos', filter=Q(movimientos__activo=True)))
        .order_by('-num_mov')[:5]
    )
    ultimos_usuarios    = Usuario.objects.order_by('-date_joined')[:6]
    
    # ── Gráficos de Actividad (Últimos 7 días) ──
    from django.db.models.functions import TruncDate
    import datetime
    
    fecha_hoy = timezone.localdate()
    hace_7_dias = fecha_hoy - datetime.timedelta(days=6)
    
    movimientos_por_dia = (
        Movimiento.objects.filter(fecha_registro__date__gte=hace_7_dias, activo=True)
        .annotate(dia=TruncDate('fecha_registro'))
        .values('dia')
        .annotate(total=Count('id'))
        .order_by('dia')
    )
    
    chart_activity_labels = []
    chart_activity_data = []
    for i in range(7):
        d = hace_7_dias + datetime.timedelta(days=i)
        chart_activity_labels.append(d.strftime('%d %b'))
        total = next((item['total'] for item in movimientos_por_dia if item['dia'] == d), 0)
        chart_activity_data.append(total)
        
    # ── Gráficos de Categorías Populares (Separados por Módulo) ──
    # 1. Ingresos
    top_ingresos = (
        Movimiento.objects.filter(activo=True, categoria__tipo='INGRESO')
        .values('categoria__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )
    chart_ingresos_labels = [c['categoria__nombre'] for c in top_ingresos]
    chart_ingresos_data = [c['total'] for c in top_ingresos]

    # 2. Egresos
    top_egresos = (
        Movimiento.objects.filter(activo=True, categoria__tipo='EGRESO')
        .values('categoria__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )
    chart_egresos_labels = [c['categoria__nombre'] for c in top_egresos]
    chart_egresos_data = [c['total'] for c in top_egresos]

    # 3. Ahorros
    from ahorros.models import AhorroMeta
    top_ahorros = (
        AhorroMeta.objects.values('categoria__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )
    chart_ahorros_labels = [c['categoria__nombre'] for c in top_ahorros]
    chart_ahorros_data = [c['total'] for c in top_ahorros]

    context = {
        'total_usuarios':      total_usuarios,
        'usuarios_activos':    usuarios_activos,
        'usuarios_inactivos':  usuarios_inactivos,
        'admins':              admins,
        'total_movimientos':   total_movimientos,
        'mov_este_mes':        mov_este_mes,
        'total_categorias':    total_categorias,
        'top_usuarios':        top_usuarios,
        'ultimos_usuarios':    ultimos_usuarios,
        
        # Datos para los gráficos pasados como JSON strings
        'chart_activity_labels': json.dumps(chart_activity_labels),
        'chart_activity_data':   json.dumps(chart_activity_data),
        'chart_ingresos_labels': json.dumps(chart_ingresos_labels),
        'chart_ingresos_data':   json.dumps(chart_ingresos_data),
        'chart_egresos_labels':  json.dumps(chart_egresos_labels),
        'chart_egresos_data':    json.dumps(chart_egresos_data),
        'chart_ahorros_labels':  json.dumps(chart_ahorros_labels),
        'chart_ahorros_data':    json.dumps(chart_ahorros_data),
        
        'seccion':             'home',
    }
    return render(request, 'panel_admin/home.html', context)


# ──────────────────────────────────────────────────────────────
#  PERFIL DEL ADMIN
# ──────────────────────────────────────────────────────────────

@admin_required
def admin_perfil(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email    = request.POST.get('email', '').strip().lower()
        telefono = request.POST.get('telefono', '').strip()

        if not username:
            return JsonResponse({'ok': False, 'msg': 'El nombre de usuario es obligatorio.'})
        if Usuario.objects.exclude(pk=request.user.pk).filter(username__iexact=username).exists():
            return JsonResponse({'ok': False, 'msg': 'Ese nombre de usuario ya está en uso.'})
        if email and Usuario.objects.exclude(pk=request.user.pk).filter(email__iexact=email).exists():
            return JsonResponse({'ok': False, 'msg': 'Ese correo ya está registrado.'})

        request.user.username = username
        request.user.email    = email
        request.user.telefono = telefono
        request.user.save()
        return JsonResponse({'ok': True, 'msg': 'Perfil actualizado correctamente.', 'username': username})

    return JsonResponse({'ok': False, 'msg': 'Método no permitido.'}, status=405)


def tiene_sesion_activa(user_id):
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    sesiones = Session.objects.filter(expire_date__gte=timezone.now())
    for s in sesiones:
        data = s.get_decoded()
        if str(data.get('_auth_user_id')) == str(user_id):
            return True
    return False


# ──────────────────────────────────────────────────────────────
#  USUARIOS — listado
# ──────────────────────────────────────────────────────────────

@admin_required
def admin_usuarios(request):
    q      = request.GET.get('q', '').strip()
    rol    = request.GET.get('rol', '')
    estado = request.GET.get('estado', '')

    usuarios = Usuario.objects.all().order_by('-date_joined')
    if q:
        usuarios = usuarios.filter(Q(username__icontains=q) | Q(email__icontains=q))
    if rol:
        usuarios = usuarios.filter(rol=rol)
    if estado == 'activo':
        usuarios = usuarios.filter(is_active=True)
    elif estado == 'inactivo':
        usuarios = usuarios.filter(is_active=False)

    usuarios = usuarios.annotate(
        num_mov=Count('movimientos', filter=Q(movimientos__activo=True))
    )

    context = {
        'usuarios':   usuarios,
        'q':          q,
        'rol_fil':    rol,
        'estado_fil': estado,
        'seccion':    'usuarios',
    }
    return render(request, 'panel_admin/usuarios.html', context)


# ──────────────────────────────────────────────────────────────
#  USUARIOS — CRUD via JSON (modales)
# ──────────────────────────────────────────────────────────────

@admin_required
def admin_usuario_detalle(request, usuario_id):
    u = get_object_or_404(Usuario, pk=usuario_id)
    return JsonResponse({
        'id': u.pk, 'username': u.username,
        'email': u.email or '', 'telefono': u.telefono or '',
        'rol': u.rol, 'activo': u.is_active,
    })


@admin_required
def admin_crear_usuario_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    from usuarios.forms import UsuarioCreationForm
    form = UsuarioCreationForm(request.POST)
    if form.is_valid():
        user = form.save()
        return JsonResponse({'ok': True, 'msg': f'Usuario "{user.username}" creado correctamente.'})
    errores = {field: errs[0] for field, errs in form.errors.items()}
    return JsonResponse({'ok': False, 'errores': errores})


@admin_required
def admin_editar_usuario_ajax(request, usuario_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    usuario  = get_object_or_404(Usuario, pk=usuario_id)
    username = request.POST.get('username', '').strip()
    email    = request.POST.get('email', '').strip().lower()
    telefono = request.POST.get('telefono', '').strip()
    password = request.POST.get('password', '').strip()

    if not username:
        return JsonResponse({'ok': False, 'msg': 'El nombre de usuario es obligatorio.'})
    if Usuario.objects.exclude(pk=usuario_id).filter(username__iexact=username).exists():
        return JsonResponse({'ok': False, 'msg': 'Ese nombre de usuario ya está en uso.'})
    if email and Usuario.objects.exclude(pk=usuario_id).filter(email__iexact=email).exists():
        return JsonResponse({'ok': False, 'msg': 'Ese correo ya está registrado.'})
    if password and len(password) < 8:
        return JsonResponse({'ok': False, 'msg': 'La contraseña debe tener al menos 8 caracteres.'})

    usuario.username = username
    usuario.email    = email
    usuario.telefono = telefono
    if password:
        usuario.set_password(password)
    usuario.save()
    return JsonResponse({'ok': True, 'msg': f'Usuario "{username}" actualizado.'})


@admin_required
def admin_toggle_usuario(request, usuario_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    if usuario == request.user:
        return JsonResponse({'ok': False, 'msg': 'No puedes desactivarte a ti mismo.'})
    if usuario.rol == 'ADMIN':
        return JsonResponse({'ok': False, 'msg': 'No puedes desactivar a un administrador.'})
    if usuario.is_active and tiene_sesion_activa(usuario.id):
        return JsonResponse({'ok': False, 'msg': 'No puedes desactivar a un usuario con sesión activa.'})
    
    usuario.is_active = not usuario.is_active
    usuario.save()
    estado = 'activado' if usuario.is_active else 'desactivado'
    return JsonResponse({'ok': True, 'activo': usuario.is_active, 'msg': f'Usuario {estado}.'})


@admin_required
def admin_cambiar_rol(request, usuario_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    if usuario == request.user:
        return JsonResponse({'ok': False, 'msg': 'No puedes cambiar tu propio rol.'})
    if usuario.rol == 'ADMIN':
        return JsonResponse({'ok': False, 'msg': 'No puedes quitarle el rol a otro administrador.'})
        
    nuevo_rol        = 'ADMIN' if usuario.rol == 'USER' else 'USER'
    usuario.rol      = nuevo_rol
    usuario.is_staff = (nuevo_rol == 'ADMIN')
    usuario.save()
    return JsonResponse({'ok': True, 'rol': nuevo_rol, 'msg': f'Rol cambiado a {nuevo_rol}.'})


@admin_required
def admin_eliminar_usuario(request, usuario_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    if usuario == request.user:
        return JsonResponse({'ok': False, 'msg': 'No puedes eliminarte a ti mismo.'})
    if usuario.rol == 'ADMIN':
        return JsonResponse({'ok': False, 'msg': 'No puedes eliminar a otro administrador.'})
    if tiene_sesion_activa(usuario.id):
        return JsonResponse({'ok': False, 'msg': 'No puedes eliminar a un usuario con sesión activa.'})

    username = usuario.username
    try:
        # Eliminación manual en orden para evitar FOREIGN KEY constraint
        # en SQLite (que no siempre respeta CASCADE automáticamente)
        from django.db import transaction

        with transaction.atomic():
            # 1. Notificaciones
            try:
                from notificaciones.models import Notificacion
                Notificacion.objects.filter(usuario=usuario).delete()
            except Exception:
                pass

            # 2. Historial
            try:
                from historial.models import AccionHistorial
                AccionHistorial.objects.filter(usuario=usuario).delete()
            except Exception:
                pass

            # 3. Agente financiero (mensajes y alertas)
            try:
                from agente_financiero.models import MensajeChat, AlertaDiaria
                MensajeChat.objects.filter(usuario=usuario).delete()
                AlertaDiaria.objects.filter(usuario=usuario).delete()
            except Exception:
                pass

            # 4. Programaciones
            try:
                from programaciones.models import Programacion
                Programacion.objects.filter(usuario=usuario).delete()
            except Exception:
                pass

            # 5. Presupuesto
            try:
                from presupuesto.models import Presupuesto
                Presupuesto.objects.filter(usuario=usuario).delete()
            except Exception:
                pass

            # 6. Ahorros
            try:
                from ahorros.models import AhorroMeta, AporteAhorro
                AporteAhorro.objects.filter(ahorro__usuario=usuario).delete()
                AhorroMeta.objects.filter(usuario=usuario).delete()
            except Exception:
                pass

            # 7. Movimientos
            Movimiento.objects.filter(usuario=usuario).delete()

            # 8. Resumen mensual (dashboard)
            try:
                from dashboard.models import ResumenMensual
                ResumenMensual.objects.filter(usuario=usuario).delete()
            except Exception:
                pass

            # 9. Preferencias (OneToOne)
            try:
                from usuarios.models import Preferencias
                Preferencias.objects.filter(usuario=usuario).delete()
            except Exception:
                pass

            # 10. Finalmente el usuario
            usuario.delete()

        return JsonResponse({'ok': True, 'msg': f'Usuario "{username}" y todos sus datos han sido eliminados.'})

    except Exception as e:
        return JsonResponse({'ok': False, 'msg': f'Error al eliminar: {str(e)}'})


# ──────────────────────────────────────────────────────────────
#  CATEGORÍAS — listado
# ──────────────────────────────────────────────────────────────

@admin_required
def admin_categorias(request):
    q      = request.GET.get('q', '').strip()
    tipo   = request.GET.get('tipo', '')
    estado = request.GET.get('estado', '')  # 'activo' | 'inactivo' | ''
    categorias = Categoria.objects.all().order_by('tipo', 'nombre')
    if q:
        categorias = categorias.filter(nombre__icontains=q)
    if tipo:
        categorias = categorias.filter(tipo=tipo)
    if estado == 'activo':
        categorias = categorias.filter(activo=True)
    elif estado == 'inactivo':
        categorias = categorias.filter(activo=False)
    categorias = categorias.annotate(
        num_mov=Count('movimientos', filter=Q(movimientos__activo=True))
    )
    context = {
        'categorias':  categorias,
        'q':           q,
        'tipo_fil':    tipo,
        'estado_fil':  estado,
        'seccion':     'categorias',
    }
    return render(request, 'panel_admin/categorias.html', context)


# ──────────────────────────────────────────────────────────────
#  CATEGORÍAS — CRUD via JSON (modales)
# ──────────────────────────────────────────────────────────────

@admin_required
def admin_categoria_detalle(request, categoria_id):
    cat = get_object_or_404(Categoria, pk=categoria_id)
    return JsonResponse({
        'id': cat.pk, 'nombre': cat.nombre,
        'tipo': cat.tipo, 'descripcion': cat.descripcion or '', 'activo': cat.activo,
    })


@admin_required
def admin_crear_categoria_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    nombre = request.POST.get('nombre', '').strip()
    tipo   = request.POST.get('tipo', '').strip()
    desc   = request.POST.get('descripcion', '').strip()
    if not nombre or not tipo:
        return JsonResponse({'ok': False, 'msg': 'Nombre y tipo son obligatorios.'})
    if tipo not in ['INGRESO', 'EGRESO', 'AHORRO']:
        return JsonResponse({'ok': False, 'msg': 'Tipo inválido.'})
    if Categoria.objects.filter(nombre__iexact=nombre, tipo=tipo).exists():
        return JsonResponse({'ok': False, 'msg': f'Ya existe una categoría de tipo {tipo} con el nombre "{nombre}".'})
    cat = Categoria.objects.create(nombre=nombre, tipo=tipo, descripcion=desc)
    return JsonResponse({'ok': True, 'msg': f'Categoría "{nombre}" creada.', 'id': cat.pk})


@admin_required
def admin_editar_categoria_ajax(request, categoria_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    cat    = get_object_or_404(Categoria, pk=categoria_id)
    nombre = request.POST.get('nombre', '').strip()
    tipo   = request.POST.get('tipo', '').strip()
    desc   = request.POST.get('descripcion', '').strip()
    if not nombre or not tipo:
        return JsonResponse({'ok': False, 'msg': 'Nombre y tipo son obligatorios.'})
    if tipo not in ['INGRESO', 'EGRESO', 'AHORRO']:
        return JsonResponse({'ok': False, 'msg': 'Tipo inválido.'})
    if Categoria.objects.exclude(pk=categoria_id).filter(nombre__iexact=nombre).exists():
        return JsonResponse({'ok': False, 'msg': f'Ya existe otra categoría con el nombre "{nombre}".'})
    cat.nombre = nombre; cat.tipo = tipo; cat.descripcion = desc
    cat.save()
    return JsonResponse({'ok': True, 'msg': f'Categoría "{nombre}" actualizada.'})


@admin_required
def admin_toggle_categoria(request, categoria_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    cat = get_object_or_404(Categoria, pk=categoria_id)
    cat.activo = not cat.activo
    cat.save()
    estado = 'activada' if cat.activo else 'desactivada'
    return JsonResponse({'ok': True, 'activo': cat.activo, 'msg': f'Categoria {estado}.'})


# ──────────────────────────────────────────────────────────────
#  IMPORTACION MASIVA DE CATEGORIAS (CSV)
# ──────────────────────────────────────────────────────────────

@admin_required
def importar_categorias_csv(request):
    """
    Permite al administrador subir un archivo CSV para importar categorias
    de forma masiva. Las categorias duplicadas (mismo nombre + tipo) se omiten.

    GET:  muestra el formulario de subida con instrucciones.
    POST: procesa el archivo CSV y muestra el resumen de la importacion.
    """
    from .services import procesar_csv_categorias

    if request.method == 'POST':
        archivo = request.FILES.get('archivo_csv')

        if not archivo:
            messages.error(request, 'No se selecciono ningun archivo.')
            return redirect('panel_admin:importar_categorias_csv')

        if not archivo.name.lower().endswith('.csv'):
            messages.error(request, 'El archivo debe tener extension .csv')
            return redirect('panel_admin:importar_categorias_csv')

        if archivo.size > 2 * 1024 * 1024:  # 2 MB maximo
            messages.error(request, 'El archivo no puede superar los 2 MB.')
            return redirect('panel_admin:importar_categorias_csv')

        resultado = procesar_csv_categorias(archivo)

        if resultado['errores'] and resultado['creadas'] == 0 and resultado['omitidas'] == 0:
            # Solo errores criticos (ej: columnas faltantes)
            for err in resultado['errores']:
                messages.error(request, err)
        else:
            resumen = (
                f"Importacion completada: "
                f"{resultado['creadas']} categoria(s) creada(s), "
                f"{resultado['omitidas']} omitida(s) por duplicado."
            )
            messages.success(request, resumen)
            if resultado['errores']:
                for err in resultado['errores']:
                    messages.warning(request, err)

        return redirect('panel_admin:importar_categorias_csv')

    context = {'seccion': 'categorias'}
    return render(request, 'panel_admin/importar_categorias.html', context)
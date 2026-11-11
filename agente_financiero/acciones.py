"""
Acciones de escritura del agente con confirmacion humana (human-in-the-loop).

Flujo:
1. Una herramienta de escritura llama a preparar_accion: se valida todo y se
   guarda una AccionPendiente. No se toca ningun dato del usuario.
2. El chat muestra una tarjeta con el resumen y los botones Confirmar / Cancelar.
3. El boton llama a la API, que ejecuta confirmar_accion o cancelar_accion.
   Antes de aplicar se vuelve a validar (el saldo o la categoria pudieron cambiar).
"""
import logging
import secrets
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from categorias.models import Categoria
from dashboard.services import obtener_disponible
from movimientos.models import Movimiento
from presupuesto.models import Presupuesto

from .models import AccionPendiente

logger = logging.getLogger(__name__)

VIGENCIA = timedelta(minutes=10)
MAX_PENDIENTES_POR_RESPUESTA = 3


class ErrorAccion(Exception):
    """Error con mensaje apto para mostrar al usuario."""


def formatear_cop(monto) -> str:
    return f"${Decimal(str(monto)):,.0f}".replace(",", ".")


def preparar_accion(usuario, tipo: str, datos: dict, resumen: str) -> AccionPendiente:
    """Guarda una accion pendiente de confirmacion y devuelve el registro."""
    return AccionPendiente.objects.create(
        usuario=usuario,
        token=secrets.token_urlsafe(32),
        tipo=tipo,
        datos=datos,
        resumen=resumen[:255],
        expira_en=timezone.now() + VIGENCIA,
    )


def _obtener_pendiente(usuario, token) -> AccionPendiente:
    """Bloquea la fila y valida dueno, estado y vigencia."""
    accion = (
        AccionPendiente.objects.select_for_update()
        .filter(token=str(token or '')[:64], usuario=usuario)
        .first()
    )
    if accion is None:
        raise ErrorAccion("No encontramos esa acción.")
    if accion.estado != AccionPendiente.Estado.PENDIENTE:
        raise ErrorAccion("Esta acción ya fue resuelta.")
    if accion.vencida:
        raise ErrorAccion("La acción venció. Pídele a Gastu que la prepare de nuevo.")
    return accion


def cancelar_accion(usuario, token) -> str:
    with transaction.atomic():
        accion = _obtener_pendiente(usuario, token)
        accion.estado = AccionPendiente.Estado.CANCELADA
        accion.resuelto_en = timezone.now()
        accion.save(update_fields=["estado", "resuelto_en"])
    return "Listo, no hice ningún cambio."


def confirmar_accion(usuario, token) -> str:
    """Aplica la accion. Devuelve el mensaje para el usuario o lanza ErrorAccion."""
    ejecutores = {
        AccionPendiente.Tipo.CREAR_MOVIMIENTO: _crear_movimiento,
        AccionPendiente.Tipo.EDITAR_MOVIMIENTO: _editar_movimiento,
        AccionPendiente.Tipo.ELIMINAR_MOVIMIENTO: _eliminar_movimiento,
        AccionPendiente.Tipo.ELIMINAR_PRESUPUESTO: _eliminar_presupuesto,
    }
    try:
        with transaction.atomic():
            accion = _obtener_pendiente(usuario, token)
            mensaje = ejecutores[accion.tipo](usuario, accion.datos)
            accion.estado = AccionPendiente.Estado.CONFIRMADA
            accion.resuelto_en = timezone.now()
            accion.save(update_fields=["estado", "resuelto_en"])
        return mensaje
    except ErrorAccion:
        # Fuera de la transaccion (que ya hizo rollback): la accion queda FALLIDA
        # para que no se pueda reintentar con datos que ya no son validos.
        ahora = timezone.now()
        pendientes = AccionPendiente.objects.filter(
            usuario=usuario, token=str(token or '')[:64], estado=AccionPendiente.Estado.PENDIENTE,
        )
        pendientes.filter(expira_en__lte=ahora).update(estado=AccionPendiente.Estado.CANCELADA, resuelto_en=ahora)
        pendientes.update(estado=AccionPendiente.Estado.FALLIDA, resuelto_en=ahora)
        raise


# ── Ejecutores ──────────────────────────────────────────────────

def _categoria_valida(categoria_id, tipo) -> Categoria:
    categoria = Categoria.objects.filter(pk=categoria_id, tipo=tipo, activo=True, es_sistema=False).first()
    if categoria is None:
        raise ErrorAccion("La categoría ya no está disponible.")
    return categoria


def _validar_disponible(usuario, monto, fecha, monto_original=None):
    disponible = obtener_disponible(usuario, fecha.month, fecha.year, monto_original=monto_original)
    if monto > disponible:
        raise ErrorAccion(
            f"El monto ({formatear_cop(monto)}) supera tu disponible del mes ({formatear_cop(disponible)})."
        )


def _crear_movimiento(usuario, datos) -> str:
    tipo = datos["tipo"]
    monto = Decimal(datos["monto"])
    categoria = _categoria_valida(datos["categoria_id"], tipo)
    fecha = datetime.fromisoformat(datos["fecha"]).date() if datos.get("fecha") else timezone.localdate()
    if tipo == "EGRESO":
        _validar_disponible(usuario, monto, fecha)
    momento = timezone.now()
    if fecha != timezone.localdate():
        momento = timezone.make_aware(datetime.combine(fecha, time(12, 0)))
    Movimiento.objects.create(
        usuario=usuario, tipo=tipo, categoria=categoria, monto=monto,
        descripcion=datos.get("descripcion") or "Registrado con Gastu IA",
        fecha_registro=momento,
    )
    return f"Registré el {tipo.lower()} de {formatear_cop(monto)} en {categoria.nombre}."


def _movimiento_del_usuario(usuario, movimiento_id) -> Movimiento:
    mov = Movimiento.objects.select_related("categoria").filter(pk=movimiento_id, usuario=usuario).first()
    if mov is None:
        raise ErrorAccion("El movimiento ya no existe.")
    return mov


def _editar_movimiento(usuario, datos) -> str:
    mov = _movimiento_del_usuario(usuario, datos["id"])
    if "categoria_id" in datos:
        mov.categoria = _categoria_valida(datos["categoria_id"], mov.tipo)
    if "monto" in datos:
        monto = Decimal(datos["monto"])
        if mov.tipo == "EGRESO":
            _validar_disponible(usuario, monto, timezone.localdate(), monto_original=mov.monto)
        mov.monto = monto
    if "descripcion" in datos:
        mov.descripcion = datos["descripcion"] or None
    mov.save()
    return f"Actualicé el {mov.tipo.lower()} de {mov.categoria.nombre}."


def _eliminar_movimiento(usuario, datos) -> str:
    mov = _movimiento_del_usuario(usuario, datos["id"])
    texto = f"Eliminé el {mov.tipo.lower()} de {formatear_cop(mov.monto)} en {mov.categoria.nombre}."
    mov.delete()
    return texto


def _eliminar_presupuesto(usuario, datos) -> str:
    pres = Presupuesto.objects.select_related("categoria").filter(pk=datos["id"], usuario=usuario).first()
    if pres is None:
        raise ErrorAccion("El presupuesto ya no existe.")
    texto = f"Eliminé el presupuesto de {pres.categoria.nombre}."
    pres.delete()
    return texto

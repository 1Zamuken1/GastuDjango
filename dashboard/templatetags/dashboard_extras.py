"""Filtros de presentacion del dashboard (no cambian datos, solo como se muestran)."""
import re

from django import template

register = template.Library()

# "CLARO COLOMBIA (Bancolombia)" -> concepto "CLARO COLOMBIA", banco "Bancolombia".
# Lo agrega la captura bancaria al confirmar; en la lista se muestra como etiqueta.
RE_BANCO_FINAL = re.compile(r"^(?P<concepto>.+?)\s*\((?P<banco>[^()]{2,40})\)\s*$")


@register.filter
def separar_banco(descripcion):
    """Devuelve {"concepto", "banco"} a partir de una descripcion con "(Banco)" al final."""
    texto = str(descripcion or "").strip()
    m = RE_BANCO_FINAL.match(texto)
    if not m:
        return {"concepto": texto, "banco": ""}
    return {"concepto": m.group("concepto"), "banco": m.group("banco")}


MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


@register.filter
def fecha_corta(fecha_ddmmaaaa):
    """"09/11/2026" -> "09 nov" (formato de la libreta del agente)."""
    partes = str(fecha_ddmmaaaa or "").split("/")
    if len(partes) == 3 and partes[1].isdigit() and 1 <= int(partes[1]) <= 12:
        return f"{partes[0]} {MESES_CORTOS[int(partes[1]) - 1]}"
    return fecha_ddmmaaaa

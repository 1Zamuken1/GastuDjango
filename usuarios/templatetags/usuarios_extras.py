"""Etiquetas de plantilla de usuarios."""
from django import template

from usuarios.services import avatar_de

register = template.Library()


@register.inclusion_tag('usuarios/includes/_avatar.html')
def avatar_usuario(usuario, clase=''):
    """
    Avatar del usuario (pool, foto de Google o inicial) dentro de un elemento con
    la clase indicada. Lleva data-avatar-slot para que avatar.js lo actualice.
    """
    return {'avatar': avatar_de(usuario), 'clase': clase, 'nombre': usuario.username}

"""
Generador de los avatares de Gastu (la mascota buho) en SVG.

Cada avatar es el mismo busto de Gastu (cabeza, mechones, gafas, pico) con un
atuendo y un accesorio distintos. Los archivos salen a
usuarios/static/usuarios/img/avatares/ y se versionan; este script solo hace
falta para regenerarlos o anadir variantes:

    venv/Scripts/python.exe -m usuarios.avatares_gastu
"""
from pathlib import Path

SALIDA = Path(__file__).resolve().parent / 'static' / 'usuarios' / 'img' / 'avatares'

# Paleta de la mascota (tomada del logo)
TRAZO = '#3b2314'
PLUMA = '#a5622b'
PLUMA_CLARA = '#c27a3a'
CREMA = '#f6dfb8'
MOTA = '#f0c28a'
OJO = '#e8ae2a'
GAFAS = '#1e2a78'
PICO = '#e8892b'

T = f'stroke="{TRAZO}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"'
CUERPO = 'M10 122 C12 100 32 87 60 87 C88 87 108 100 110 122 Z'


def _ojos(cerrados=False):
    if cerrados:
        return ''.join(
            f'<path d="M{x - 8} 63 Q{x} 70 {x + 8} 63" fill="none" stroke="{TRAZO}" stroke-width="2.6" stroke-linecap="round"/>'
            for x in (46, 74)
        )
    partes = []
    for x in (46, 74):
        partes.append(f'<circle cx="{x}" cy="62" r="10.5" fill="{OJO}" {T}/>')
        partes.append(f'<circle cx="{x}" cy="62.5" r="6.5" fill="{TRAZO}"/>')
        partes.append(f'<circle cx="{x - 2.5}" cy="59.5" r="2.4" fill="#fff"/>')
        partes.append(f'<circle cx="{x + 2.6}" cy="65" r="1.1" fill="#fff"/>')
    return ''.join(partes)


def _cabeza(ojos_cerrados=False, mechones=True):
    partes = []
    if mechones:
        for signo in (1, -1):
            x = (lambda v: v) if signo == 1 else (lambda v: 120 - v)
            partes.append(
                f'<path d="M{x(32)} 47 Q{x(22)} 32 {x(14)} 14 Q{x(33)} 22 {x(49)} 33 Z" fill="{PLUMA_CLARA}" {T}/>'
            )
    partes.append(f'<ellipse cx="60" cy="62" rx="34" ry="31" fill="{PLUMA}" {T}/>')
    # Motas de la frente
    for cx, cy in ((50, 39), (60, 36), (70, 39), (55, 43.5), (65, 43.5)):
        partes.append(f'<ellipse cx="{cx}" cy="{cy}" rx="1.4" ry="2.4" fill="{MOTA}"/>')
    # Discos faciales y cejas claras
    partes.append(f'<circle cx="46" cy="62" r="15.5" fill="{CREMA}"/>')
    partes.append(f'<circle cx="74" cy="62" r="15.5" fill="{CREMA}"/>')
    partes.append(f'<path d="M29 49 Q45 42 60 52 Q75 42 91 49" fill="none" stroke="{CREMA}" stroke-width="4.5" stroke-linecap="round"/>')
    partes.append(_ojos(ojos_cerrados))
    # Gafas redondas azul marino
    partes.append(
        f'<g fill="none" stroke="{GAFAS}" stroke-width="3.4">'
        '<circle cx="45.5" cy="62" r="14"/><circle cx="74.5" cy="62" r="14"/>'
        '<path d="M57 58 Q60 55.5 63 58"/><path d="M31.5 60 L27 58"/><path d="M88.5 60 L93 58"/></g>'
    )
    # Pico
    partes.append(f'<path d="M54.5 69 Q60 66.5 65.5 69 L60 81 Z" fill="{PICO}" {T}/>')
    return ''.join(partes)


# ── Atuendos (se dibujan detras de la cabeza) ─────────────────────────────

def _traje():
    return (
        f'<path d="{CUERPO}" fill="#4b5563" {T}/>'
        f'<path d="M47 88 L60 108 L73 88 Z" fill="#fff" {T}/>'
        f'<path d="M57 93 L63 93 L65.5 110 L60 116 L54.5 110 Z" fill="#6b21a8" {T}/>'
        f'<path d="M44 88 L56 112 M76 88 L64 112" fill="none" {T}/>'
        '<path d="M24 104 L24 122 M96 104 L96 122 M34 96 L34 122 M86 96 L86 122" stroke="#6b7280" stroke-width="1.2"/>'
    )


def _sueter(color, cuello='#fff'):
    return (
        f'<path d="{CUERPO}" fill="{color}" {T}/>'
        f'<path d="M45 89 L53 100 L60 92 L67 100 L75 89 Z" fill="{cuello}" {T}/>'
    )


def _camiseta_deporte():
    return (
        f'<path d="{CUERPO}" fill="#047857" {T}/>'
        f'<path d="M46 88 L60 103 L74 88" fill="none" stroke="#fff" stroke-width="4"/>'
        f'<path d="M46 88 L60 103 L74 88" fill="none" {T}/>'
        '<text x="88" y="116" font-family="Arial, sans-serif" font-weight="900" font-size="15" fill="#fff" text-anchor="middle">7</text>'
    )


def _chaqueta_chef():
    botones = ''.join(f'<circle cx="{x}" cy="{y}" r="1.8" fill="{TRAZO}"/>' for x in (52, 68) for y in (104, 114))
    return (
        f'<path d="{CUERPO}" fill="#f8fafc" {T}/>'
        f'<path d="M44 89 Q60 100 76 89" fill="none" {T}/>'
        f'<path d="M50 92 L60 99 L70 92 L68 97 L60 103 L52 97 Z" fill="#dc2626" {T}/>' + botones
    )


def _camisa_safari():
    return (
        f'<path d="{CUERPO}" fill="#b08947" {T}/>'
        f'<path d="M44 88 L54 104 L60 94 L66 104 L76 88 Z" fill="#d9bf8c" {T}/>'
        f'<rect x="24" y="102" width="14" height="11" rx="2" fill="#c9a666" {T}/>'
        f'<rect x="82" y="102" width="14" height="11" rx="2" fill="#c9a666" {T}/>'
    )


def _bata():
    return (
        f'<path d="{CUERPO}" fill="#f8fafc" {T}/>'
        f'<path d="M48 88 L60 106 L72 88 Z" fill="#60a5fa" {T}/>'
        f'<path d="M44 88 L58 120 M76 88 L62 120" fill="none" {T}/>'
        f'<rect x="78" y="104" width="12" height="9" rx="1.5" fill="none" {T}/>'
        '<path d="M82 101 L82 107" stroke="#2563eb" stroke-width="2.2" stroke-linecap="round"/>'
    )


def _rayas():
    rayas = ''.join(f'<path d="M8 {y} L112 {y}" stroke="#1e3a8a" stroke-width="3.2"/>' for y in (100, 108, 116))
    return (
        '<clipPath id="c-rayas"><path d="' + CUERPO + '"/></clipPath>'
        f'<path d="{CUERPO}" fill="#fff"/>'
        f'<g clip-path="url(#c-rayas)">{rayas}</g>'
        f'<path d="{CUERPO}" fill="none" {T}/>'
    )


def _pijama():
    puntos = ''.join(
        f'<circle cx="{x}" cy="{y}" r="2" fill="#fff" opacity=".8"/>'
        for x, y in ((24, 108), (38, 100), (34, 116), (86, 100), (96, 112), (80, 116), (52, 114), (68, 118))
    )
    return f'<path d="{CUERPO}" fill="#93c5fd" {T}/>' + puntos


def _abrigo_bufanda():
    return (
        f'<path d="{CUERPO}" fill="#0f766e" {T}/>'
        f'<path d="M30 92 Q60 104 90 92 L88 101 Q60 113 32 101 Z" fill="#dc2626" {T}/>'
        f'<path d="M70 104 L76 122 L66 122 L62 106 Z" fill="#dc2626" {T}/>'
        '<path d="M40 97 L40 103 M50 100 L50 107 M60 101 L60 108 M70 100 L70 107 M80 97 L80 103" stroke="#fca5a5" stroke-width="2"/>'
    )


def _fiesta():
    return (
        f'<path d="{CUERPO}" fill="#db2777" {T}/>'
        f'<path d="M50 96 L60 101 L50 106 Z M70 96 L60 101 L70 106 Z" fill="#facc15" {T}/>'
        f'<circle cx="60" cy="101" r="2.6" fill="#facc15" {T}/>'
    )


def _gabardina():
    return (
        f'<path d="{CUERPO}" fill="#b08a5a" {T}/>'
        f'<path d="M40 88 L54 110 L48 88 Z M80 88 L66 110 L72 88 Z" fill="#9a7748" {T}/>'
        f'<path d="M52 89 L60 104 L68 89 Z" fill="#f8fafc" {T}/>'
        f'<circle cx="52" cy="114" r="1.8" fill="{TRAZO}"/><circle cx="68" cy="114" r="1.8" fill="{TRAZO}"/>'
    )


# ── Accesorios (se dibujan delante de la cabeza) ──────────────────────────

def _birrete():
    return (
        f'<path d="M38 36 Q60 26 82 36 L80 44 Q60 36 40 44 Z" fill="#1f2937" {T}/>'
        f'<path d="M60 14 L96 26 L60 38 L24 26 Z" fill="#111827" {T}/>'
        f'<path d="M60 26 L88 30 L90 44" fill="none" stroke="#facc15" stroke-width="2"/>'
        f'<circle cx="90" cy="46" r="2.6" fill="#facc15" {T}/>'
    )


def _cinta():
    return (
        f'<path d="M29 44 Q60 28 91 44 L90 52 Q60 36 30 52 Z" fill="#dc2626" {T}/>'
        '<path d="M45 39 Q60 33 75 39" fill="none" stroke="#fff" stroke-width="2"/>'
    )


def _gorro_chef():
    return (
        f'<path d="M38 44 L40 30 L80 30 L82 44 Q60 38 38 44 Z" fill="#fff" {T}/>'
        f'<path d="M40 31 C26 30 28 10 44 13 C46 2 74 2 76 13 C92 10 94 30 80 31 Z" fill="#fff" {T}/>'
        '<path d="M52 18 L52 30 M68 18 L68 30" stroke="#cbd5e1" stroke-width="1.6"/>'
    )


def _salacot():
    return (
        f'<ellipse cx="60" cy="37" rx="42" ry="8" fill="#c9a666" {T}/>'
        f'<path d="M36 36 C36 12 84 12 84 36 Q60 41 36 36 Z" fill="#d9bf8c" {T}/>'
        '<path d="M37 31 Q60 37 83 31" fill="none" stroke="#7c5a2a" stroke-width="3.2"/>'
    )


def _audifonos():
    return (
        f'<path d="M24 62 Q22 16 60 16 Q98 16 96 62" fill="none" stroke="{TRAZO}" stroke-width="7" stroke-linecap="round"/>'
        '<path d="M24 62 Q22 16 60 16 Q98 16 96 62" fill="none" stroke="#7c3aed" stroke-width="3.6" stroke-linecap="round"/>'
        f'<rect x="14" y="50" width="14" height="24" rx="6" fill="#7c3aed" {T}/>'
        f'<rect x="92" y="50" width="14" height="24" rx="6" fill="#7c3aed" {T}/>'
    )


def _antiparras():
    return (
        f'<path d="M27 42 Q60 30 93 42" fill="none" stroke="#475569" stroke-width="4"/>'
        f'<rect x="40" y="31" width="17" height="12" rx="5" fill="#bae6fd" {T}/>'
        f'<rect x="63" y="31" width="17" height="12" rx="5" fill="#bae6fd" {T}/>'
        '<path d="M44 34 L48 34" stroke="#fff" stroke-width="2" stroke-linecap="round"/>'
    )


def _boina():
    return (
        f'<path d="M30 40 C24 22 58 14 82 22 C96 27 94 38 84 40 Q58 34 30 40 Z" fill="#dc2626" {T}/>'
        f'<path d="M58 17 L60 10" fill="none" stroke="{TRAZO}" stroke-width="3" stroke-linecap="round"/>'
    )


def _gorro_dormir():
    return (
        f'<path d="M30 44 Q38 18 62 16 Q90 14 104 44 Q60 32 30 44 Z" fill="#3b82f6" {T}/>'
        f'<path d="M62 16 Q92 10 104 30" fill="none" {T}/>'
        f'<path d="M28 44 Q60 32 92 44 L91 51 Q60 39 29 51 Z" fill="#fff" {T}/>'
        f'<circle cx="104" cy="46" r="6" fill="#fff" {T}/>'
        '<text x="96" y="22" font-family="Arial, sans-serif" font-weight="900" font-size="11" fill="#1e3a8a">z</text>'
    )


def _gorro_lana():
    return (
        f'<path d="M30 46 C28 14 92 14 90 46 Z" fill="#f59e0b" {T}/>'
        '<path d="M44 22 L44 44 M60 18 L60 44 M76 22 L76 44" stroke="#d97706" stroke-width="2.2"/>'
        f'<rect x="27" y="40" width="66" height="11" rx="5" fill="#fbbf24" {T}/>'
        f'<circle cx="60" cy="14" r="6.5" fill="#fff" {T}/>'
    )


def _cono_fiesta():
    confeti = ''.join(
        f'<rect x="{x}" y="{y}" width="3.4" height="3.4" rx=".6" fill="{c}" transform="rotate({r} {x} {y})"/>'
        for x, y, c, r in ((16, 30, '#22c55e', 20), (100, 26, '#3b82f6', -15), (22, 82, '#facc15', 35), (101, 80, '#ef4444', 10), (14, 56, '#db2777', -25))
    )
    return (
        f'<path d="M48 38 L62 4 L78 36 Q63 42 48 38 Z" fill="#facc15" {T}/>'
        '<path d="M52 29 L70 25 M56 19 L66 17" stroke="#db2777" stroke-width="3"/>'
        f'<circle cx="62" cy="5" r="4" fill="#db2777" {T}/>' + confeti
    )


def _sombrero_detective():
    return (
        f'<path d="M22 42 Q60 30 98 42 Q96 48 88 46 Q60 38 32 46 Q24 48 22 42 Z" fill="#57534e" {T}/>'
        f'<path d="M36 40 C36 18 42 14 60 20 C78 14 84 18 84 40 Q60 34 36 40 Z" fill="#78716c" {T}/>'
        '<path d="M37 35 Q60 29 83 35" fill="none" stroke="#292524" stroke-width="4"/>'
    )


def _lupa():
    return (
        f'<path d="M100 112 L112 122" stroke="{TRAZO}" stroke-width="5" stroke-linecap="round"/>'
        f'<circle cx="94" cy="104" r="9" fill="#e0f2fe" fill-opacity=".75" stroke="#57534e" stroke-width="3.2"/>'
    )


# clave: (nombre, fondo, atuendo, accesorio, ojos_cerrados, mechones)
VARIANTES = {
    'clasico': ('Gastu clásico', '#dbeafe', _traje, None, False, True),
    'estudiante': ('Gastu estudiante', '#e0e7ff', lambda: _sueter('#1d4ed8'), _birrete, False, False),
    'deportista': ('Gastu deportista', '#dcfce7', _camiseta_deporte, _cinta, False, True),
    'chef': ('Gastu chef', '#fee2e2', _chaqueta_chef, _gorro_chef, False, False),
    'viajero': ('Gastu viajero', '#fef3c7', _camisa_safari, _salacot, False, False),
    'musico': ('Gastu músico', '#ede9fe', lambda: _sueter('#4c1d95', '#a78bfa'), _audifonos, False, True),
    'cientifico': ('Gastu científico', '#cffafe', _bata, _antiparras, False, True),
    'artista': ('Gastu artista', '#ffe4e6', _rayas, _boina, False, False),
    'dormilon': ('Gastu dormilón', '#e0f2fe', _pijama, _gorro_dormir, True, False),
    'invierno': ('Gastu invierno', '#ccfbf1', _abrigo_bufanda, _gorro_lana, False, False),
    'fiesta': ('Gastu fiestero', '#fce7f3', _fiesta, _cono_fiesta, False, True),
    'detective': ('Gastu detective', '#f5f5f4', _gabardina, lambda: _sombrero_detective() + _lupa(), False, False),
}


def svg_de(clave):
    nombre, fondo, atuendo, accesorio, cerrados, mechones = VARIANTES[clave]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" '
        f'aria-label="{nombre}"><rect width="120" height="120" fill="{fondo}"/>'
        f'{atuendo()}{_cabeza(cerrados, mechones)}{accesorio() if accesorio else ""}</svg>\n'
    )


def generar():
    SALIDA.mkdir(parents=True, exist_ok=True)
    for clave in VARIANTES:
        (SALIDA / f'gastu_{clave}.svg').write_text(svg_de(clave), encoding='utf-8')
    return len(VARIANTES)


if __name__ == '__main__':
    print('generados', generar())

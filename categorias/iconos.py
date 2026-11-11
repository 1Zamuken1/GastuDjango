"""Iconos de Lucide disponibles para las categorias.

Cada categoria guarda el nombre de un icono de https://lucide.dev. La lista
es corta a proposito: el administrador elige entre iconos que ya se ven bien
en las cards y en el selector de categorias.
"""

ICONO_POR_DEFECTO = 'tag'

ICONOS_CATEGORIA = [
    ('tag', 'Etiqueta'),
    # Ingresos
    ('briefcase', 'Maletín'),
    ('laptop', 'Portátil'),
    ('trending-up', 'Tendencia al alza'),
    ('key-round', 'Llave'),
    ('gift', 'Regalo'),
    ('shopping-bag', 'Bolsa de compras'),
    ('arrow-left-right', 'Transferencia'),
    ('rotate-ccw', 'Reembolso'),
    ('trophy', 'Trofeo'),
    ('circle-plus', 'Más'),
    ('wallet', 'Billetera'),
    ('banknote', 'Billete'),
    ('hand-coins', 'Monedas'),
    # Egresos
    ('utensils', 'Comida'),
    ('shopping-cart', 'Mercado'),
    ('bus', 'Bus'),
    ('car', 'Carro'),
    ('fuel', 'Gasolina'),
    ('house', 'Casa'),
    ('lightbulb', 'Servicios'),
    ('wifi', 'Internet'),
    ('heart-pulse', 'Salud'),
    ('graduation-cap', 'Educación'),
    ('clapperboard', 'Entretenimiento'),
    ('shirt', 'Ropa'),
    ('smartphone', 'Celular'),
    ('credit-card', 'Tarjeta'),
    ('receipt', 'Recibo'),
    ('dumbbell', 'Deporte'),
    ('dog', 'Mascotas'),
    ('baby', 'Hijos'),
    ('coffee', 'Café'),
    # Ahorro
    ('shield', 'Escudo'),
    ('plane', 'Viaje'),
    ('book-open', 'Libro'),
    ('chart-line', 'Inversión'),
    ('armchair', 'Retiro'),
    ('piggy-bank', 'Alcancía'),
]

# Icono de las categorias base, por nombre en minusculas.
ICONOS_BASE = {
    'saldo inicial': 'wallet',
    'salario': 'briefcase',
    'freelance': 'laptop',
    'inversiones': 'trending-up',
    'arriendo recibido': 'key-round',
    'bonificaciones': 'gift',
    'ventas': 'shopping-bag',
    'transferencias': 'arrow-left-right',
    'reembolsos': 'rotate-ccw',
    'premios': 'trophy',
    'otros ingresos': 'circle-plus',
    'alimentación': 'utensils',
    'transporte': 'bus',
    'vivienda': 'house',
    'salud': 'heart-pulse',
    'educación': 'graduation-cap',
    'entretenimiento': 'clapperboard',
    'ropa y calzado': 'shirt',
    'tecnología': 'smartphone',
    'deudas y créditos': 'credit-card',
    'otros gastos': 'receipt',
    'fondo de emergencia': 'shield',
    'meta de viaje': 'plane',
    'educación futura': 'book-open',
    'inversión planeada': 'chart-line',
    'retiro / pensión': 'armchair',
    'otros ahorros': 'piggy-bank',
}


def icono_sugerido(nombre):
    """Icono para una categoria segun su nombre; etiqueta si no es una categoria base."""
    return ICONOS_BASE.get((nombre or '').strip().lower(), ICONO_POR_DEFECTO)

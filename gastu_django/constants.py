"""
Constantes compartidas del proyecto GastuApp.

Centraliza valores que se reutilizan en multiples apps para
evitar duplicacion y garantizar consistencia.
"""

from decimal import Decimal

ZERO = Decimal('0')

# Nombres de meses en español, indexados por numero (1-12).
# Se usa dict para permitir acceso seguro con .get() y compatibilidad
# con acceso por indice MESES_ES[mes] donde mes es 1-12.
MESES_ES = {
    1: 'Enero',    2: 'Febrero',   3: 'Marzo',     4: 'Abril',
    5: 'Mayo',     6: 'Junio',     7: 'Julio',     8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}

# Paleta de colores para el grafico de distribución (pie/donut chart).
PIE_COLORES = [
    '#e11d48', '#f87171', '#fbbf24', '#a3e635',
    '#34d399', '#38bdf8', '#818cf8', '#f472b6',
]

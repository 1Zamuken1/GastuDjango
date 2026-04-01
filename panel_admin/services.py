"""
Servicios del panel de administracion.
Contiene la logica de negocio para importacion masiva de datos.
"""

import csv
import io
from categorias.models import Categoria


# ──────────────────────────────────────────────────────────────
#  IMPORTACION MASIVA DE CATEGORIAS (CSV)
# ──────────────────────────────────────────────────────────────

TIPOS_VALIDOS = {'INGRESO', 'EGRESO', 'AHORRO'}

COLUMNAS_REQUERIDAS = {'nombre', 'tipo'}


def procesar_csv_categorias(archivo_csv):
    """
    Procesa un archivo CSV subido por el administrador e importa categorias
    al sistema. Omite filas que representen duplicados (mismo nombre + tipo).

    El archivo CSV debe tener encabezados en la primera fila.
    Columnas reconocidas:
        - nombre      (obligatorio): nombre de la categoria.
        - tipo        (obligatorio): INGRESO, EGRESO o AHORRO.
        - descripcion (opcional):   descripcion corta.
        - activo      (opcional):   true/false. Por defecto: true.

    Args:
        archivo_csv: objeto InMemoryUploadedFile recibido del formulario.

    Returns:
        dict con:
            - creadas (int):   cantidad de categorias importadas.
            - omitidas (int):  cantidad de filas omitidas por duplicado.
            - errores (list):  lista de mensajes de error por fila invalida.
            - total (int):     total de filas procesadas (sin encabezado).
    """
    creadas  = 0
    omitidas = 0
    errores  = []

    try:
        contenido = archivo_csv.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        contenido = archivo_csv.read().decode('latin-1')

    reader = csv.DictReader(io.StringIO(contenido))

    # Normalizar encabezados a minusculas sin espacios
    if reader.fieldnames is None:
        return {
            'creadas': 0, 'omitidas': 0,
            'errores': ['El archivo esta vacio o no tiene encabezados.'],
            'total': 0,
        }

    encabezados = {c.strip().lower() for c in reader.fieldnames}

    columnas_faltantes = COLUMNAS_REQUERIDAS - encabezados
    if columnas_faltantes:
        return {
            'creadas': 0, 'omitidas': 0,
            'errores': [
                f'Faltan columnas obligatorias en el CSV: {", ".join(columnas_faltantes)}. '
                f'Las columnas requeridas son: nombre, tipo.'
            ],
            'total': 0,
        }

    for numero_fila, fila in enumerate(reader, start=2):
        # Limpiar y normalizar los valores de la fila
        nombre      = (fila.get('nombre') or '').strip()
        tipo_raw    = (fila.get('tipo') or '').strip().upper()
        descripcion = (fila.get('descripcion') or '').strip()
        activo_raw  = (fila.get('activo') or 'true').strip().lower()
        activo      = activo_raw not in ('false', '0', 'no', 'n')

        # Validar campos obligatorios
        if not nombre:
            errores.append(f'Fila {numero_fila}: el campo "nombre" esta vacio. Fila omitida.')
            continue

        if tipo_raw not in TIPOS_VALIDOS:
            errores.append(
                f'Fila {numero_fila}: tipo "{tipo_raw}" no valido para "{nombre}". '
                f'Valores aceptados: INGRESO, EGRESO, AHORRO. Fila omitida.'
            )
            continue

        # Verificar duplicado (nombre exacto sin distinguir mayusculas + tipo)
        existe = Categoria.objects.filter(
            nombre__iexact=nombre,
            tipo=tipo_raw,
        ).exists()

        if existe:
            omitidas += 1
            continue

        # Crear la categoria
        Categoria.objects.create(
            nombre=nombre,
            tipo=tipo_raw,
            descripcion=descripcion or None,
            activo=activo,
        )
        creadas += 1

    total = creadas + omitidas + len(errores)
    return {
        'creadas':  creadas,
        'omitidas': omitidas,
        'errores':  errores,
        'total':    total,
    }

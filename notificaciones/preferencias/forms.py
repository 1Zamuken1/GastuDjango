from django import forms
from .models import PreferenciasAlertas


# ── Presentacion del formulario (solo textos y agrupacion; los campos, sus
#    nombres y su validacion no cambian) ─────────────────────────────────────

ETIQUETAS = {
    'umbral_advertencia_porcentaje': 'Aviso de presupuesto',
    'egreso_grande_porcentaje': 'Considerar grande un gasto desde',
    'alerta_egreso_grande_activa': 'Gasto grande',
    'alert_gasto_incremental_enabled': 'Gastos en aumento',
    'alert_gasto_incremental_porcentaje': 'Aumento mínimo',
    'alert_gasto_incremental_meses': 'Comparar con los últimos',
    'alert_reduccion_ingresos_enabled': 'Ingresos a la baja',
    'alert_reduccion_ingresos_porcentaje': 'Caída mínima',
    'alert_patron_inusual_enabled': 'Patrón de gasto inusual',
    'alert_concentracion_gastos_enabled': 'Gasto concentrado en una categoría',
    'alert_concentracion_gastos_porcentaje': 'Concentración desde',
    'alert_concepto_sin_uso_enabled': 'Ingreso habitual sin registrar',
    'alert_concepto_sin_uso_dias': 'Días sin registrarlo',
    'alert_velocidad_gasto_enabled': 'Ritmo de gasto acelerado',
    'alert_inactividad_ingresos_enabled': 'Sin ingresos recientes',
    'alert_inactividad_dias': 'Días sin ingresos',
    'alert_egresos_agrupados_enabled': 'Muchos gastos seguidos',
    'alert_egresos_agrupados_cantidad': 'Cantidad de gastos',
    'alert_egresos_agrupados_horas': 'En un lapso de',
    'meta_ahorro_mensual': 'Meta de ahorro mensual',
    'alert_meta_ahorro_enabled': 'Avance de la meta de ahorro',
    'alert_balance_critico_enabled': 'Balance crítico',
    'alert_recordatorio_ahorro_enabled': 'Recordatorio de cuota de ahorro',
    'alert_recordatorio_ahorro_dias': 'Avisar con anticipación de',
    'alert_micro_gastos_enabled': 'Muchos gastos pequeños',
    'alert_micro_gastos_cantidad': 'Cantidad de gastos',
    'alert_micro_gastos_monto_max': 'De máximo',
    'alert_gastos_hormiga_enabled': 'Gastos hormiga del día',
    'alert_gastos_hormiga_monto_dia': 'Cuando sumen al día',
    'alert_proyeccion_sobregasto_enabled': 'Proyección de sobregasto',
    'alert_comparacion_periodo_enabled': 'Comparación con el mes anterior',
    'alert_dia_mes_critico_enabled': 'Mes en riesgo',
    'alert_dia_mes_critico_porcentaje': 'Gasto de tus ingresos desde',
    'alert_egreso_sin_concepto_enabled': 'Gastos sin descripción',
    'alert_egreso_sin_concepto_cantidad': 'Cantidad de gastos',
    'alert_ingreso_inusual_enabled': 'Ingreso inusual',
    'alert_ingreso_inusual_multiplicador': 'Veces tu ingreso habitual',
}

AYUDAS = {
    'umbral_advertencia_porcentaje': 'Te avisamos cuando un presupuesto llega a este porcentaje.',
    'alerta_egreso_grande_activa': 'Un solo gasto que se lleva una parte grande de tus ingresos del mes.',
    'alert_gasto_incremental_enabled': 'Una categoría en la que gastas cada vez más.',
    'alert_reduccion_ingresos_enabled': 'Tus ingresos bajan frente a meses anteriores.',
    'alert_patron_inusual_enabled': 'Un gasto que no se parece a tus hábitos.',
    'alert_concentracion_gastos_enabled': 'Una sola categoría acumula buena parte de tus gastos.',
    'alert_concepto_sin_uso_enabled': 'Un ingreso que sueles tener y no has registrado.',
    'alert_velocidad_gasto_enabled': 'Gastas más rápido de lo normal para esta altura del mes.',
    'alert_inactividad_ingresos_enabled': 'Pasan varios días sin que registres ingresos.',
    'alert_egresos_agrupados_enabled': 'Varios gastos registrados en poco tiempo.',
    'alert_meta_ahorro_enabled': 'Seguimiento de tu meta de ahorro del mes.',
    'alert_balance_critico_enabled': 'Tu saldo queda en cero o en negativo.',
    'alert_recordatorio_ahorro_enabled': 'Antes de la fecha de pago de tus cuotas de ahorro.',
    'alert_micro_gastos_enabled': 'Muchos gastos pequeños que juntos suman bastante.',
    'alert_gastos_hormiga_enabled': 'Gastos pequeños del día que llegan a un tope.',
    'alert_proyeccion_sobregasto_enabled': 'Si sigues a este ritmo, gastarías más de lo que ingresa.',
    'alert_comparacion_periodo_enabled': 'Cómo vas frente al mismo punto del mes pasado.',
    'alert_dia_mes_critico_enabled': 'Antes de fin de mes ya gastaste gran parte de tus ingresos.',
    'alert_egreso_sin_concepto_enabled': 'Gastos registrados sin descripción.',
    'alert_ingreso_inusual_enabled': 'Un ingreso mucho mayor que el habitual.',
}

# Unidad que se muestra junto a cada valor numerico.
UNIDADES = {
    'umbral_advertencia_porcentaje': '%', 'egreso_grande_porcentaje': '% del ingreso',
    'alert_gasto_incremental_porcentaje': '%', 'alert_gasto_incremental_meses': 'meses',
    'alert_reduccion_ingresos_porcentaje': '%', 'alert_concentracion_gastos_porcentaje': '%',
    'alert_concepto_sin_uso_dias': 'días', 'alert_inactividad_dias': 'días',
    'alert_egresos_agrupados_cantidad': 'gastos', 'alert_egresos_agrupados_horas': 'horas',
    'meta_ahorro_mensual': '$', 'alert_recordatorio_ahorro_dias': 'días',
    'alert_micro_gastos_cantidad': 'gastos', 'alert_micro_gastos_monto_max': '$',
    'alert_gastos_hormiga_monto_dia': '$', 'alert_dia_mes_critico_porcentaje': '%',
    'alert_egreso_sin_concepto_cantidad': 'gastos', 'alert_ingreso_inusual_multiplicador': 'veces',
}

# (titulo, descripcion, icono, [(interruptor o None, [campos numericos])])
SECCIONES = [
    ('Presupuestos y gastos grandes', 'Lo básico para no pasarte del plan.', 'gauge', [
        (None, ['umbral_advertencia_porcentaje']),
        ('alerta_egreso_grande_activa', ['egreso_grande_porcentaje']),
        ('alert_dia_mes_critico_enabled', ['alert_dia_mes_critico_porcentaje']),
        ('alert_proyeccion_sobregasto_enabled', []),
        ('alert_balance_critico_enabled', []),
    ]),
    ('Tendencias', 'Cambios en tus hábitos de un mes a otro.', 'trending-up', [
        ('alert_gasto_incremental_enabled', ['alert_gasto_incremental_porcentaje', 'alert_gasto_incremental_meses']),
        ('alert_reduccion_ingresos_enabled', ['alert_reduccion_ingresos_porcentaje']),
        ('alert_comparacion_periodo_enabled', []),
        ('alert_patron_inusual_enabled', []),
        ('alert_velocidad_gasto_enabled', []),
    ]),
    ('Categorías e ingresos', 'Dónde se concentra tu dinero y qué falta registrar.', 'layers', [
        ('alert_concentracion_gastos_enabled', ['alert_concentracion_gastos_porcentaje']),
        ('alert_concepto_sin_uso_enabled', ['alert_concepto_sin_uso_dias']),
        ('alert_inactividad_ingresos_enabled', ['alert_inactividad_dias']),
        ('alert_ingreso_inusual_enabled', ['alert_ingreso_inusual_multiplicador']),
    ]),
    ('Gastos pequeños y frecuentes', 'Lo que se escapa sin darte cuenta.', 'coins', [
        ('alert_micro_gastos_enabled', ['alert_micro_gastos_cantidad', 'alert_micro_gastos_monto_max']),
        ('alert_gastos_hormiga_enabled', ['alert_gastos_hormiga_monto_dia']),
        ('alert_egresos_agrupados_enabled', ['alert_egresos_agrupados_cantidad', 'alert_egresos_agrupados_horas']),
        ('alert_egreso_sin_concepto_enabled', ['alert_egreso_sin_concepto_cantidad']),
    ]),
    ('Ahorro', 'Tu meta mensual y las cuotas de tus metas.', 'piggy-bank', [
        ('alert_meta_ahorro_enabled', ['meta_ahorro_mensual']),
        ('alert_recordatorio_ahorro_enabled', ['alert_recordatorio_ahorro_dias']),
    ]),
]


class PreferenciasAlertasForm(forms.ModelForm):
    class Meta:
        model = PreferenciasAlertas
        fields = [
            'umbral_advertencia_porcentaje',
            'egreso_grande_porcentaje',
            'alerta_egreso_grande_activa',

            'alert_gasto_incremental_enabled',
            'alert_gasto_incremental_porcentaje',
            'alert_gasto_incremental_meses',
            'alert_reduccion_ingresos_enabled',
            'alert_reduccion_ingresos_porcentaje',
            'alert_patron_inusual_enabled',

            'alert_concentracion_gastos_enabled',
            'alert_concentracion_gastos_porcentaje',
            'alert_concepto_sin_uso_enabled',
            'alert_concepto_sin_uso_dias',

            'alert_velocidad_gasto_enabled',
            'alert_inactividad_ingresos_enabled',
            'alert_inactividad_dias',
            'alert_egresos_agrupados_enabled',
            'alert_egresos_agrupados_cantidad',
            'alert_egresos_agrupados_horas',

            'meta_ahorro_mensual',
            'alert_meta_ahorro_enabled',
            'alert_balance_critico_enabled',
            'alert_recordatorio_ahorro_enabled',
            'alert_recordatorio_ahorro_dias',

            'alert_micro_gastos_enabled',
            'alert_micro_gastos_cantidad',
            'alert_micro_gastos_monto_max',
            'alert_gastos_hormiga_enabled',
            'alert_gastos_hormiga_monto_dia',

            'alert_proyeccion_sobregasto_enabled',
            'alert_comparacion_periodo_enabled',
            'alert_dia_mes_critico_enabled',
            'alert_dia_mes_critico_porcentaje',

            'alert_egreso_sin_concepto_enabled',
            'alert_egreso_sin_concepto_cantidad',
            'alert_ingreso_inusual_enabled',
            'alert_ingreso_inusual_multiplicador',
        ]
        labels = ETIQUETAS
        help_texts = AYUDAS

    def secciones(self):
        """
        Campos agrupados para la pestana Preferencias de Mi perfil.

        Devuelve todos los campos del formulario exactamente una vez: si alguno no
        aparece en SECCIONES, va a una seccion "Otras alertas" para que nunca deje de
        enviarse (un campo omitido se guardaria vacio).
        """
        usados, resultado = set(), []
        for titulo, descripcion, icono, filas in SECCIONES:
            items = []
            for interruptor, numericos in filas:
                campos = [n for n in [interruptor, *numericos] if n and n in self.fields]
                usados.update(campos)
                items.append({
                    'interruptor': self[interruptor] if interruptor in self.fields else None,
                    'valores': [
                        {'campo': self[n], 'unidad': UNIDADES.get(n, '')}
                        for n in numericos if n in self.fields
                    ],
                })
            resultado.append({'titulo': titulo, 'descripcion': descripcion, 'icono': icono, 'filas': items})
        restantes = [n for n in self.fields if n not in usados]
        if restantes:
            resultado.append({
                'titulo': 'Otras alertas', 'descripcion': '', 'icono': 'bell',
                'filas': [{'interruptor': None, 'valores': [{'campo': self[n], 'unidad': UNIDADES.get(n, '')} for n in restantes]}],
            })
        return resultado

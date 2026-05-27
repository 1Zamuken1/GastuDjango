> Hola tengo una duda y quiero que me respondas de manera directa y realista, tengo el modulo de ahorros este modulo me permite hacer aportes para ir cumpliendo la meta del ahorro,
que pasa cuando hago un aporte, el sistema deshabilita la posibilidad de hacer otro aporte si no estoy en la fecha establecida ademas de impedirme actualizar el valor del apórte, en
base a esto si yo por ejemplo hago un aporte hoy de 1 millon, y el dia de maañana me llega un dinero que no quiero gastar sino que quiero utilizar para adelantar un pago al ahorro yn  el sistema no me deja hacerlo, quiere decir que esta mal planteada esa idea, cierto? pensaria que deberia permitirse hacer aportes a capital algo asi como se manejan en los pagos de
creditos donde indepentiene del interes puede aportar ya sea para reduccion de cuota o reduccion de plazo

---

# Plan de Implementación Aprobado por Product Owner
*(Instrucciones directas para el Agente Antigravity de Desarrollo)*

**Contexto:**
Se requiere añadir la funcionalidad de "Aporte Libre / Extraordinario" (Opción A: Reducción de Cuota) al módulo de Ahorros.
Restricciones críticas:
1. **NO rediseñar la estructura base del SM.** El sistema de cuotas estrictas se mantiene.
2. **Alta Trazabilidad.** El aporte extraordinario debe generar historial, impactar el dashboard, la utilidad mensual, y la barra de progreso de forma idéntica a un aporte normal. No se deben crear transacciones fantasma.

**Estrategia: Adelanto de Capital sobre Cuota Activa**
El aporte extraordinario utilizará el *endpoint* actual (`registrar_aporte`), pero con un flag (`extraordinario=true`) que evite el filtro de fecha (`cuota_disponible_pago`).
Al hacer el POST, el sistema buscará la primera cuota `PENDIENTE`, le asignará el pago total ingresado por el usuario y la marcará como `APORTADO`.
Dado que los Signals (`post_save` en `AporteAhorro`) ya están configurados en el proyecto, esto desencadenará toda la trazabilidad automática (Acción en Historial, actualización de ResumenMensual). Finalmente, la función existente `recalcular_aportes_restantes` reducirá automáticamente las cuotas futuras compensando el pago extra.

---

## Tareas a Ejecutar (Frontend & Backend)

### 1. Frontend: Añadir Panel de Aporte Libre
**Archivo:** `ahorros/templates/ahorros/aporte.html`
**Ubicación:** Dentro de `<div class="detalle-modal__content">`, preferiblemente entre "Especificaciones" y "Resumen Cuotas" (o en un lugar visualmente destacado antes de la tabla).
**Acción:**
- Añadir un pequeño contenedor/tarjeta con título "Aporte Libre / Extraordinario".
- Incluir un pequeño formulario que envíe un POST a `{% url 'ahorros:registrar_aporte' meta_id=ahorro.id %}`.
- El formulario debe tener:
  - `{% csrf_token %}`
  - `<input type="hidden" name="extraordinario" value="true">`
  - Un `<input type="number" name="aporte" step="0.01" min="0.01">` donde el usuario digita libremente el valor.
  - Un `<button type="submit">`.
- Usar las clases CSS de Tailwind o nativas del proyecto para que armonice con el diseño actual.

### 2. Backend: Habilitar Bypass en la Vista
**Archivo:** `ahorros/views.py`
**Función:** `registrar_aporte(request, meta_id, aporte_id=None)`
**Acción:**
En el bloque de request.POST (línea ~230+):
1. Leer el flag: `es_extraordinario = request.POST.get('extraordinario') == 'true'`
2. Cambiar la lógica de búsqueda de cuota. Actualmente dice:
   ```python
   if aporte_id:
       cuota = ...
   else:
       cuota_temp = find_cuota_disponible(meta_id, usuario)
   ```
   **Debe quedar:**
   ```python
   if es_extraordinario:
       cuota_temp = AporteAhorro.objects.filter(
           ahorro=ahorro, estado_ap=AporteAhorro.EstadoAp.PENDIENTE
       ).order_by('fecha_limite').first()
       if not cuota_temp:
           return JsonResponse({"ok": False, "error": "No hay cuotas pendientes para aplicar el aporte."})
       cuota = AporteAhorro.objects.select_for_update().get(id=cuota_temp.id)
   elif aporte_id:
       cuota = AporteAhorro.objects.select_for_update().get(id=aporte_id, ahorro=ahorro)
   else:
       cuota_temp = find_cuota_disponible(meta_id, usuario)
       if not cuota_temp:
           return JsonResponse({"ok": False, "error": "No hay cuota disponible para aportar hoy."})
       cuota = AporteAhorro.objects.select_for_update().get(id=cuota_temp.id)
   ```
3. Bypass en la validación `cuota_disponible_pago`. Actualmente dice:
   ```python
   if not cuota_disponible_pago(cuota, ahorro.frecuencia):
       return JsonResponse({"ok": False, "error": "La cuota no esta disponible para pago todavia."})
   ```
   **Debe quedar:**
   ```python
   if not es_extraordinario and not cuota_disponible_pago(cuota, ahorro.frecuencia):
       return JsonResponse({"ok": False, "error": "La cuota no esta disponible para pago todavia."})
   ```

### 3. Bugs Previstos y Validación
- **Idempotencia y bloqueos de BD:** Ya manejado por `select_for_update()` en la vista.
- **Trazabilidad en Dashboard:** El trigger `post_save` de `AporteAhorro` ejecutará `actualizar_resumen()`. El nuevo saldo aparecerá restado en el Dashboard en la variable `disponible` y sumado en `total_ahorros`.
- **Trazabilidad en IA:** La IA usa el historial y los modelos de transacciones. Puesto que el estado de la cuota cambió formalmente a `APORTADO`, la IA interpretará el aumento.
- **Redondeo Residual:** `recalcular_aportes_restantes` asignará el resto entre las siguientes cuotas de manera nivelada, la última cuota absorberá decimales residuales (lógica segura que ya existe en `services.py`).

**Fin del Documento.** Ejecutar tal cual para no romper el ambiente de producción.
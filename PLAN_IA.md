# PLAN DE IMPLEMENTACIÓN — AGENTE INTELIGENTE GASTU (IA)
## GastuDjango / GastuApp

> **Objetivo:** Dotar al agente financiero GASTU de capacidades avanzadas ("superpoderes") compatibles con modelos LLM servidos por Groq (`llama-3.3-70b-versatile` y modelos afines), eliminando alucinaciones aritméticas mediante ejecución determinista en Python, habilitando operaciones CRUD seguras con confirmación humana, exportación/importación inteligente y una metodología estandarizada para la creación de Skills a través de chat.
> **Ubicación:** Raíz del proyecto (`PLAN_IA.md`). Documento temporal, eliminable tras completar el ciclo de implementación.

---

## 1. Diagnóstico del Estado Actual del Agente

A partir del análisis técnico de `agente_financiero` y módulos relacionados:

### Lo que funciona bien hoy
- Conexión vía API con Groq con tool calling nativo (`preguntar_a_groq`).
- `RecolectorDatos` captura un buen panorama del usuario (resumen mensual, metas, presupuestos, programaciones).
- Sistema de alertas proactivas con detección de 6 situaciones financieras y fallback cuando no hay cuota de IA.
- Suite de 38 pruebas unitarias sólidas (`pytest`) para modelos, recolector y vistas.

### Cuellos de botella y limitaciones críticas detectadas
1. **Solo 3 herramientas de solo lectura y acotadas a Movimientos:**
   - Únicamente puede consultar movimientos, total mensual y gastos por categoría.
   - No tiene herramientas para consultar **ahorros/cuotas**, **presupuestos activos**, **programaciones recurrentes**, **tendencias históricas** ni categorías disponibles.
2. **Cero capacidad de mutación (Sin CRUD):**
   - El usuario no puede pedirle *"GASTU, anota un gasto de $45.000 en Almuerzo"* o *"Crea un presupuesto de $300.000 para transporte"*. El agente es puramente consultivo.
3. **Alucinaciones y Errores Aritméticos:**
   - Cuando se le pide calcular proyecciones compuestas, cuántos días faltan para una meta o cuánto le queda por gastar a un ritmo diario, el LLM calcula "mentalmente" y falla en la matemática y en el manejo de fechas en español.
4. **Tool Calling de una sola pasada (Single-round):**
   - El cliente solo realiza una llamada con tools y luego pide la respuesta final; no permite razonamiento multi-paso encadenado (ej. consultar categoría -> verificar saldo disponible -> registrar movimiento).
5. **Falta de integración con Exportación e Importación:**
   - La aplicación ya cuenta con excelentes exportadores en `views_exportar.py` (Excel con `openpyxl`, PDF con `xhtml2pdf` y CSV), pero el agente no tiene forma de generar o vincular estos reportes cuando el usuario los solicita.
6. **Bug detectado en `herramientas.py`:**
   - `obtener_resumen_periodo` utiliza `Sum(1)` en lugar de `Count('id')`, lo que genera recuentos inconsistentes.

---

## 2. Pilares de los Nuevos "Superpoderes"

```mermaid
flowchart TD
    subgraph ARQ_AGENTE["Arquitectura Avanzada del Agente GASTU"]
        LLM[Groq Cloud LLM\nllama-3.3-70b-versatile]
        ORQ[Orquestador Multi-Paso\ngroq_client.py]
        
        subgraph TOOLS_READ["Herramientas de Consulta Determinista"]
            T1[Movimientos & Filtros Avanzados]
            T2[Metas de Ahorro & Cuotas]
            T3[Presupuestos & Estados Reales]
            T4[Programaciones Recurrentes]
        end

        subgraph TOOLS_MATH["Herramientas Matemáticas Exactas (Python)"]
            M1[Calculadora Financiera\nInterés, Ritmo de Gasto, Días Restantes]
            M2[Simulador de Capacidad de Endeudamiento]
            M3[Proyector de Cumplimiento de Ahorro]
        end

        subgraph TOOLS_WRITE["Herramientas CRUD con Human-in-the-Loop"]
            W1[Registrar/Editar Movimiento]
            W2[Crear/Ajustar Presupuesto]
            W3[Aportar a Meta de Ahorro]
            W4[Acciones Destructivas\n(Payload de Confirmación Requerida)]
        end

        subgraph SKILLS_EXP_IMP["Habilidades de Exportación & Archivos"]
            E1[Generador de Enlaces de Descarga\nExcel, PDF, CSV]
            I1[Asistente de Ingesta Masiva / CSV]
        end
    end

    LLM <--> ORQ
    ORQ --> TOOLS_READ
    ORQ --> TOOLS_MATH
    ORQ --> TOOLS_WRITE
    ORQ --> SKILLS_EXP_IMP
```

---

## 3. Desglose de Fases de Implementación

### Fase 1: Motor Matemático Determinista y Correcciones Base

**Objetivo:** El modelo **nunca** calcula cifras en texto; toda operación aritmética es delegada a Python utilizando tipos `Decimal` exactos.

1. **Corrección de bugs existentes:**
   - Reemplazar `Sum(1)` por `Count('id')` en `herramientas.py:obtener_resumen_periodo`.
2. **Creación de herramientas matemáticas (`tools_financieras.py` o dentro de `herramientas.py`):**
   - `calcular_proyeccion_meta(meta_id, aporte_adicional_mensual)`: Calcula matemáticamente la fecha estimada exacta de finalización y el porcentaje de aceleración.
   - `calcular_ritmo_gasto(categoria_id, periodo_dias)`: Calcula gasto promedio diario, gasto proyectado a fin de mes vs límite de presupuesto y días de supervivencia del saldo actual.
   - `calcular_capacidad_disponible()`: Evalúa ingresos netos menos compromisos fijos (programaciones activas + cuotas de ahorro obligatorias) para determinar el disponible real sin riesgo de sobregiro.

---

### Fase 2: Soporte para Operaciones CRUD y Protocolo Human-in-the-Loop

**Objetivo:** Permitir que el agente ejecute acciones directamente en la base de datos bajo un marco de permisos estricto.

1. **Herramientas de Escritura Segura:**
   - `crear_movimiento(tipo, categoria_nombre_o_id, monto, descripcion, fecha=None)`: Localiza la categoría más cercana, valida saldo suficiente para egresos, crea la instancia llamando al servicio y registra la auditoría en `AccionHistorial`.
   - `crear_presupuesto(categoria_id, limite, fecha_inicio, fecha_fin)`.
   - `registrar_aporte_ahorro(meta_id, monto)`.
2. **Flujo de Confirmación Humana (Human-in-the-Loop):**
   - Para operaciones que alteren estados críticos o eliminen datos (ej. `eliminar_movimiento`, `abandonar_meta_ahorro`), el agente no ejecuta directamente la mutación en la base de datos en su primer turno.
   - Retorna un payload estructurado:
     ```json
     {
       "tipo_accion": "REQUERIR_CONFIRMACION",
       "accion": "eliminar_movimiento",
       "datos": {"id": 142, "descripcion": "Cena", "monto": 55000},
       "mensaje_usuario": "He preparado la eliminación del gasto de $55.000 en Cena. ¿Deseas confirmar la acción?"
     }
     ```
   - El frontend renderiza botones dinámicos de **[Confirmar]** y **[Cancelar]**, devolviendo un callback seguro al backend.

---

### Fase 3: Tool Calling Multi-Paso (Multi-turn Tool Reasoning)

**Objetivo:** Permitir que el LLM consulte datos previos antes de decidir la siguiente acción en una sola interacción del usuario.

1. **Refactorización de `groq_client.py:preguntar_a_groq`:**
   - Sustituir la lógica fija de dos pasos por un bucle controlado con un máximo de 5 iteraciones (`max_iteraciones=5`).
   - Ciclo:
     1. Enviar historial + herramientas a Groq.
     2. Si el modelo responde con llamadas a herramientas (`tool_calls`), ejecutarlas.
     3. Anexar las respuestas `tool` y reinyectar el array completo de herramientas para que el modelo pueda solicitar una herramienta adicional si lo necesita.
     4. Si el modelo responde con texto final (`finish_reason != "tool_calls"`), terminar y devolver la respuesta.

---

### Fase 4: Integración de Exportación e Importación de Datos

**Objetivo:** Generar archivos descargables desde el chat y asistir al usuario en la carga estructurada.

1. **Herramienta de Exportación Directa:**
   - `generar_reporte_descarga(modulo, formato, mes=None, anio=None, tipo=None)`:
     - Reutiliza directamente las funciones de `movimientos/views_exportar.py`, `ahorros/views_exportar.py` y `dashboard/export_services.py`.
     - Genera el reporte y devuelve una URL efímera firmada o ruta interna de descarga que el frontend muestra como botón estilizado de descarga: *"He generado tu reporte en Excel. [Descargar Reporte (.xlsx)]"*.
2. **Skill / Asistente de Importación de Datos:**
   - Reconocimiento de datos pegados en texto o CSV subido en el chat, mapeo contra las categorías existentes del usuario y creación por lotes previa vista previa.

---

### Fase 5: Optimización de Prompts y Manejo del Idioma Español

1. **Inyección de Ejemplos Few-Shot en `prompt_builder.py`:**
   - Incorporar 3 a 5 conversaciones de ejemplo en español neutro / latinoamericano que enseñen al modelo:
     - Cómo interpretar modismos o descripciones coloquiales de gastos ("me gasté 20 lucas en empanadas" -> Tipo: EGRESO, Monto: 20000, Categoría inferida: Alimentación/Restaurantes).
     - Cómo rechazar responder preguntas que requieran cálculos aritméticos sin invocar su herramienta de cálculo.
2. **Formato Estricto de Moneda y Cifras:**
   - Instrucción negativa explícita: *"Nunca inventes totales ni realices aproximaciones mentales de saldo. Cita exclusivamente los montos devueltos por tus herramientas en formato de pesos colombianos ($X.XXX.XXX)"*.

---

## 4. Metodología para Creación de Skills desde el Chat

De acuerdo a tus requerimientos, cuando vayamos a crear una nueva **Skill** para el agente, el flujo de trabajo en el chat seguirá un estándar estructurado mediante un formulario de especificación profunda antes de escribir una sola línea de código:

### Protocolo de Creación de Skill (Formulario Maestro)

Cuando se solicite diseñar una nueva Skill, se presentará el siguiente formulario completo para definir alcance y reglas:

```markdown
### FORMULARIO DE DEFINICIÓN DE SKILL: [Nombre de la Skill]

#### A. Visión Macro (Estrategia y Propósito)
1. **Propósito Principal:** ¿Qué problema concreto del usuario resuelve esta skill?
2. **Rol del Agente:** ¿Cómo debe actuar el agente al ejecutarla? (Ej. consejero conservador, auditor implacable, tutor pedagógico, ejecutor silencioso).
3. **Disparadores (Triggers):** ¿Qué palabras clave, intenciones del usuario o eventos del sistema deben activar esta habilidad?
4. **Módulos Afectados:** ¿Qué áreas de GastuApp intervienen? (Movimientos, Ahorros, Presupuestos, Programaciones, Notificaciones, Historial).

#### B. Especificación Micro (Comportamiento, Cuestionario y Flujo de Datos)
1. **Entradas Requeridas (Inputs):**
   - Parámetros obligatorios (ej. monto, categoría, período).
   - Parámetros opcionales con valores por defecto.
   - ¿Qué debe hacer si el usuario no proporciona un dato obligatorio? (¿Preguntar interactivamente o inferirlo?).
2. **Reglas de Negocio y Restricciones:**
   - ¿Qué validaciones deben pasar antes de proceder? (Ej. no exceder el disponible, no crear categorías duplicadas).
   - ¿Requiere confirmación previa del usuario (Human-in-the-Loop)? (Sí/No y bajo qué umbrales).
3. **Casos de Éxito (Muestras Favorables / Fáciles):**
   - Ejemplo 1: Entrada simple y respuesta esperada.
   - Ejemplo 2: Acción con parámetros completos.
4. **Casos de Borde y Error (Muestras Desfavorables / Complicadas):**
   - Ejemplo 1: Fondos insuficientes o fechas incoherentes en el pasado.
   - Ejemplo 2: Ambigüedad en la categoría solicitada por el usuario.
   - Ejemplo 3: Usuario que cambia de opinión a mitad del flujo.
5. **Salida y Presentación Visual:**
   - Formato de respuesta: ¿Texto enriquecido, tarjetas de acción rápida, botones de confirmación, enlace de descarga de archivo?
   - Registro en Auditoría: ¿Qué se guarda en `AccionHistorial`?
```

---

## 5. Criterios de Aceptación y Pruebas del Agente (DoD)

1. **Aritmética y Precisión:**
   - 100% de coherencia entre los datos de base de datos y los valores citados por el agente (cero discrepancias de centavos o cálculo mental).
2. **Cobertura de Pruebas Automatizadas:**
   - Tests unitarios con `pytest` para cada nueva herramienta agregada a `herramientas.py`.
   - Pruebas del orquestador multi-paso simulando escenarios de 2 y 3 llamadas de herramientas encadenadas.
3. **Seguridad y Control de Acceso:**
   - Ninguna herramienta del agente puede consultar o modificar registros que no pertenezcan al `request.user` autenticado.
   - Acciones destructivas bloqueadas exitosamente hasta recibir el token o confirmación explícita del usuario.


# Agente Financiero (Gastu) - Brief de rediseño de UI/UX

Documento para el agente encargado del diseño y el frontend de GastuApp.
Acompaña a la maqueta `gastu-agente-maqueta.html` (cuatro estados, estática).

---

## 0. Cómo usar este documento

1. Abre `gastu-agente-maqueta.html` en el navegador y revisa los cuatro estados.
2. Lee las secciones 1 a 10 (decisiones, tokens, componentes, contrato de bloques).
3. Responde las preguntas de la sección 11 con este formato por pregunta:

```
P<n>
Decisión: (acepto / rechazo / propongo alternativa)
Detalle: (qué harás o qué cambiarías)
Razón: (una o dos líneas)
```

Quien diseñó la maqueta no tuvo acceso al repositorio. Todo lo que este documento dice sobre el código sale de `Agent.md` y de las guías del proyecto, no de haber leído los archivos reales. Donde algo se asume, está marcado como **Supuesto**.

Los datos numéricos de la maqueta (por ejemplo $19.900 diarios, 5 días restantes, $14.100 por día, 14 egresos) son de ejemplo, inventados para que cuadren entre sí. No salen de datos reales.

---

## 1. Alcance y restricciones

### Alcance
- Solo se rediseña el contenido de la zona principal de la página del agente (el chat).
- El sidebar y el navbar no se tocan. En la maqueta aparecen en azul oscuro únicamente para evaluar el contraste con el chat. Colores aproximados, tomados a ojo de una captura: navbar `#1b273d`, sidebar `#172136`, ítem activo `#223656`.

### Restricciones del proyecto (de Agent.md y guías internas)
- Django 5.2 con templates, Tailwind CSS 4 (app `theme`), Lucide para iconos, ApexCharts disponible.
- Tipografía: Plus Jakarta Sans (títulos y cifras) y DM Sans (cuerpo).
- Sin emojis en ningún archivo, texto visible ni comentario.
- La plantilla extiende `base_app.html`. No crear layouts locales.
- HTML, CSS y JS en archivos separados. Nunca `{{ }}` ni `{% %}` dentro de `<style>` ni de `style=""`. Los datos para JS van por atributos `data-` o por `<script type="application/json">`.
- El agente solo consulta datos, nunca los modifica. Ninguna acción de la UI debe sugerir lo contrario.
- Archivos actuales del agente (según Agent.md): `agente_financiero.html`, `agente_financiero.js`, `agente_financiero.css`.

---

## 2. Diagnóstico de la UI anterior

| Problema | Efecto |
|---|---|
| Burbuja de la IA en azul marino, igual al sidebar | Se sentía pegada al shell y pesada sobre el lienzo blanco |
| Burbuja del usuario en café | Color sin relación con la paleta del proyecto |
| Alerta ámbar sobre fondo oscuro | Contraste turbio |
| Tabla de 5 filas + badge "88 %" + párrafo de alerta | El mismo dato tres veces |
| Burbuja de la IA de más de 1000 px de ancho | Líneas de más de 100 caracteres, difíciles de leer |
| Botón flotante de campana encima del botón de enviar | Colisión visual |
| Texto de privacidad diminuto y casi sin contraste | No se leía |
| Sin acciones por mensaje | No había copiar ni regenerar |

---

## 3. Decisiones de diseño

Cada decisión lleva su razón, para poder discutirla o rechazarla una por una.

**D1. Sin card contenedora.** El chat ocupa toda la zona principal sobre un único fondo (`#eef2f7`). Una card blanca sobre fondo gris producía "card dentro de card" y reducía el ancho útil. El encabezado es una barra plana con una línea fina inferior.

**D2. La IA escribe directo sobre el lienzo, sin burbuja.** Solo el usuario tiene burbuja, como en los chats de IA actuales. Libera ancho. La columna de lectura se limita a 760 px (720 de contenido más 20 de padding por lado) para mantener líneas de 70 a 90 caracteres.

**D3. La respuesta empieza por la conclusión.** Un titular de una frase (23 px, peso 800) con la respuesta directa, antes de cualquier dato. Después el visual, después el consejo.

**D4. Un visual por respuesta, no tres.** Se eliminó el patrón tabla + badge + alerta. Cada tipo de dato tiene un componente que lo comunica mejor que una tabla: medidor para consumo de presupuesto, libreta para listas de movimientos, cifras grandes para totales.

**D5. El color significa estado, no decora.**
- Verde: dentro del límite, acción principal (enviar), dinero disponible.
- Ámbar: zona de alerta (consumo igual o mayor al umbral).
- Rojo escarlata: egresos y montos negativos (coherente con Agent.md: los egresos usan escarlata, no naranja).
- Los colores por sección (ingresos, egresos, presupuestos, ahorros) solo aparecen en el estado vacío.

**D6. La personalidad sale de componentes propios, no de decoración.**
- Medidor de 24 segmentos, como un indicador de combustible.
- Libreta de cuentas: puntos guía entre concepto y monto, total con doble subrayado contable.
- Anillo del avatar como "ánimo" del agente (sección 6.2).
- Saludo según la hora ("Buenas noches, Demo") en el estado vacío.
- Voz del agente: la recomendación empieza con "Mi consejo." en un café cálido (`#92400e`).

**D7. Los atajos "Para seguir" son filas con línea divisoria**, no botones tipo píldora ni cards. El icono es una burbuja de chat y no un "+", porque el agente no agrega nada.

**D8. La zona de escritura es un campo flotante**, no una barra ni una card.
- Fondo casi blanco (`#f8fafc`), borde de 1,5 px, sombra muy suave, esquinas de 26 px.
- Separado del borde inferior de la pantalla: 28 px en escritorio, 18 px en móvil, más `env(safe-area-inset-bottom)`.
- Un degradado corto del color del lienzo a transparente sobre el área de mensajes evita un corte duro al hacer scroll.
- Sin texto de ayuda debajo (ver D9).
- Antes de esta versión se probó un campo hundido sin borde y se descartó: quedaba sin presencia. También se descartó la barra blanca con campo en píldora y sombra, porque se leía como "otra card".

**D9. El aviso de privacidad se movió al encabezado**: subtítulo "Consulta tus datos reales; nunca los modifica". Antes iba en una línea debajo del campo, que se rompía en pantallas pequeñas o con zoom. En el encabezado se recorta con puntos suspensivos si no cabe.

**D10. Acciones por mensaje discretas**: copiar y regenerar como iconos de 32 px, sin borde, junto a la línea de procedencia.

**D11. Línea de procedencia** en gris y pequeña ("Basado en 14 egresos de noviembre"). Refuerza la promesa de "datos reales" y da confianza en una app de finanzas.

**D12. Consejo con datos propios, no genérico.** "Revisa tus próximos gastos" lo diría cualquier IA. El consejo debe citar el ritmo diario del usuario y un tope diario para cerrar el mes. Las cifras las calcula el backend (sección 7).

**D13. Sin información duplicada.** El límite aparece una sola vez (en la bandera del medidor). El segundo bloque de cifras muestra el máximo diario, que es un dato nuevo, en lugar de repetir el límite.

**D14. Dos atajos de seguimiento como máximo.** Tres filas con líneas ocupaban demasiado alto en pantallas bajas.

---

## 4. Tokens

### 4.1 Colores

| Token propuesto | Valor | Uso |
|---|---|---|
| canvas | `#eef2f7` | Fondo del chat |
| ink | `#0f172a` | Texto principal |
| ink-muted | `#475569` | Texto secundario, etiquetas, hora, procedencia |
| line | `#d0d9e4` | Línea bajo el encabezado |
| line-row | `#d5dee9` | Separadores de filas |
| line-strong | `#cbd5e1` | Divisor de cifras, borde superior de atajos |
| field-bg | `#f8fafc` | Fondo del campo de escritura |
| field-border | `#8497ae` | Borde del campo |
| action | `#047857` | Burbuja del usuario, botón enviar, iconos de atajos, texto "Te quedan" |
| action-bright | `#10b981` | Segmentos del medidor dentro del límite |
| warn | `#d97706` | Segmentos en zona de alerta, anillo de ánimo "alerta" |
| warn-ink | `#92400e` | Texto "Mi consejo.", etiquetas ámbar |
| flag-bg | `#78350f` | Bandera del medidor |
| danger | `#be123c` | Montos de egreso |
| segment-empty | `#d5dee9` | Segmentos vacíos |
| ring-ok | `#059669` | Anillo del avatar en estado normal |
| ring-think | `#94a3b8` | Anillo del avatar mientras "revisa" |
| brand-fill / brand-ring / brand-ink | `#f5ebe0` / `#8b5e34` / `#6b4226` | Avatar provisional (tonos del búho) |

Colores por sección en el estado vacío (icono / fondo): ingresos `#047857` / `#d1fae5`; egresos `#be123c` / `#ffe4e6`; presupuestos `#6d28d9` / `#ede9fe`; ahorros `#b45309` / `#fef3c7`.

### 4.2 Diferencias respecto al sistema de diseño actual

Estas decisiones se apartan de las variables documentadas en Agent.md. Hay que decidir si se acepta cada una o se vuelve al valor original (preguntas P1 a P3).

| Documentado | Maqueta | Motivo |
|---|---|---|
| Fondo del body `#e8edf2` | Lienzo `#eef2f7` | Un poco más claro para que el verde y el ámbar resalten. Casi igual al body, así que podría unificarse |
| `--slate-500: #64748b` para texto secundario | `#475569` | `#64748b` sobre el lienzo da 4,23:1 (no pasa AA en texto pequeño). `#475569` da 6,74:1 |
| `--emerald-dark: #059669` para botones | `#047857` | Texto blanco sobre `#059669` da 3,77:1 (falla AA en texto normal). Sobre `#047857` da 5,48:1 |

### 4.3 Contrastes calculados

| Par | Ratio |
|---|---|
| ink sobre lienzo | 15,88:1 |
| ink-muted `#475569` sobre lienzo | 6,74:1 |
| warn-ink `#92400e` sobre lienzo | 6,31:1 |
| danger `#be123c` sobre lienzo | 5,59:1 |
| action `#047857` sobre lienzo | 4,88:1 |
| Blanco sobre `#78350f` (bandera) | 9,07:1 |
| Blanco sobre `#047857` (burbuja y botón) | 5,48:1 |
| **Borde del campo `#8497ae` contra lienzo** | **2,66:1** |

Punto abierto: el borde del campo queda por debajo de 3:1, que es lo recomendado para delimitar componentes de interfaz. Ver P6.

### 4.4 Tipografía

| Rol | Familia | Tamaño / peso |
|---|---|---|
| Titular de respuesta | Plus Jakarta Sans | 23 px (20 px en móvil), 800, interlineado 1,3 |
| Saludo del estado vacío | Plus Jakarta Sans | `clamp(28px, 4.4vw, 40px)`, 800, interlineado 1,1 |
| Cifras grandes | Plus Jakarta Sans | 26 px (22 px en móvil), 800 |
| Títulos de sección y nombres | Plus Jakarta Sans | 14,5 a 17 px, 700 |
| Cuerpo | DM Sans | 15,5 px, interlineado 1,6 |
| Etiquetas y procedencia | DM Sans | 12 a 13 px |

### 4.5 Espaciado y forma
- Columna: `max-width: 760px`, padding lateral 20 px (16 px en móvil).
- Separación entre bloques de una respuesta: 14 px. Entre mensajes: 24 a 26 px.
- Burbuja del usuario: radios 20 / 20 / 6 / 20, ancho máximo 85 %.
- Campo de escritura: alto mínimo 48 px, radio 26 px.
- Segmentos del medidor: 24 unidades, 30 px de alto, 4 px de separación, radio 5 px.

---

## 5. Estructura de la página

```
+--------------------------------------------------------------+
| navbar (no se toca)                                          |
+---------+----------------------------------------------------+
| sidebar | encabezado: avatar, "Gastu", subtítulo, Limpiar    |
| (no se  |----------------------------------------------------|
| toca)   | zona de mensajes (scroll vertical, flex: 1)        |
|         |    columna centrada, máx. 760 px                   |
|         |                                                    |
|         |  [degradado de transición]                         |
|         |    campo de escritura flotante (flex: none)        |
+---------+----------------------------------------------------+
```

### Cómo evitar que el campo de escritura crezca y tape el chat

Es un problema que ya se vio en la app real con zoom alto, pantallas pequeñas y móvil. Casi siempre se debe a alturas en `vh` o en porcentaje en el pie. Esquema recomendado:

```css
.chat-root     { height: 100dvh; display: flex; flex-direction: column; min-height: 0; }
.chat-scroll   { flex: 1; min-height: 0; overflow-y: auto; }
.chat-composer { flex: none; padding-bottom: max(28px, env(safe-area-inset-bottom)); }
.chat-composer textarea { max-height: 132px; overflow-y: auto; resize: none; }
```

Notas:
- La raíz del chat necesita una altura definida (la del área principal, no `vh` sueltos en los hijos). **Supuesto:** hay que revisar cómo `base_app.html` define la altura del área de contenido (scroll de página o contenedor con scroll propio).
- `min-height: 0` en la zona de scroll es imprescindible dentro de un flex en columna.
- El `textarea` crece hasta unas 5 líneas y luego hace scroll interno.
- Por debajo de 760 px: el sidebar se oculta (la app ya lo hace) y aparece un botón de menú en el navbar. En la maqueta móvil el padding lateral baja a 16 px y las cifras se compactan.

---

## 6. Catálogo de componentes

### 6.1 Burbuja del usuario
- Fondo `action`, texto blanco, alineada a la derecha, ancho máximo 85 %.
- Hora debajo, a la derecha, en `ink-muted`, 12 px.
- Datos: `contenido` y `creado_en` del mensaje.

### 6.2 Avatar con anillo de ánimo
- Círculo de 34 px (40 px en el encabezado, 76 px en el estado vacío) con el rostro del búho. Anillo de 3 px que cambia según el ánimo de la respuesta.

| Ánimo | Anillo | Cuándo |
|---|---|---|
| `normal` | `#059669` | Respuesta informativa sin alerta |
| `alerta` | `#d97706` | Presupuesto en zona de alerta, meta por vencer, balance negativo |
| `pensando` | `#94a3b8` | Mientras el agente consulta datos |
| `critico` (propuesto, no está en la maqueta) | `#be123c` | Presupuesto excedido o error |

- El ánimo lo decide el backend según reglas de negocio, no el modelo de lenguaje.
- La maqueta usa una "G" provisional. Debe reemplazarse por `gastu_logo_rostro.png`.

### 6.3 Titular
- Una frase, 23 px. Siempre es la conclusión ("Vas al 88% de tu presupuesto en Alimentación.").
- Recomendado: generado por plantilla en el backend según el estado (sección 7.4), no por el modelo.

### 6.4 Medidor (bloque `medidor`)
- 24 segmentos que representan de 0 a 100 % del límite.
- Segmentos llenos: `round(consumo_pct / 100 * 24)`, con tope en 24.
  - Hasta el umbral de alerta: verde `action-bright`.
  - Por encima del umbral: ámbar `warn`.
  - Con consumo de 100 % o más: la zona sobre el umbral pasa a `danger` (**propuesto**, no está en la maqueta).
- Marca vertical en la posición del umbral (80 % por defecto) con la etiqueta "Alerta al 80%" debajo.
- Bandera sobre el segmento final: `$gastado de $límite`, fondo `flag-bg`, texto blanco, con triángulo apuntando al segmento.
- Accesibilidad: el conjunto es `role="img"` con `aria-label` del tipo "88 por ciento consumido, $517.000 de $587.500". Los segmentos son decorativos (`aria-hidden`).
- Variantes pendientes de diseñar: bajo el umbral (todo verde), excedido (más de 100 %), sin presupuesto definido (no hay medidor).

### 6.5 Cifras (bloque `cifras`)
- Dos columnas separadas por una línea vertical fina, sin cajas.
- Cada una: etiqueta de 12,5 px y valor de 26 px.
- Tono `ok` pinta el valor en `action`; `neutro` lo deja en `ink`.
- En la maqueta: "Te quedan $70.500" y "Máximo por día, 5 días restantes $14.100".

### 6.6 Consejo (bloque `consejo`)
- Párrafo de 15,5 px que empieza con "Mi consejo." en negrita y `warn-ink`.
- Longitud objetivo: 2 líneas en escritorio (máximo 220 caracteres).
- Es el único texto de la respuesta que escribe el modelo (sección 7).

### 6.7 Libreta (bloque `libreta`)
- Encabezado con regla gruesa de 2 px arriba, título a la izquierda y "N de M" a la derecha.
- Filas de unos 44 px: fecha (13 px, `ink-muted`), concepto, línea de puntos que se estira, monto en `danger` (egresos) con signo menos.
- Línea de resumen "y K movimientos más".
- Pie con total: regla de 1 px arriba y monto con doble subrayado (`border-bottom: 4px double`).
- Para ingresos: mismo componente con monto en `action` y signo más (**propuesto**).
- En pantallas estrechas el concepto debe truncarse con puntos suspensivos antes de romper la fila (por definir, P12).

### 6.8 Procedencia
- Texto de 12,5 px en `ink-muted`, a la derecha de las acciones. Cuenta de registros que respaldan la respuesta.

### 6.9 Acciones por mensaje
- Copiar y regenerar. Botones reales con `aria-label`, objetivo táctil de 32 px (a revisar: las pautas de accesibilidad suelen pedir 44 px en móvil).
- Se perdió el botón "Copiar tabla" que existía antes. Ver P13.

### 6.10 Atajos "Para seguir" (bloque `siguientes`)
- Lista de máximo dos filas con línea divisoria arriba y abajo, texto a la izquierda e icono de chat a la derecha.
- Al pulsar, se envía la `pregunta` asociada como si el usuario la hubiera escrito.

### 6.11 Estado "revisando"
- Avatar con anillo gris y texto "Revisando tus egresos de octubre" con tres puntos.
- La maqueta no los anima. Propuesta: una sola animación suave de los puntos, respetando `prefers-reduced-motion`. Contenedor con `role="status"`.
- El texto debe derivarse de la herramienta que ejecuta el backend (mapa fijo herramienta a frase), no del modelo.

### 6.12 Estado vacío
- Avatar grande con anillo verde, saludo según hora y nombre del usuario, una línea de apoyo y cuatro sugerencias como filas (no cards) con icono circular del color de su sección.
- Las cuatro sugerencias salen de las "4 sugerencias rápidas" que Agent.md dice que existen hoy:
  - Cuánto he ingresado este mes.
  - En qué categoría gasto más.
  - Cómo van mis presupuestos.
  - Cómo van mis metas de ahorro.
- Saludo: "Buenos días / Buenas tardes / Buenas noches" según la hora local del usuario, calculado en el cliente o en la vista.

### 6.13 Encabezado del chat
- Avatar de 40 px con punto de estado, nombre "Gastu", subtítulo de privacidad y botón "Limpiar chat" como texto con icono, sin borde.
- En móvil el texto del botón se oculta y queda solo el icono.
- "Limpiar" hoy no pide confirmación. Recomendado: confirmar con `GastuAlerts` (SweetAlert2), que ya existe en el proyecto.

### 6.14 Campo de escritura
- `textarea` de una línea que crece. Enter envía, Shift+Enter inserta salto de línea.
- Botón de enviar circular de 40 px, `action`. Aro verde al enfocar.
- Estado deshabilitado mientras el agente responde (por definir si se permite escribir y encolar).

---

## 7. Contrato de respuesta estructurada (el punto más importante)

### 7.1 Por qué
La IA del proyecto se sirve con Groq Cloud (`llama-3.3-70b-versatile` según Agent.md). Son modelos bastante más débiles que los de gama alta: se equivocan en aritmética, no siempre siguen el formato pedido y varían el tono. Hoy la respuesta es texto con markdown que el frontend interpreta, y de ahí sale la tabla recargada y los datos repetidos. Si el diseño depende de cómo redacte el modelo, se rompe cada vez que el modelo cambia.

**Principio:** el backend calcula los datos y arma los bloques visuales. El modelo solo redacta frases cortas dentro de huecos definidos.

### 7.2 Quién produce qué

| Elemento | Lo produce | Por qué |
|---|---|---|
| Cifras, porcentajes, días, ritmo diario, máximo diario | Backend (servicios Python) | La aritmética del modelo no es confiable en una app de finanzas |
| Estado (`ok`, `alerta`, `excedido`) y ánimo del avatar | Backend | Es regla de negocio |
| Titular | Backend, por plantilla | Debe ser exacto y estable |
| Bloques `medidor`, `cifras`, `libreta`, `procedencia` | Backend | Son datos |
| Atajos `siguientes` | Backend, por mapa de intención | Deterministas y siempre relevantes |
| Texto de estado "revisando" | Backend, por mapa herramienta a frase | Sin dependencia del modelo |
| `consejo` | Modelo | Es lo único que necesita lenguaje natural |
| `texto` (respuesta libre a preguntas abiertas) | Modelo | Para consultas que no encajan en una plantilla |

### 7.3 Esquema JSON propuesto

Respuesta del endpoint `POST /api/agente/chat/` (hoy devuelve texto; este sería el cambio):

```json
{
  "version": 1,
  "intencion": "estado_presupuesto",
  "animo": "alerta",
  "bloques": [
    {"tipo": "titular", "texto": "Vas al 88% de tu presupuesto en Alimentación."},
    {"tipo": "medidor",
     "categoria": "Alimentación",
     "periodo": "2026-11",
     "limite": 587500,
     "gastado": 517000,
     "consumo_pct": 88,
     "umbral_pct": 80,
     "estado": "alerta"},
    {"tipo": "cifras",
     "items": [
       {"etiqueta": "Te quedan", "valor": 70500, "tono": "ok"},
       {"etiqueta": "Máximo por día, 5 días restantes", "valor": 14100, "tono": "neutro"}
     ]},
    {"tipo": "consejo",
     "texto": "Llevas $19.900 diarios; a ese ritmo el límite te alcanza en unos 3 días. Para cerrar noviembre dentro del presupuesto, intenta no pasar de $14.100 al día.",
     "origen": "modelo"},
    {"tipo": "procedencia", "texto": "Basado en 14 egresos de noviembre", "cantidad": 14},
    {"tipo": "siguientes",
     "items": [
       {"etiqueta": "Ver movimientos de Alimentación",
        "pregunta": "Muéstrame los movimientos de Alimentación de noviembre"},
       {"etiqueta": "Comparar con octubre",
        "pregunta": "¿Cómo va Alimentación en octubre comparado con noviembre?"}
     ]}
  ]
}
```

Reglas del contrato:
- Los montos viajan como enteros (pesos), nunca como texto con formato. El frontend los formatea como `$517.000` (locale `es-CO`).
- `origen` en `consejo` y `texto` vale `"modelo"` o `"plantilla"`. Sirve para depurar y medir cuánto falla el modelo.
- El frontend ignora bloques con `tipo` desconocido en lugar de fallar (compatibilidad hacia adelante).
- `version` permite cambiar el esquema sin romper el historial.

Bloque `libreta`:

```json
{"tipo": "libreta",
 "titulo": "Egresos de noviembre",
 "filas": [
   {"fecha": "2026-11-07", "concepto": "Supermercado Éxito", "monto": 142300, "movimiento": "EGRESO"}
 ],
 "mostradas": 4,
 "total_filas": 14,
 "total": {"etiqueta": "Total Alimentación", "valor": 517000}}
```

Bloque `texto` (respuesta libre): `{"tipo": "texto", "texto": "...", "origen": "modelo"}`. Se renderiza con un subconjunto mínimo de markdown: negrita, cursiva y listas. Sin encabezados, tablas, imágenes ni HTML.

### 7.4 Cálculos que debe hacer el backend

Para `estado_presupuesto` de una categoría en un mes:

```
consumo_pct        = gastado / limite * 100
disponible         = max(limite - gastado, 0)
dias_transcurridos = dia_actual                      (mínimo 1)
dias_restantes     = dias_del_mes - dia_actual + 1   (incluye hoy; convención por acordar, P9)
gasto_diario       = gastado / dias_transcurridos
maximo_diario      = disponible / dias_restantes
dias_hasta_limite  = disponible / gasto_diario       (si gasto_diario es 0: no aplica)
estado             = ok        si consumo_pct < umbral
                     alerta    si umbral <= consumo_pct < 100
                     excedido  si consumo_pct >= 100
```

Casos borde: límite 0 o no definido, gasto 0, último día del mes, mes pasado (sin "días restantes"), presupuesto excedido (`disponible` en 0 y mostrar cuánto se pasó).

Titular por plantilla según estado (ejemplos, a revisar):
- `ok`: "Vas bien en {categoría}: llevas el {pct}% de tu presupuesto."
- `alerta`: "Vas al {pct}% de tu presupuesto en {categoría}."
- `excedido`: "Te pasaste del presupuesto de {categoría} por ${exceso}."

### 7.5 Flujo propuesto con tool calling

Agent.md lista tres herramientas: `obtener_movimientos`, `obtener_resumen_periodo`, `obtener_gastos_por_categoria`. Propuesta:

1. El modelo recibe la pregunta y elige una herramienta (esto lo hace razonablemente bien).
2. Cada herramienta devuelve datos ya calculados **y** los bloques visuales listos. Al modelo se le devuelve un resumen compacto de cifras, no una lista cruda para que "la cuente".
3. Se le pide al modelo solo el `consejo` (o el `texto` si la intención es abierta), con las cifras ya calculadas en el prompt y la instrucción de no inventar números.
4. El backend valida el texto (7.6). Si falla, usa la plantilla.
5. El backend ensambla `bloques` y responde.

Herramienta nueva sugerida: `estado_presupuesto_categoria(categoria, mes, anio)`, que devuelva el conjunto de bloques de la sección 7.3. **Supuesto:** hoy no existe y la pregunta de presupuesto se resuelve con las herramientas actuales y texto libre.

### 7.6 Validación de la salida del modelo

Reglas mínimas (pseudocódigo Python, a adaptar):

```python
def validar_consejo(texto, cifras_permitidas):
    """Valida el consejo generado por el modelo antes de mostrarlo."""
    if not texto or len(texto) > 220:
        return False
    numeros = extraer_numeros(texto)
    return all(n in cifras_permitidas for n in numeros)
```

- Si el texto contiene un número que no está en las cifras permitidas, se descarta y se usa la plantilla. `extraer_numeros` debe normalizar formatos como `$19.900`, `19900` o "19,9 mil".
- Si el formato no es válido (JSON roto, markdown no permitido), se descarta.
- Opcional y más costoso: descartar si menciona categorías, fechas o nombres que no están en el contexto.
- Se registra el motivo de cada descarte para medir la calidad del modelo.

Consejo de plantilla (respaldo) con las mismas cifras:
"Llevas {gasto_diario} diarios; a ese ritmo el límite te alcanza en unos {dias_hasta_limite} días. Para cerrar {mes} dentro del presupuesto, intenta no pasar de {maximo_diario} al día."

### 7.7 Otras medidas para un modelo débil
- Temperatura baja (Agent.md indica 0,4; probar 0,2 para el `consejo`).
- Salida acotada: una o dos frases, máximo 220 caracteres, sin listas ni markdown.
- Ejemplos en el prompt (few-shot) del tono deseado, con tres casos: ok, alerta, excedido.
- Modo JSON o salida estructurada de Groq para el `consejo`, si el modelo lo soporta (verificar en la documentación vigente de Groq).
- Streaming: solo tiene sentido para el bloque `texto`. Los bloques de datos llegan completos y de golpe.
- Caché de respuestas por (usuario, intención, fecha) para no gastar cuota del plan gratuito en preguntas repetidas.
- Manejo de errores y límites de cuota: estado de error visible (pendiente de diseñar, sección 9).

### 7.8 Historial

Hoy `MensajeChat` guarda `contenido` como texto. Para reproducir bloques al recargar la página hace falta guardar la respuesta estructurada. **Propuesta:** agregar un campo `bloques` (`JSONField`, nulo) al modelo, conservando `contenido` como texto plano de respaldo. Requiere migración. `GET /api/agente/chat/` devolvería `bloques` cuando existan. Los mensajes antiguos (solo texto) se renderizan como un bloque `texto`.

---

## 8. Implementación en el frontend

- La respuesta llega como JSON por `fetch` y **el JS pinta los bloques**. No hay `{{ }}` de Django en el estilo de ningún componente.
- Cada tipo de bloque tiene una función de render (`renderMedidor`, `renderLibreta`, etc.) y un único bloque CSS con prefijo propio (por ejemplo `.chat-medidor`, `.chat-libreta`) en `agente_financiero.css`.
- Los segmentos del medidor se generan con un bucle en JS a partir de `consumo_pct` y `umbral_pct`, con clases `--ok` y `--warn`. Solo la posición de la marca del umbral y de la bandera se asignan desde JS con `style.setProperty` sobre una variable CSS.
- Iconos: Lucide (`data-lucide`) y `lucide.createIcons()` tras cada render de bloques.
- Alertas y confirmaciones: `window.GastuAlerts`.
- El texto del modelo se inserta con `textContent` (o con un convertidor de markdown mínimo y escapado), nunca con `innerHTML` sin sanear.
- Todo bloque tiene respaldo accesible en texto (`aria-label` en el medidor; tabla semántica o lista para la libreta, ver P12).
- La zona de mensajes lleva `aria-live="polite"` para anunciar respuestas nuevas.

---

## 9. Estados que faltan por diseñar

| Estado | Nota |
|---|---|
| Error del agente (red, cuota de Groq agotada, formato inválido sin respaldo) | Mensaje dentro del flujo con reintento. Ánimo `critico` |
| Sin datos o sin presupuesto definido para la categoría | Sin medidor; frase y enlace a la página de presupuestos (navegación, no modificación) |
| Presupuesto excedido | Medidor con zona roja y cifra "te pasaste por" |
| Presupuesto dentro del límite | Medidor todo verde |
| Respuesta larga de texto libre | Ancho de lectura, listas, negrita |
| Comparación entre dos periodos | Probable bloque `comparacion` nuevo |
| Ingresos y ahorros | Bloques equivalentes: libreta de ingresos, meta de ahorro (medidor con otro color) |
| Separadores de fecha en historial largo | "Hoy", "Ayer", fecha |
| Cargar historial anterior | Paginación o carga bajo demanda |
| Mensaje del usuario muy largo | Límite de alto con "ver más" |
| Campo de escritura deshabilitado o enviando | Aspecto y comportamiento |
| Reducción de movimiento | Respetar `prefers-reduced-motion` en cualquier animación |

---

## 10. Lo que no se hizo a propósito

- No se anima el medidor al aparecer. Propuesta opcional: un único llenado de izquierda a derecha al llegar la respuesta, no al cargar el historial.
- No hay modo oscuro. El chat vive junto a un shell oscuro, pero el área de lectura es clara. Si el proyecto planea tema oscuro, habría que definir tokens.
- Los atajos no los genera el modelo (son del backend), para evitar ofrecer preguntas que el agente no sabe responder.
- Ninguna acción modifica datos (crear, editar, borrar), por coherencia con "Gastu solo consulta tus datos".

---

## 11. Preguntas para el agente de diseño

Responde con el formato de la sección 0.

### A. Sistema de diseño y tokens
- **P1.** El lienzo `#eef2f7` difiere del fondo del body `#e8edf2`. ¿Se unifica a `#e8edf2` (reajustando contrastes) o se crea un token nuevo para el chat?
- **P2.** `--slate-500` (`#64748b`) no pasa AA como texto pequeño sobre el lienzo. ¿Propones cambiar el token global a `#475569` o crear uno específico (`--ink-muted`) solo para el agente?
- **P3.** Los botones principales usan `--emerald-dark` (`#059669`), que da 3,77:1 con texto blanco. ¿Se acepta `#047857` como valor de acción en todo el proyecto o solo en el chat?
- **P4.** ¿Existe una forma establecida de reutilizar los colores por sección (variables tipo `--section-*`)? La maqueta los repite a mano.
- **P5.** El avatar debe usar `gastu_logo_rostro.png`. ¿Hay versión recortada en círculo o en varios tamaños (34, 40 y 76 px)? ¿Hace falta una con fondo transparente o con fondo `#f5ebe0`?
- **P6.** El borde del campo de escritura da 2,66:1 sobre el lienzo (lo recomendado es 3:1). ¿Oscurecer el borde, aumentar el relleno o aceptar la diferencia porque el campo tiene fondo y sombra propios?

### B. Layout e implementación
- **P7.** ¿Cómo define hoy `base_app.html` la altura del área de contenido (scroll de página o contenedor con scroll propio)? ¿El esquema `100dvh` + flex de la sección 5 es compatible o hay que adaptarlo?
- **P8.** ¿Prefieres estos componentes con clases propias en `agente_financiero.css` (como se propone) o con utilidades de Tailwind 4? ¿Hay una convención de nombres (BEM, prefijos) que deba seguir?
- **P9.** Convención de "días restantes": ¿incluye el día de hoy o no? Debe acordarse con el backend para que `maximo_diario` sea coherente con lo que ve el usuario.
- **P10.** El botón flotante de campana de la captura original (alertas): ¿sigue existiendo en esta pantalla? Si es así, ¿dónde debe vivir para no chocar con el campo de escritura en móvil?
- **P11.** En la maqueta el sidebar se oculta bajo 760 px. ¿Es el breakpoint real de `base_app.html` o es otro?
- **P12.** Libreta de movimientos: ¿conviene marcarla como tabla semántica (`<table>`) por accesibilidad o como lista con líneas de puntos? ¿Cómo debe truncarse el concepto en 360 px de ancho?
- **P13.** Antes existía "Copiar tabla". ¿Se mantiene una acción equivalente ("Copiar movimientos") dentro del bloque libreta?

### C. Backend y modelo de lenguaje
- **P14.** Agent.md menciona Gemini Flash con Groq de respaldo en la tabla de stack, pero la sección del agente describe solo Groq con `llama-3.3-70b-versatile`. ¿Cuál es el estado real hoy?
- **P15.** ¿Se acepta que `POST /api/agente/chat/` devuelva `bloques` (esquema 7.3) en lugar de texto? ¿Cuál sería el costo de migrar `MensajeChat` con un `JSONField`?
- **P16.** `RecolectorDatos` y `EjecutorHerramientas` ya calculan agregados. ¿Cuáles de las fórmulas de la sección 7.4 existen ya y cuáles habría que agregar en `services.py`?
- **P17.** ¿Qué hace hoy el sistema si Groq responde con error, tarda demasiado o agota la cuota? ¿Hay respaldo sin IA para el chat (Agent.md lo menciona para las alertas, pero no para el chat)?
- **P18.** Validación de números del modelo (7.6): ¿es viable normalizar los formatos de moneda del usuario (`$19.900`, `19900`, "19,9 mil")? ¿Hay una alternativa más robusta?
- **P19.** Para ahorrar cuota se propone cachear respuestas por (usuario, intención, fecha). ¿Es aceptable que un dato quede desfasado hasta el siguiente movimiento registrado? ¿Se invalida con los signals existentes?
- **P20.** Streaming: ¿está habilitado hoy? Con bloques estructurados, el texto libre podría hacer streaming y los bloques de datos aparecer completos. ¿Tiene sentido para este proyecto o se descarta por complejidad?

### D. Producto y experiencia
- **P21.** Los atajos "Para seguir" salen de un mapa fijo por intención. ¿Qué intenciones soporta realmente el agente hoy, para no ofrecer preguntas sin respuesta?
- **P22.** Confirmación de "Limpiar chat": ¿usar `GastuAlerts` (SweetAlert2) con un texto claro de que el historial se borra de forma permanente?
- **P23.** Animación: ¿hay lineamientos del proyecto sobre movimiento? ¿Se aprueba una única animación de llenado del medidor y una de puntos en "revisando", con `prefers-reduced-motion`?
- **P24.** Tono de voz: "Mi consejo." habla en primera persona y con tono cercano. ¿Existe una guía de voz de marca para Gastu (formal o informal, tuteo, expresiones como "ojo")?
- **P25.** ¿Hay planes de adaptar este mismo sistema de bloques a otras pantallas (dashboard, `alertas_modal.html`)? Si es así, conviene extraerlos desde ahora como componentes compartidos.

### E. Sugerencias abiertas
- **P26.** ¿Qué otras mejoras recomendarías para el manejo del modelo (prompting, evaluación, observabilidad), dado que es menos capaz y de plan gratuito?
- **P27.** ¿Qué incongruencias ves entre esta maqueta y el resto de la aplicación (espaciados, iconografía, radios) que convenga corregir antes de implementar?
- **P28.** ¿Qué haría falta para probar visualmente esta pantalla con la metodología de Playwright del proyecto (seeders con presupuestos en estado ok, alerta y excedido, y con historial largo)?

---

## 12. Orden de implementación sugerido

1. Estructura y estilos base: layout sin card, encabezado, zona de mensajes, campo de escritura (sin dependencias del backend).
2. Burbuja del usuario, estado "revisando", estado vacío con saludo.
3. Renderizador de bloques en JS con datos de ejemplo (`texto`, `titular`, `procedencia`, `siguientes`).
4. Bloques de datos: `medidor`, `cifras`, `libreta`.
5. Backend: servicio `estado_presupuesto_categoria`, esquema de respuesta, validación y plantilla de respaldo para el `consejo`.
6. Campo `bloques` en el historial (migración) y mensajes antiguos como `texto`.
7. Estados de error, sin datos, excedido, accesibilidad y pruebas.

---

## 13. Archivos de referencia

| Archivo | Contenido |
|---|---|
| `gastu-agente-maqueta.html` | Maqueta estática con 4 estados: respuesta con presupuesto, estado vacío, libreta y "revisando", y vista móvil. Autocontenida; solo carga las fuentes de Google Fonts |
| `AGENTE_FINANCIERO_UI_BRIEF.md` | Este documento |

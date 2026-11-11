// ═══════════════════════════════════════════════════════════════
//  tours.js  —  Tutorial guiado con Driver.js para GastuApp
// ═══════════════════════════════════════════════════════════════

// Helper: genera el HTML con la imagen de Gastu + texto
const getGastuHtml = (imgSrc, text) => `
  <div class="gastu-chat-bubble-container">
    <div class="gastu-avatar-wrapper">
      <img src="${imgSrc}" class="gastu-avatar-img" alt="Gastu" />
      <div class="gastu-avatar-badge"></div>
    </div>
    <div class="gastu-chat-text">${text}</div>
  </div>
`;

// Imágenes del proyecto
const gastuImgs = {
  gastu_normal: window.GASTU_STATIC_URL + 'img/gastu_guia.png',
  gastu_rostro: window.GASTU_STATIC_URL + 'img/gastu_guia.png'
};

// Driver.js no corrige el popover cuando el elemento esta pegado al borde de
// la pantalla (pasa en movil): lo desplazamos lo justo para que quepa entero.
const MARGEN_POPOVER = 8;
const encajarPopover = (wrapper) => {
    if (!wrapper) return;
    wrapper.style.translate = '';
    wrapper.classList.remove('gastu-popover-desplazado');
    const rect = wrapper.getBoundingClientRect();
    let dx = 0;
    if (rect.right > window.innerWidth - MARGEN_POPOVER) dx = window.innerWidth - MARGEN_POPOVER - rect.right;
    if (rect.left + dx < MARGEN_POPOVER) dx = MARGEN_POPOVER - rect.left;
    if (dx) {
        wrapper.style.translate = dx + 'px 0';
        wrapper.classList.add('gastu-popover-desplazado'); // la flecha ya no apunta bien
    }
};
// Driver.js recoloca el popover despues de pintarlo (y al hacer scroll): cada vez
// que cambia su left/top lo volvemos a encajar.
const vigilarPopover = (wrapper) => {
    if (!wrapper || wrapper._gastuVigilado) return;
    wrapper._gastuVigilado = true;
    let ultima = '';
    new MutationObserver(() => {
        const pos = [wrapper.style.left, wrapper.style.top, wrapper.style.right, wrapper.className].join('|');
        if (pos === ultima) return;
        ultima = pos;
        encajarPopover(wrapper);
    }).observe(wrapper, { attributes: true, attributeFilter: ['style', 'class'] });
    encajarPopover(wrapper);
};

// Opciones comunes de Driver.js
const commonDriverOptions = {
    // Driver.js 1.0 no tiene onPopoverRender: el popover se busca al resaltar cada paso
    onHighlighted: () => vigilarPopover(document.querySelector('.driver-popover')),
    showProgress: true,
    progressText: '{{current}} de {{total}}',
    allowClose: false,      // NO cerrar al hacer clic en el overlay — solo con botón X
    showButtons: ['next', 'previous', 'close'], // Mostrar explícitamente el botón de cerrar/skip
    nextBtnText: 'Siguiente &rarr;',
    prevBtnText: '&larr; Anterior',
    doneBtnText: 'Entendido',
    popoverClass: 'gastu-driver-popover',
    overlayColor: '#0f172a',
    overlayOpacity: 0.72,
    stagePadding: 8,
    stageRadius: 12
};

// ── Definición de Tours por módulo ──────────────────────────
const toursConfig = {
    dashboard: [
        {
            popover: {
                title: '¡Bienvenido a GastuApp!',
                description: getGastuHtml(gastuImgs.gastu_normal, '¡Hola! Soy Gastu. Te doy un recorrido rápido por tu panel para que saques el máximo provecho a la app.'),
                align: 'center'
            }
        },
        {
            element: '#sidebar',
            popover: {
                title: 'Menú de navegación',
                description: getGastuHtml(gastuImgs.gastu_rostro, 'Desde aquí saltas a cualquier módulo: ingresos, egresos, ahorros, presupuestos, el agente y la captura automática.'),
                side: 'right', align: 'start'
            }
        },
        {
            element: '#status-badge-wrap',
            popover: {
                title: 'Estado de tu mes',
                description: 'De un vistazo: verde si vas bien, ámbar si tienes déficit o presupuestos en alerta, y rojo si tu dinero total quedó en negativo.',
                side: 'bottom', align: 'end'
            }
        },
        {
            element: '.nav-mes-group',
            popover: {
                title: 'Navegación por meses',
                description: 'Revisa meses anteriores o vuelve al mes actual con un clic.',
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '.carousel-section',
            popover: {
                title: 'Tarjetas de resumen',
                description: 'Total es todo tu dinero, incluido lo que tienes ahorrado. Disponible es lo que puedes gastar: no cuenta tus ahorros, porque ese dinero no deberías tocarlo. También verás tus ingresos, gastos y la diferencia del mes.',
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '.dash-filtros',
            popover: {
                title: 'Filtros y exportación',
                description: 'Filtra el panel por tipo de movimiento, fechas, montos o categorías, y descarga tu información en Excel o PDF.',
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '#chart-tendencia',
            popover: {
                title: 'Tendencia del mes',
                description: 'La evolución de tus ingresos y egresos día a día. Usa los botones de zoom para acercarte a un periodo.',
                side: 'top', align: 'start'
            }
        },
        {
            element: '#chart-pie',
            popover: {
                title: 'Distribución de gastos',
                description: 'En qué categorías se va tu dinero este mes.',
                side: 'top', align: 'start'
            }
        },
        {
            element: '.bottom-grid',
            popover: {
                title: 'Movimientos y metas',
                description: 'Tus últimas transacciones y el avance de tus metas de ahorro activas.',
                side: 'top', align: 'start'
            }
        },
        {
            element: '#notif-btn',
            popover: {
                title: 'Tus alertas',
                description: 'Aquí te aviso si detecto gastos inusuales o si te acercas al límite de un presupuesto. En la pestaña Pendientes aparecen los movimientos que capturé de tus correos del banco, listos para confirmar.',
                side: 'bottom', align: 'end'
            }
        },
        {
            element: '#user-btn',
            popover: {
                title: 'Tu cuenta',
                description: 'Entra a Mi perfil para cambiar tus datos, tu avatar o tus alertas, o cierra sesión.',
                side: 'bottom', align: 'end'
            }
        }
    ],
    ingresos: [
        {
            popover: {
                title: 'Módulo de ingresos',
                description: getGastuHtml(gastuImgs.gastu_rostro, 'Aquí registras todo el dinero que entra. ¡A sumar!'),
                align: 'center'
            }
        },
        {
            element: '.mov-resumen',
            popover: {
                title: 'Resumen del periodo',
                description: 'El total ingresado, cuántos registros llevas, en cuántas categorías y el promedio por registro. A la derecha ves tu disponible para gastar, sin contar lo que tienes ahorrado.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '#selector-periodo',
            popover: {
                title: 'Elige el periodo',
                description: 'Cambia el mes o el año para revisar ingresos anteriores.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '.toolbar__search',
            popover: {
                title: 'Buscador de categorías',
                description: 'Escribe para encontrar una categoría en segundos.',
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '#btn-historial',
            popover: {
                title: 'Historial de ingresos',
                description: 'El registro completo de tus ingresos en orden cronológico, para revisar un movimiento puntual.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '.export-group',
            popover: {
                title: 'Descargar',
                description: 'Exporta tus ingresos en PDF, Excel o CSV para compartirlos o respaldarlos.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '#btn-nuevo',
            popover: {
                title: 'Nuevo ingreso',
                description: getGastuHtml(gastuImgs.gastu_rostro, 'Registra aquí el dinero que entra. ¡Cada peso cuenta!'),
                side: 'bottom', align: 'end'
            }
        },
        {
            element: '.categorias-grid',
            popover: {
                title: 'Ingresos por categoría',
                description: 'Cuánto has ingresado en cada categoría y qué parte del total representa. Toca una tarjeta para ver su detalle.',
                side: 'top', align: 'start'
            }
        }
    ],
    egresos: [
        {
            popover: {
                title: 'Módulo de egresos',
                description: getGastuHtml(gastuImgs.gastu_normal, 'Lleva el control de tus gastos. Cada peso cuenta y yo te ayudo a cuidarlos.'),
                align: 'center'
            }
        },
        {
            element: '.mov-resumen',
            popover: {
                title: 'Resumen del periodo',
                description: 'El total gastado, cuántos registros llevas, en cuántas categorías y el promedio por gasto. A la derecha ves tu disponible para gastar, sin contar lo que tienes ahorrado.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '#selector-periodo',
            popover: {
                title: 'Elige el periodo',
                description: 'Cambia el mes o el año para comparar tus gastos con meses anteriores.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '.toolbar__search',
            popover: {
                title: 'Buscador de categorías',
                description: 'Escribe para encontrar una categoría y ver cuánto llevas gastado en ella.',
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '#btn-historial',
            popover: {
                title: 'Historial de egresos',
                description: 'Todos tus gastos en orden cronológico, ideal para rastrear un movimiento puntual.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '.export-group',
            popover: {
                title: 'Descargar',
                description: 'Exporta un reporte de tus gastos en PDF, Excel o CSV.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '#btn-nuevo',
            popover: {
                title: 'Nuevo egreso',
                description: getGastuHtml(gastuImgs.gastu_rostro, 'Añade tus gastos aquí. Te aviso si estás gastando demasiado rápido en una categoría.'),
                side: 'bottom', align: 'end'
            }
        },
        {
            element: '.cat-presupuesto',
            popover: {
                title: 'Medidor de presupuesto',
                description: 'Si la categoría tiene un presupuesto activo, este medidor muestra cuánto llevas: verde si vas bien, ámbar cuando te acercas al límite y rojo si te pasaste.',
                side: 'top', align: 'start'
            }
        },
        {
            element: '.categorias-grid',
            popover: {
                title: 'Gastos por categoría',
                description: 'En qué se va tu dinero este mes, categoría por categoría. Toca una tarjeta para ver su detalle.',
                side: 'top', align: 'start'
            }
        }
    ],
    programaciones: [
         {
            popover: {
                title: 'Programaciones Fijas',
                description: getGastuHtml(gastuImgs.gastu_normal, '¿Tienes recibos o suscripciones que pagas cada mes? Prográmalos aquí para que se registren solos o te avise.'),
                align: 'center'
            }
        },
        {
            element: '.stats-hero',
            popover: {
                title: 'Resumen de Programaciones',
                description: 'Aquí puedes ver cuántas programaciones tienes activas y el impacto mensual estimado de tus ingresos y egresos fijos.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '#btn-historial',
            popover: {
                title: 'Historial de Ejecuciones',
                description: 'Verifica qué programaciones se han ejecutado automáticamente y cuándo.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '#btn-nuevo',
            popover: {
                title: 'Nueva Programación',
                description: getGastuHtml(gastuImgs.gastu_rostro, 'Haz clic aquí para agregar un nuevo pago frecuente.'),
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '#cards-programacion-wrap',
            popover: {
                title: 'Tus Programaciones Activas',
                description: 'Gestiona todas tus programaciones. Puedes editarlas, pausarlas o eliminarlas desde aquí.',
                side: 'top', align: 'start'
            }
        }
    ],
    ahorros: [
        {
            popover: {
                title: 'Mis Ahorros',
                description: getGastuHtml(gastuImgs.gastu_normal, 'El primer paso para la libertad financiera es ahorrar. Crea metas y aparta dinero regularmente.'),
                align: 'center'
            }
        },
        {
            element: '.stats-hero',
            popover: {
                title: 'Progreso General',
                description: 'Revisa cuánto has ahorrado en total, cuántas metas has completado y cuándo es tu próximo aporte programado.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '.toolbar__search',
            popover: {
                title: 'Buscador de Metas',
                description: 'Encuentra rápidamente la meta de ahorro que buscas escribiendo su nombre o descripción aquí.',
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '#btn-historial',
            popover: {
                title: 'Historial de Aportes',
                description: 'Verifica todos los aportes que has hecho a tus diferentes metas de ahorro a lo largo del tiempo.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '.export-group',
            popover: {
                title: 'Exportación',
                description: 'Descarga el historial completo de tus ahorros en PDF, Excel o CSV para respaldar tu progreso.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '#btn-nueva-meta',
            popover: {
                title: 'Crear Meta',
                description: getGastuHtml(gastuImgs.gastu_rostro, 'Haz clic aquí para crear una nueva meta de ahorro (como "Viaje" o "Fondo de Emergencia").'),
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '#grid-metas',
            popover: {
                title: 'Tus Metas Activas',
                description: 'Aquí aparecerán tus metas. Podrás registrar aportes rápidamente y ver la barra de progreso de cada una.',
                side: 'top', align: 'start'
            }
        }
    ],
    presupuestos: [
        {
            popover: {
                title: 'Control de Presupuestos',
                description: getGastuHtml(gastuImgs.gastu_normal, 'Evita gastar de más estableciendo límites para cada categoría. Yo vigilaré que no te pases.'),
                align: 'center'
            }
        },
        {
            element: '.stats-hero',
            popover: {
                title: 'Estado Actual',
                description: 'Revisa rápidamente el total de tus límites mensuales y cuánto de tu dinero ya has consumido en presupuestos activos.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '#btn-nuevo',
            popover: {
                title: 'Nuevo Presupuesto',
                description: getGastuHtml(gastuImgs.gastu_rostro, 'Crea un límite de gasto mensual para la categoría que quieras controlar.'),
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '#cards-presupuesto',
            popover: {
                title: 'Tus Presupuestos',
                description: 'Aquí verás el progreso de cada presupuesto en tiempo real. Te alertaré con colores si te acercas demasiado a tu límite.',
                side: 'top', align: 'start'
            }
        }
    ],
    historial: [
        {
            popover: {
                title: 'Historial de Movimientos',
                description: getGastuHtml(gastuImgs.gastu_normal, 'Aquí podrás ver y filtrar todas tus transacciones pasadas.'),
                align: 'center'
            }
        },
        {
            element: '.toolbar__actions',
            popover: {
                title: 'Filtros y Exportación',
                description: 'Usa estas herramientas para exportar tu información a PDF, Excel o buscar un movimiento en específico.',
                side: 'bottom', align: 'start'
            }
        }
    ],
    agente: [
        {
            popover: {
                title: 'Agente financiero',
                description: getGastuHtml(gastuImgs.gastu_rostro, '¡Hola! Soy Gastu, tu asistente. Consulto tus datos reales para responderte y puedo registrar movimientos por ti.'),
                align: 'center'
            }
        },
        {
            element: '.agente-ask',
            popover: {
                title: 'Preguntas rápidas',
                description: 'Si no sabes por dónde empezar, toca una de estas preguntas.',
                side: 'top', align: 'center'
            }
        },
        {
            element: '#agenteForm',
            popover: {
                title: 'Escríbeme como quieras',
                description: 'Prueba con "¿En qué gasté más este mes?" o "Ayer gasté 20 mil en almuerzo". Si me pides un cambio, te muestro una tarjeta y nada se guarda hasta que tú lo confirmas.',
                side: 'top', align: 'center'
            }
        },
        {
            element: '#btnLimpiarChat',
            popover: {
                title: 'Nueva conversación',
                description: 'Borra el chat actual y empieza de cero.',
                side: 'bottom', align: 'end'
            }
        }
    ],
    captura: [
        {
            popover: {
                title: 'Captura automática',
                description: getGastuHtml(gastuImgs.gastu_normal, 'Reenvíame los correos de notificación de tu banco y yo convierto cada compra o transferencia en un movimiento. Tú solo revisas y confirmas.'),
                align: 'center'
            }
        },
        {
            element: '#btn-activar',
            popover: {
                title: 'Actívala en un paso',
                description: 'Al activarla te doy un correo personal y privado. Nunca te pediré claves del banco ni acceso a tu correo: solo veo las alertas que tú decidas reenviar.',
                side: 'top', align: 'center'
            }
        },
        {
            element: '#cap-hero',
            popover: {
                title: 'Lo que capturé',
                description: 'Cuántos movimientos esperan tu revisión, cuánto suman en gastos e ingresos y cuántos ya confirmaste.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '.cap-tabs',
            popover: {
                title: 'Pendientes, historial y reglas',
                description: 'En Pendientes confirmas o descartas cada movimiento. En Historial ves lo que ya procesé. En Reglas ves lo que aprendí: recuerdo la categoría de cada comercio que confirmas y, si activas Automático, los próximos se registran solos.',
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '.cap-direccion',
            popover: {
                title: 'Tu dirección de captura',
                description: 'Crea en Gmail un filtro que reenvíe solo las alertas de tu banco a esta dirección. Si un correo no viene del banco, te lo marco para que lo revises con cuidado.',
                side: 'left', align: 'start'
            }
        },
        {
            element: '.cap-config',
            popover: {
                title: 'Lista de configuración',
                description: 'Los pasos para dejarla lista. Se van marcando solos a medida que avanzas, hasta que llegue tu primera alerta.',
                side: 'left', align: 'start'
            }
        }
    ],
    perfil: [
        {
            popover: {
                title: 'Tu perfil',
                description: getGastuHtml(gastuImgs.gastu_normal, 'Administra tu cuenta, tu avatar, tus alertas y tus notificaciones.'),
                align: 'center'
            }
        },
        {
            element: '#btn-cambiar-avatar',
            popover: {
                title: 'Elige tu avatar',
                description: 'Toca tu avatar para elegir una de mis versiones: estudiante, chef, deportista y más. Se verá en tu perfil y en la barra superior.',
                side: 'bottom', align: 'start'
            }
        },
        {
            element: 'button[data-tab="datos"]',
            popover: {
                title: 'Tus datos',
                description: 'Tu información personal y la seguridad de tu cuenta.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '#perfil-form',
            popover: {
                title: 'Editar información',
                description: 'Actualiza tu nombre de usuario o tu teléfono.',
                side: 'top', align: 'start'
            }
        },
        {
            element: '#password-form',
            popover: {
                title: 'Seguridad',
                description: 'Cambia tu contraseña de vez en cuando para mantener tu cuenta segura.',
                side: 'top', align: 'start'
            }
        },
        {
            element: 'button[data-tab="preferencias"]',
            popover: {
                title: 'Preferencias de alertas',
                description: 'Elige qué te aviso y desde qué valores, agrupado por tema: presupuestos, tendencias, gastos pequeños y ahorro.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: 'button[data-tab="notificaciones"]',
            popover: {
                title: 'Centro de notificaciones',
                description: 'Todos los avisos que te he enviado, con filtros por tipo y la opción de marcarlos como leídos.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '.danger-zone',
            popover: {
                title: 'Zona de peligro',
                description: 'Desde aquí puedes eliminar tu cuenta y todos tus datos de forma permanente.',
                side: 'top', align: 'start'
            }
        }
    ]
};

// ── Motor del Tour ──────────────────────────────────────────
let _skipDialogOpen = false;  // Guardia contra re-entrada

window.GastuTours = {
    activeDriver: null,

    init: function(moduleName) {
        if (!toursConfig[moduleName] || typeof window.driver === 'undefined') return;

        const storageKey = 'gastu_tour_visto_' + moduleName;
        const hasSeen = localStorage.getItem(storageKey);

        if (!hasSeen) {
            if (moduleName === 'dashboard') {
                // Solo auto-iniciamos el Dashboard
                setTimeout(() => this.start(moduleName), 800);
            } else {
                // Fricción cero: sugerir sutilmente usando el botón del topbar
                const tourBtn = document.getElementById('tour-btn');
                if (tourBtn && !tourBtn.classList.contains('tour-pulse-hint')) {
                    tourBtn.classList.add('tour-pulse-hint');
                }
            }
        }
    },

    start: function(moduleName) {
        if (!toursConfig[moduleName] || typeof window.driver === 'undefined') return;

        // Esperar si hay un SweetAlert abierto (ej. "Novedades de hoy" o pendientes)
        if (document.querySelector('.swal2-container')) {
            setTimeout(() => this.start(moduleName), 1000);
            return;
        }

        this._launchDriver(moduleName);
    },

    _launchDriver: function(moduleName) {
        _skipDialogOpen = false;
        document.body.classList.add('tour-active');

        // Quitar la sugerencia si el usuario inició el tour manualmente
        const tourBtn = document.getElementById('tour-btn');
        if (tourBtn) tourBtn.classList.remove('tour-pulse-hint');

        // ── Tematización Dinámica por Módulo ──
        const moduleColors = {
            dashboard: { hex: '#047857', rgb: '4, 120, 87' },
            ingresos: { hex: '#10b981', rgb: '16, 185, 129' },
            egresos: { hex: '#e11d48', rgb: '225, 29, 72' },
            ahorros: { hex: '#d97706', rgb: '217, 119, 6' },
            programaciones: { hex: '#1d4ed8', rgb: '29, 78, 216' },
            presupuestos: { hex: '#7c3aed', rgb: '124, 58, 237' },
            agente: { hex: '#0ea5e9', rgb: '14, 165, 243' },
            perfil: { hex: '#2563eb', rgb: '37, 99, 235' },
            captura: { hex: '#a21caf', rgb: '162, 28, 175' },
            categorias: { hex: '#a855f7', rgb: '168, 85, 247' },
            historial: { hex: '#64748b', rgb: '100, 116, 139' }
        };
        const activeColor = moduleColors[moduleName] || { hex: '#10b981', rgb: '16, 185, 129' };
        document.documentElement.style.setProperty('--tour-accent-color', activeColor.hex);
        document.documentElement.style.setProperty('--tour-accent-color-rgb', activeColor.rgb);

        // ── Adaptación Dinámica de Elementos (Mobile vs Desktop) ──
        const isMobile = window.innerWidth <= 768;
        const adaptedSteps = toursConfig[moduleName].map(originalStep => {
            const step = { ...originalStep, popover: { ...originalStep.popover } };
            
            if (isMobile && step.element === '#sidebar') {
                step.element = '.sidebar-toggle-mobile-btn';
                step.popover.side = 'bottom';
                step.popover.align = 'start';
            }
            // En movil el popover ocupa casi todo el ancho: centrado no se sale
            // de la pantalla; los botones pegados al borde derecho van a su derecha.
            if (isMobile && step.element && step.element !== '.sidebar-toggle-mobile-btn') {
                const alDerecha = ['#btn-historial', '.export-group', '#btn-nuevo', '#notif-btn', '#user-btn', '#btnLimpiarChat'];
                step.popover.align = alDerecha.includes(step.element) ? 'end' : 'center';
            }
            return step;
        });

        // ── Filtrado Dinámico de Pasos (Responsive Seguro) ──
        const validSteps = adaptedSteps.filter(step => {
            if (!step.element) return true; // Popover centrado siempre es válido
            const el = document.querySelector(step.element);
            if (!el) return false;
            // Validar que el elemento sea visible
            const style = window.getComputedStyle(el);
            return style.display !== 'none' && style.visibility !== 'hidden' && el.offsetWidth > 0 && el.offsetHeight > 0;
        });

        // Función para bloquear clicks en el sidebar durante el tour
        const blockSidebarClicks = (e) => {
            if (document.body.classList.contains('tour-active')) {
                // Exceptuamos el botón de saltar
                if (e.target.closest('#btn-gastu-saltar-tour')) return;

                if (e.target.closest('#sidebar') || e.target.closest('.sidebar-toggle-mobile-btn') || e.target.closest('.sidebar-toggle-btn')) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (window.GastuAlerts) {
                        window.GastuAlerts.toastInfo('Por favor, termina o salta el tutorial antes de navegar.');
                    }
                }
            }
        };
        document.addEventListener('click', blockSidebarClicks, true); // Captura temprana

        // ── BOTÓN FLOTANTE "SALTAR TUTORIAL" (Premium Glassmorphism) ──
        let skipBtn = document.getElementById('btn-gastu-saltar-tour');
        if (!skipBtn) {
            skipBtn = document.createElement('button');
            skipBtn.id = 'btn-gastu-saltar-tour';
            skipBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 2px;"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                Saltar Tutorial
            `;
            skipBtn.style.cssText = `
                position: fixed;
                bottom: 25px;
                right: 25px;
                z-index: 2147483647;
                background: rgba(15, 23, 42, 0.8) !important;
                backdrop-filter: blur(8px) !important;
                -webkit-backdrop-filter: blur(8px) !important;
                color: #cbd5e1 !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                padding: 10px 18px !important;
                border-radius: 99px !important;
                font-family: 'DM Sans', sans-serif !important;
                font-weight: 600 !important;
                font-size: 14px !important;
                cursor: pointer !important;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.05) !important;
                display: flex !important;
                align-items: center !important;
                gap: 6px !important;
                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
                pointer-events: auto !important;
            `;
            skipBtn.onmouseover = () => {
                skipBtn.style.background = 'rgba(15, 23, 42, 0.95) !important';
                skipBtn.style.color = 'white !important';
                skipBtn.style.transform = 'translateY(-2px) scale(1.02) !important';
                skipBtn.style.borderColor = 'rgba(255, 255, 255, 0.2) !important';
                skipBtn.style.boxShadow = '0 12px 30px -5px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1) !important';
            };
            skipBtn.onmouseout  = () => {
                skipBtn.style.background = 'rgba(15, 23, 42, 0.8) !important';
                skipBtn.style.color = '#cbd5e1 !important';
                skipBtn.style.transform = 'translateY(0) scale(1) !important';
                skipBtn.style.borderColor = 'rgba(255, 255, 255, 0.1) !important';
                skipBtn.style.boxShadow = '0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.05) !important';
            };
            skipBtn.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (typeof window.driver !== 'undefined') {
                    // Trigger the onDestroyStarted logic
                    // En Driver.js v1, podemos intentar cerrar el popover actual
                    const closeBtn = document.querySelector('.driver-popover-close-btn');
                    if (closeBtn) {
                        closeBtn.click();
                    } else {
                        // Si no hay botón, forzamos destrucción
                        if (window.GastuTours.activeDriver) window.GastuTours.activeDriver.destroy();
                    }
                }
            };
            document.body.appendChild(skipBtn);
        }

        const cleanupTour = () => {
            document.body.classList.remove('tour-active');
            document.removeEventListener('click', blockSidebarClicks, true);
            const btn = document.getElementById('btn-gastu-saltar-tour');
            if (btn) btn.remove();
        };

        const driverObj = window.driver.js.driver({
            ...commonDriverOptions,
            steps: validSteps,
            onDestroyStarted: async () => {
                // Si ya no hay pasos, el tour terminó naturalmente
                if (!driverObj.hasNextStep()) {
                    driverObj.destroy();
                    localStorage.setItem('gastu_tour_visto_' + moduleName, 'true');
                    cleanupTour();
                    return;
                }

                // Evitar que se abra el diálogo más de una vez
                if (_skipDialogOpen) return;
                _skipDialogOpen = true;

                // Primero destruir el driver para que no haya conflicto de z-index
                driverObj.destroy();

                let saltar = true;
                if (window.GastuAlerts) {
                    saltar = await GastuAlerts.confirmar(
                        '¿Saltar tutorial?',
                        'Puedes volver a verlo en cualquier momento desde el botón de ayuda.',
                        'Sí, saltar'
                    );
                } else {
                    saltar = confirm('¿Saltar tutorial? Puedes volver a verlo luego.');
                }

                _skipDialogOpen = false;
                if (saltar) {
                    // El usuario quiere saltar — marcar como visto
                    localStorage.setItem('gastu_tour_visto_' + moduleName, 'true');
                    cleanupTour();
                } else {
                    // El usuario quiere continuar — relanzar el driver
                    this._launchDriver(moduleName);
                }
            },
        });

        window.driverObj = driverObj; // Compatibilidad absoluta con Playwright
        this.activeDriver = driverObj;
        driverObj.drive();
    }
};

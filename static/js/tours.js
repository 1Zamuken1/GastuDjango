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

// Opciones comunes de Driver.js
const commonDriverOptions = {
    showProgress: true,
    allowClose: false,      // NO cerrar al hacer clic en el overlay — solo con botón X
    showButtons: ['next', 'previous', 'close'], // Mostrar explícitamente el botón de cerrar/skip
    nextBtnText: 'Siguiente &rarr;',
    prevBtnText: '&larr; Anterior',
    doneBtnText: 'Entendido ✓',
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
                description: getGastuHtml(gastuImgs.gastu_normal, '¡Hola! Soy Gastu. Voy a darte un recorrido rápido por tu panel de control para que aproveches al máximo la app.'),
                align: 'center'
            }
        },
        {
            element: '#sidebar',
            popover: {
                title: 'Menú de Navegación',
                description: getGastuHtml(gastuImgs.gastu_rostro, 'Desde aquí puedes saltar a cualquier módulo: ingresos, egresos, ahorros y más.'),
                side: 'right', align: 'start'
            }
        },
        {
            element: '.nav-mes-group',
            popover: {
                title: 'Navegación por Meses',
                description: 'Aquí puedes revisar la información de meses pasados o volver rápidamente al mes actual.',
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '.carousel-section',
            popover: {
                title: 'Tarjetas de Resumen',
                description: 'Desliza estas tarjetas para ver tu saldo disponible, utilidad, ahorros y la diferencia entre tus ingresos y gastos.',
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '#chart-tendencia',
            popover: {
                title: 'Tendencia Financiera',
                description: 'Observa la evolución de tus ingresos y egresos a lo largo del mes. Puedes arrastrar y hacer zoom.',
                side: 'top', align: 'start'
            }
        },
        {
            element: '#chart-pie',
            popover: {
                title: 'Distribución de Gastos',
                description: 'Descubre en qué categorías estás gastando más dinero mediante este gráfico circular.',
                side: 'top', align: 'start'
            }
        },
        {
            element: '.bottom-grid',
            popover: {
                title: 'Movimientos y Metas',
                description: 'Revisa tus transacciones recientes y el estado de tus metas de ahorro activas.',
                side: 'top', align: 'start'
            }
        },
        {
            element: '#notif-btn',
            popover: {
                title: 'Tus Alertas',
                description: 'Aquí te enviaré notificaciones inteligentes si detecto gastos inusuales o si te acercas a tu límite presupuestal.',
                side: 'bottom', align: 'end'
            }
        },
        {
            element: '#user-btn',
            popover: {
                title: 'Perfil y Sesión',
                description: 'Tu espacio personal. Actualiza tus datos o cierra sesión desde este menú.',
                side: 'bottom', align: 'end'
            }
        }
    ],
    ingresos: [
        {
            popover: {
                title: 'Módulo de Ingresos',
                description: getGastuHtml(gastuImgs.gastu_rostro, 'Aquí puedes registrar todo el dinero que entra. ¡A sumar!'),
                align: 'center'
            }
        },
        {
            element: '.hero-stats',
            popover: {
                title: 'Métricas Rápidas',
                description: 'Un resumen de tus ingresos del mes: cantidad de registros, categorías con actividad y el promedio por registro.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '.toolbar__search',
            popover: {
                title: 'Buscador de Categorías',
                description: 'Escribe aquí para filtrar rápidamente tus ingresos y encontrar una categoría específica en segundos.',
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '#btn-historial',
            popover: {
                title: 'Historial de Ingresos',
                description: 'Aquí se almacena el registro cronológico completo de todos tus ingresos. Útil para auditorías o revisiones detalladas.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '.export-group',
            popover: {
                title: 'Exportación de Datos',
                description: 'Puedes descargar tu información en formato PDF, Excel o CSV para compartirla o respaldarla.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '#btn-nuevo',
            popover: {
                title: 'Nuevo Ingreso',
                description: getGastuHtml(gastuImgs.gastu_rostro, 'Usa este botón para registrar dinero entrante. ¡Cada centavo cuenta!'),
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '.categorias-grid',
            popover: {
                title: 'Ingresos por Categoría',
                description: 'Aquí verás cuánto has ingresado en cada categoría este mes y su porcentaje respecto al total.',
                side: 'top', align: 'start'
            }
        }
    ],
    egresos: [
         {
            popover: {
                title: 'Módulo de Egresos',
                description: getGastuHtml(gastuImgs.gastu_normal, 'Lleva el control de todos tus gastos. Recuerda: cada peso cuenta y yo te ayudaré a cuidarlos.'),
                align: 'center'
            }
        },
        {
            element: '.hero-stats',
            popover: {
                title: 'Resumen de Gastos',
                description: 'Revisa cuántos gastos has registrado, en cuántas categorías y cuál es tu promedio de gasto por registro este mes.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '.toolbar__search',
            popover: {
                title: 'Buscador de Categorías',
                description: 'Escribe aquí para encontrar rápidamente una categoría y ver cuánto has gastado en ella.',
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '#btn-historial',
            popover: {
                title: 'Historial de Egresos',
                description: 'Aquí se almacenan todos tus gastos de forma cronológica. Ideal para rastrear movimientos puntuales.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '.export-group',
            popover: {
                title: 'Exportación de Datos',
                description: 'Descarga un reporte detallado de tus gastos en formato PDF, Excel o CSV para tu control personal.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '#btn-nuevo',
            popover: {
                title: 'Nuevo Egreso',
                description: getGastuHtml(gastuImgs.gastu_rostro, 'Añade tus gastos aquí. Te avisaré si estás gastando demasiado rápido en una categoría.'),
                side: 'bottom', align: 'start'
            }
        },
        {
            element: '.categorias-grid',
            popover: {
                title: 'Gastos por Categoría',
                description: 'Un desglose visual de en qué estás gastando más tu dinero durante el mes.',
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
            element: '.btn-historial',
            popover: {
                title: 'Historial de Ejecuciones',
                description: 'Verifica qué programaciones se han ejecutado automáticamente y cuándo.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '.btn-crear',
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
            element: '.btn-crear',
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
                title: 'Agente Financiero',
                description: getGastuHtml(gastuImgs.gastu_rostro, '¡Hola! Soy tu asistente inteligente. Puedes preguntarme cualquier duda sobre tus finanzas y te daré consejos.'),
                align: 'center'
            }
        },
        {
            element: '.agente-sugerencias',
            popover: {
                title: 'Preguntas Rápidas',
                description: 'Si no sabes qué preguntar, puedes empezar haciendo clic en cualquiera de estas sugerencias.',
                side: 'top', align: 'center'
            }
        },
        {
            element: '.agente-input-wrapper',
            popover: {
                title: 'Escribe tu consulta',
                description: 'Escríbeme por aquí. Intenta preguntar "¿En qué gasté más este mes?" o "¿Cómo puedo ahorrar más?"',
                side: 'top', align: 'center'
            }
        },
        {
            element: '#btnLimpiarChat',
            popover: {
                title: 'Reiniciar Conversación',
                description: 'Usa este botón si quieres borrar el historial de chat actual y empezar una nueva conversación.',
                side: 'bottom', align: 'end'
            }
        }
    ],
    perfil: [
        {
            popover: {
                title: 'Tu Perfil',
                description: getGastuHtml(gastuImgs.gastu_normal, 'Administra tu cuenta, cambia tu contraseña y revisa tu información personal.'),
                align: 'center'
            }
        },
        {
            element: 'button[data-tab="datos"]',
            popover: {
                title: 'Sección de Datos',
                description: 'Aquí puedes gestionar tu información personal y seguridad básica.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '#perfil-form',
            popover: {
                title: 'Editar Información',
                description: 'Actualiza tu nombre de usuario o tu teléfono de contacto desde este formulario.',
                side: 'right', align: 'start'
            }
        },
        {
            element: '#password-form',
            popover: {
                title: 'Seguridad',
                description: 'Cambia tu contraseña periódicamente para mantener tu cuenta segura.',
                side: 'right', align: 'start'
            }
        },
        {
            element: 'button[data-tab="preferencias"]',
            popover: {
                title: 'Preferencias de Alerta',
                description: 'Ajusta cuándo y cómo te avisaré sobre tus gastos y presupuestos (ej. umbral al 80%).',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: 'button[data-tab="notificaciones"]',
            popover: {
                title: 'Centro de Notificaciones',
                description: 'Aquí almacenaré todos los avisos que te he enviado por si necesitas revisarlos después.',
                side: 'bottom', align: 'center'
            }
        },
        {
            element: '.danger-zone',
            popover: {
                title: 'Zona de Peligro',
                description: 'Cuidado aquí. Desde esta sección puedes eliminar permanentemente tu cuenta y todos tus datos.',
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
            dashboard: { hex: '#6366f1', rgb: '99, 102, 241' },
            ingresos: { hex: '#10b981', rgb: '16, 185, 129' },
            egresos: { hex: '#e11d48', rgb: '225, 29, 72' },
            ahorros: { hex: '#d97706', rgb: '217, 119, 6' },
            programaciones: { hex: '#1d4ed8', rgb: '29, 78, 216' },
            presupuestos: { hex: '#7c3aed', rgb: '124, 58, 237' },
            agente: { hex: '#0ea5e9', rgb: '14, 165, 243' },
            perfil: { hex: '#0d9488', rgb: '13, 148, 136' },
            categorias: { hex: '#a855f7', rgb: '168, 85, 247' },
            historial: { hex: '#64748b', rgb: '100, 116, 139' }
        };
        const activeColor = moduleColors[moduleName] || { hex: '#10b981', rgb: '16, 185, 129' };
        document.documentElement.style.setProperty('--tour-accent-color', activeColor.hex);
        document.documentElement.style.setProperty('--tour-accent-color-rgb', activeColor.rgb);

        // ── Filtrado Dinámico de Pasos (Responsive Seguro) ──
        const validSteps = toursConfig[moduleName].filter(step => {
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

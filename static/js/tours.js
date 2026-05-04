// ═══════════════════════════════════════════════════════════════
//  tours.js  —  Tutorial guiado con Driver.js para GastuApp
// ═══════════════════════════════════════════════════════════════

// Helper: genera el HTML con la imagen de Gastu + texto
const getGastuHtml = (imgSrc, text) => `
  <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 16px;">
    <img src="${imgSrc}" alt="Gastu" style="width: 80px; height: 80px; object-fit: contain; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1)); border-radius: 12px;" />
    <div style="font-size: 0.95rem; color: #334155; font-weight: 500; line-height: 1.6;">${text}</div>
  </div>
`;

// Imágenes del proyecto (sin fondo pixelado)
const gastuImgs = {
  dashboard: window.GASTU_STATIC_URL + 'img/gastu_logo.png',
  ingresos: window.GASTU_STATIC_URL + 'img/gastu_logo_rostro.png',
  programaciones: window.GASTU_STATIC_URL + 'img/gastu_logo.png',
  pointing: window.GASTU_STATIC_URL + 'img/gastu_logo_rostro.png',
  base: window.GASTU_STATIC_URL + 'img/gastu_logo.png'
};

// Opciones comunes de Driver.js
const commonDriverOptions = {
    showProgress: true,
    allowClose: false,      // NO cerrar al hacer clic en el overlay — solo con botón X
    nextBtnText: 'Siguiente &rarr;',
    prevBtnText: '&larr; Anterior',
    doneBtnText: 'Entendido ✓',
    popoverClass: 'gastu-driver-popover',
};

// ── Definición de Tours por módulo ──────────────────────────
const toursConfig = {
    dashboard: [
        {
            popover: {
                title: '¡Bienvenido a GastuApp!',
                description: getGastuHtml(gastuImgs.dashboard, '¡Hola! Soy Gastu. Voy a darte un recorrido rápido por tu panel de control para que aproveches al máximo la app.'),
                align: 'center'
            }
        },
        {
            element: '#sidebar',
            popover: {
                title: 'Menú de Navegación',
                description: getGastuHtml(gastuImgs.pointing, 'Desde aquí puedes saltar a cualquier módulo: ingresos, egresos, ahorros y más.'),
                side: 'right', align: 'start'
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
            element: '#tour-btn',
            popover: {
                title: 'Botón de Ayuda',
                description: 'Si quieres volver a ver este tutorial en cualquier momento, haz clic aquí.',
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
                description: getGastuHtml(gastuImgs.ingresos, 'Aquí puedes registrar todo el dinero que entra. ¡A sumar!'),
                align: 'center'
            }
        },
        {
            element: '#btn-nuevo',
            popover: {
                title: 'Nuevo Ingreso',
                description: getGastuHtml(gastuImgs.pointing, 'Usa este botón para registrar un nuevo ingreso. Puedes asignarle una categoría.'),
                side: 'bottom', align: 'start'
            }
        }
    ],
    egresos: [
         {
            popover: {
                title: 'Módulo de Egresos',
                description: getGastuHtml(gastuImgs.base, 'Lleva el control de todos tus gastos. Recuerda: cada peso cuenta y yo te ayudaré a cuidarlos.'),
                align: 'center'
            }
        },
        {
            element: '#btn-nuevo',
            popover: {
                title: 'Nuevo Egreso',
                description: getGastuHtml(gastuImgs.pointing, 'Añade tus gastos aquí. Te avisaré si estás gastando demasiado rápido.'),
                side: 'bottom', align: 'start'
            }
        }
    ],
    programaciones: [
         {
            popover: {
                title: 'Programaciones Fijas',
                description: getGastuHtml(gastuImgs.programaciones, '¿Tienes recibos o suscripciones que pagas cada mes? Prográmalos aquí para que se registren solos o te avise.'),
                align: 'center'
            }
        },
        {
            element: '.btn-crear',
            popover: {
                title: 'Nueva Programación',
                description: getGastuHtml(gastuImgs.pointing, 'Haz clic aquí para agregar un nuevo pago frecuente.'),
                side: 'bottom', align: 'start'
            }
        }
    ]
};

// ── Motor del Tour ──────────────────────────────────────────
let _skipDialogOpen = false;  // Guardia contra re-entrada

window.GastuTours = {
    init: function(moduleName) {
        if (!toursConfig[moduleName] || typeof window.driver === 'undefined') return;

        const storageKey = 'gastu_tour_visto_' + moduleName;
        const hasSeen = localStorage.getItem(storageKey);

        if (!hasSeen) {
            setTimeout(() => this.start(moduleName), 800);
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

        // Función para bloquear clicks en el sidebar durante el tour
        const blockSidebarClicks = (e) => {
            if (document.body.classList.contains('tour-active')) {
                if (e.target.closest('#sidebar') || e.target.closest('.sidebar-toggle-mobile-btn') || e.target.closest('.sidebar-toggle-btn')) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (window.GastuAlerts) {
                        window.GastuAlerts.toastInfo('Por favor, cierra el tutorial antes de navegar.');
                    }
                }
            }
        };
        document.addEventListener('click', blockSidebarClicks, true); // Captura temprana

        const cleanupTour = () => {
            document.body.classList.remove('tour-active');
            document.removeEventListener('click', blockSidebarClicks, true);
        };

        const driverObj = window.driver.js.driver({
            ...commonDriverOptions,
            steps: toursConfig[moduleName],
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

        driverObj.drive();
    }
};

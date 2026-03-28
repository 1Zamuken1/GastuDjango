/**
 * historial.js — Panel lateral de historial de acciones.
 *
 * Configuracion de tema por modulo:
 *   El boton #btn-historial debe tener estos data-attributes:
 *     data-modulo       "MOVIMIENTOS" | "AHORROS" | "PRESUPUESTOS" | ...
 *     data-tema-accent  Color principal del modulo (ej: "#10b981")
 *     data-tema-light   Color de fondo claro (ej: "#ecfdf5")
 *     data-tema-label   Texto descriptivo (ej: "Ingresos")
 *     data-tema-icon    Icono Lucide del header (ej: "trending-up")
 */
document.addEventListener('DOMContentLoaded', () => {
    const btnAbrir  = document.getElementById('btn-historial');
    const panel     = document.getElementById('historial-offcanvas');
    const overlay   = document.getElementById('historial-overlay');
    const btnCerrar = document.getElementById('btn-cerrar-historial');
    const body      = document.getElementById('historial-lista');

    if (!btnAbrir || !panel) return;

    /* ── Leer configuracion del boton ── */
    const modulo = btnAbrir.dataset.modulo || 'MOVIMIENTOS';
    const tema = {
        accent:  btnAbrir.dataset.temaAccent || '#10b981',
        light:   btnAbrir.dataset.temaLight  || '#ecfdf5',
        label:   btnAbrir.dataset.temaLabel  || 'Movimientos',
        icon:    btnAbrir.dataset.temaIcon   || 'history',
    };

    /* ── Aplicar variables CSS del tema al panel ── */
    function aplicarTema() {
        panel.style.setProperty('--h-accent', tema.accent);
        panel.style.setProperty('--h-accent-light', tema.light);

        const headerIcon = panel.querySelector('.historial-header__icon-wrapper');
        if (headerIcon) {
            headerIcon.style.background = tema.accent;
        }

        const headerTitle = panel.querySelector('.historial-header__title');
        if (headerTitle) {
            headerTitle.textContent = 'Historial de ' + tema.label;
        }

        const headerIconEl = panel.querySelector('.historial-header__icon-wrapper i');
        if (headerIconEl) {
            headerIconEl.setAttribute('data-lucide', tema.icon);
        }
    }

    /* ── Abrir / cerrar ── */
    function abrirPanel() {
        aplicarTema();
        panel.classList.add('open');
        overlay.classList.add('show');
        document.body.style.overflow = 'hidden';
        cargarHistorial();
        lucide.createIcons();
    }

    function cerrarPanel() {
        panel.classList.remove('open');
        overlay.classList.remove('show');
        document.body.style.overflow = '';
    }

    btnAbrir.addEventListener('click', abrirPanel);
    btnCerrar.addEventListener('click', cerrarPanel);
    overlay.addEventListener('click', cerrarPanel);

    /* Cerrar con Escape */
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && panel.classList.contains('open')) {
            cerrarPanel();
        }
    });

    /* ── Cargar datos ── */
    async function cargarHistorial() {
        body.innerHTML = renderEstado('loading');
        lucide.createIcons();

        try {
            const resp = await fetch('/historial/api/listar/?modulo=' + modulo);
            const data = await resp.json();

            if (!data.ok) {
                throw new Error(data.error || 'Error al cargar');
            }

            renderizarHistorial(data.resultados);
        } catch (_err) {
            body.innerHTML = renderEstado('error');
            lucide.createIcons();
        }
    }

    /* ── Estado (loading, empty, error) ── */
    function renderEstado(tipo) {
        const configs = {
            loading: {
                iconClass: 'historial-state__icon--loading',
                icon: 'loader',
                spin: true,
                title: 'Cargando historial...',
                sub: 'Obteniendo tus acciones recientes',
            },
            empty: {
                iconClass: 'historial-state__icon--empty',
                icon: 'inbox',
                spin: false,
                title: 'Sin actividad reciente',
                sub: 'Las acciones de los ultimos 30 dias apareceran aqui.',
            },
            error: {
                iconClass: 'historial-state__icon--error',
                icon: 'alert-triangle',
                spin: false,
                title: 'No se pudo cargar',
                sub: 'Ocurrio un error al obtener el historial. Intenta de nuevo.',
            },
        };
        const c = configs[tipo];
        return `
            <div class="historial-state">
                <div class="historial-state__icon ${c.iconClass}">
                    <i data-lucide="${c.icon}" ${c.spin ? 'class="historial-spin"' : ''}></i>
                </div>
                <p class="historial-state__title">${c.title}</p>
                <p class="historial-state__sub">${c.sub}</p>
            </div>
        `;
    }

    /* ── Renderizar lista completa ── */
    function renderizarHistorial(acciones) {
        if (!acciones || acciones.length === 0) {
            body.innerHTML = renderEstado('empty');
            lucide.createIcons();
            return;
        }

        /* Barra de stats */
        const conteos = { CREACION: 0, EDICION: 0, ELIMINACION: 0 };
        acciones.forEach(a => { conteos[a.accion] = (conteos[a.accion] || 0) + 1; });

        const statsHTML = `
            <div class="historial-header__stats">
                <span class="historial-stat-badge">
                    <span class="historial-stat-badge__dot"></span>
                    ${acciones.length} accion${acciones.length !== 1 ? 'es' : ''}
                </span>
                <div style="display:flex;gap:10px;">
                    ${conteos.CREACION ? `<span class="historial-stat-badge" style="color:#059669;"><i data-lucide="plus" style="width:10px;height:10px;"></i> ${conteos.CREACION}</span>` : ''}
                    ${conteos.EDICION ? `<span class="historial-stat-badge" style="color:#2563eb;"><i data-lucide="pencil" style="width:10px;height:10px;"></i> ${conteos.EDICION}</span>` : ''}
                    ${conteos.ELIMINACION ? `<span class="historial-stat-badge" style="color:#e11d48;"><i data-lucide="trash-2" style="width:10px;height:10px;"></i> ${conteos.ELIMINACION}</span>` : ''}
                </div>
            </div>
        `;

        /* Insertar stats debajo del header */
        const statsContainer = panel.querySelector('#historial-stats');
        if (statsContainer) {
            statsContainer.innerHTML = statsHTML;
        }

        /* Timeline */
        const actionMap = {
            CREACION:    { icon: 'plus',    tag: 'Creado',    nodeClass: 'historial-item__node--creacion',    tagClass: 'historial-item__tag--creacion' },
            EDICION:     { icon: 'pencil',  tag: 'Editado',   nodeClass: 'historial-item__node--edicion',     tagClass: 'historial-item__tag--edicion' },
            ELIMINACION: { icon: 'trash-2', tag: 'Eliminado', nodeClass: 'historial-item__node--eliminacion', tagClass: 'historial-item__tag--eliminacion' },
        };

        let itemsHTML = '<div class="historial-timeline">';
        acciones.forEach(act => {
            const cfg = actionMap[act.accion] || actionMap.CREACION;

            const montoHTML = act.monto_afectado
                ? `<span class="historial-item__monto" style="background:${tema.light};color:${tema.accent};">$${parseFloat(act.monto_afectado).toLocaleString('es-CO')}</span>`
                : '';

            itemsHTML += `
                <div class="historial-item">
                    <div class="historial-item__node ${cfg.nodeClass}">
                        <i data-lucide="${cfg.icon}"></i>
                    </div>
                    <div class="historial-item__body">
                        <div class="historial-item__top">
                            <p class="historial-item__desc">${act.descripcion}</p>
                            ${montoHTML}
                        </div>
                        <div class="historial-item__meta">
                            <span class="historial-item__time">
                                <i data-lucide="clock"></i>
                                ${act.fecha}
                            </span>
                            <span class="historial-item__tag ${cfg.tagClass}">${cfg.tag}</span>
                        </div>
                    </div>
                </div>
            `;
        });
        itemsHTML += '</div>';

        body.innerHTML = itemsHTML;
        lucide.createIcons();
    }
});

/**
 * category-picker.js
 * Módulo reutilizable para el modal de categorías con Favoritas y Recurrentes.
 */

window.CategoryPicker = {
    init: function(options) {
        this.containerId = options.containerId || 'picker-grid';
        this.tipo = options.tipo || ''; // INGRESO, EGRESO, AHORRO, o '' para todas
        this.onSelect = options.onSelect || function(){};
        this.context = options.context || 'movimientos';
        this.allCategories = [];
        this.filteredCategories = [];
        this.injectStyles();
        this.loadCategories();
    },

    injectStyles: function() {
        if (document.getElementById('category-picker-styles')) return;
        const style = document.createElement('style');
        style.id = 'category-picker-styles';
        style.textContent = `
            /* Estandarización y posición relativa de las cards */
            .picker-cat-card {
                position: relative !important;
                overflow: visible !important;
            }
            /* Agrandar hit area del botón de favoritos (corazón) */
            .picker-cat-fav-btn {
                position: absolute !important;
                top: 2px !important;
                right: 2px !important;
                width: 32px !important;
                height: 32px !important;
                display: grid !important;
                place-items: center !important;
                border-radius: 50% !important;
                cursor: pointer !important;
                z-index: 10 !important;
                background: transparent !important;
                transition: transform 0.2s ease, background-color 0.2s ease, color 0.2s ease !important;
            }
            /* Area invisible expandida para facilitar el click (auto-apuntar) */
            .picker-cat-fav-btn::before {
                content: '';
                position: absolute;
                top: -6px;
                left: -6px;
                right: -6px;
                bottom: -6px;
                border-radius: 50%;
            }
            .picker-cat-fav-btn:hover {
                background-color: rgba(244, 63, 94, 0.12) !important;
                transform: scale(1.25) !important;
                color: #f43f5e !important;
            }
            .picker-cat-fav-btn:active {
                transform: scale(0.95) !important;
            }
            .picker-cat-fav-btn--active {
                color: #f43f5e !important;
            }
            
            /* Responsive Grid del picker de categorías - usando auto-fill fluido con base en 130px */
            .picker-cat-grid {
                display: grid !important;
                grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)) !important;
                gap: 12px !important;
                overflow-y: auto !important;
                padding: 4px !important;
                align-content: start !important;
            }
            
            /* Evitar cortes de palabras a la mitad de una letra */
            .picker-cat-nombre {
                word-break: normal !important;
                overflow-wrap: break-word !important;
                hyphens: auto !important;
            }
            
            /* Asegurar centrado del modal y evitar desbordamientos en móvil */
            #modal-picker-cat .modal,
            #modal-picker-cat-dash .modal,
            #modal-categorias .modal-container {
                width: calc(100% - 24px) !important;
                max-width: 720px !important;
                box-sizing: border-box !important;
                margin: 12px auto !important;
            }

            /* Prevenir desbordamiento del modal en dashboard */
            #modal-picker-cat-dash .modal {
                display: flex !important;
                flex-direction: column !important;
                max-height: 85vh !important;
                overflow: hidden !important;
            }
            #modal-picker-cat-dash .modal__body {
                display: flex !important;
                flex-direction: column !important;
                overflow: hidden !important;
                flex: 1 !important;
                max-height: calc(85vh - 70px) !important;
            }
            #modal-picker-cat-dash #picker-cat-grid {
                flex: 1 !important;
                overflow-y: auto !important;
                min-height: 0 !important;
            }

            /* Breakpoints responsivos para móvil */
            @media (max-width: 479px) {
                .picker-cat-grid {
                    grid-template-columns: repeat(auto-fill, minmax(105px, 1fr)) !important;
                    gap: 8px !important;
                }
                .picker-cat-card {
                    padding: 0.75rem 0.5rem !important;
                }
                .picker-cat-nombre {
                    font-size: 0.72rem !important;
                }
                #modal-picker-cat .modal__header,
                #modal-picker-cat-dash .modal__header,
                #modal-categorias .modal__header {
                    padding: 0.75rem 1rem !important;
                }
                #modal-picker-cat-dash .modal__body {
                    max-height: calc(90vh - 65px) !important;
                }
            }
        `;
        document.head.appendChild(style);
    },

    loadCategories: function(tipoOverride) {
        const tipo = tipoOverride !== undefined ? tipoOverride : this.tipo;
        this.tipo = tipo; // update current state
        const container = document.getElementById(this.containerId);
        if (!container) return;
        
        container.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:2rem;color:#94a3b8;"><i data-lucide="loader-2" class="animate-spin" style="width:24px;height:24px;margin:0 auto;"></i></div>';
        if (typeof lucide !== 'undefined') lucide.createIcons();

        const actividadParam = (this.context === 'dashboard') ? '&actividad=true' : '';

        fetch(`/api/categorias/enriched/?tipo=${tipo}${actividadParam}`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(res => res.json())
            .then(data => {
                this.allCategories = data;
                this.filteredCategories = [...data];
                this.render();
            })
            .catch(err => {
                console.error("Error cargando categorías:", err);
                container.innerHTML = '<p style="grid-column:1/-1;text-align:center;color:#ef4444;">Error al cargar categorías</p>';
            });
    },

    filter: function(query) {
        query = query.toLowerCase().trim();
        if (!query) {
            this.filteredCategories = [...this.allCategories];
        } else {
            this.filteredCategories = this.allCategories.filter(c => c.nombre.toLowerCase().includes(query));
        }
        this.render();
    },

    toggleFavorita: function(e, id) {
        e.stopPropagation();
        
        // Optimistic UI update
        const cat = this.allCategories.find(c => c.id == id);
        if (cat) {
            cat.es_favorita = !cat.es_favorita;
            this.render();
        }

        const csrfMatch = document.cookie.match(/csrftoken=([^;]+)/);
        const csrfToken = csrfMatch ? csrfMatch[1] : '';

        fetch(`/api/categorias/${id}/toggle-favorita/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            }
        })
        .then(res => res.json())
        .then(data => {
            if (cat && cat.es_favorita !== data.es_favorita) {
                cat.es_favorita = data.es_favorita;
                this.render();
            }
        })
        .catch(err => {
            console.error("Error toggle favorita:", err);
            // revert
            if (cat) {
                cat.es_favorita = !cat.es_favorita;
                this.render();
            }
        });
    },

    render: function() {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        let html = '';

        if (this.context === 'dashboard' && this.filteredCategories.length === this.allCategories.length) {
            html += `
            <div style="grid-column:1/-1; margin-bottom:-8px;">
              <button type="button" class="picker-cat-card picker-cat-card--default" data-id="" data-nombre="Todas las categorías" data-tipo="" style="width:100%; justify-content:center; padding:12px; border:2px dashed #cbd5e1; background:transparent;">
                <div class="picker-cat-icon">
                  <i data-lucide="layers" style="width:18px;height:18px;"></i>
                </div>
                <span class="picker-cat-nombre">Todas las Categorías</span>
              </button>
            </div>
            `;
        }

        const favoritas = this.filteredCategories.filter(c => c.es_favorita);
        
        const resto = this.filteredCategories.filter(c => !c.es_favorita);
        const topResto = [...resto].sort((a, b) => b.uso_global - a.uso_global);
        const recurrentes = topResto.slice(0, 6).filter(c => c.uso_global > 0);
        
        const recurrentesIds = recurrentes.map(c => c.id);
        const otras = resto.filter(c => !recurrentesIds.includes(c.id));

        if (favoritas.length > 0) {
            html += this._renderSection('Favoritas', favoritas, 'heart', '#f43f5e');
        }
        if (recurrentes.length > 0) {
            html += this._renderSection('Recurrentes', recurrentes, 'trending-up', '#10b981');
        }
        if (otras.length > 0) {
            html += this._renderSection(favoritas.length || recurrentes.length ? 'Otras' : '', otras, 'folder', '#94a3b8', true);
        }

        if (this.filteredCategories.length === 0) {
            html += '<p style="grid-column:1/-1;text-align:center;color:#94a3b8;font-size:14px;padding:2rem;">Sin resultados</p>';
        }

        container.innerHTML = html;

        const cards = container.querySelectorAll('.picker-cat-card:not(.picker-cat-card--default)');
        cards.forEach(card => {
            card.addEventListener('click', (e) => {
                if (e.target.closest('.picker-cat-fav-btn')) return;
                const id = card.getAttribute('data-id');
                const cat = this.allCategories.find(c => c.id == id);
                if (cat) this.onSelect(cat);
            });
        });

        const favBtns = container.querySelectorAll('.picker-cat-fav-btn');
        favBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = btn.getAttribute('data-id');
                this.toggleFavorita(e, id);
            });
        });

        const btnTodas = container.querySelector('.picker-cat-card--default');
        if (btnTodas) {
            btnTodas.addEventListener('click', () => {
                this.onSelect({ id: '', nombre: 'Todas las categorías', tipo: '' });
            });
        }

        if (typeof lucide !== 'undefined') lucide.createIcons();
    },

    _renderSection: function(title, categories, icon, color, isOtras=false) {
        let out = '';
        if (title) {
            out += `
            <div class="picker-section-header" style="grid-column:1/-1; display:flex; align-items:center; gap:8px; margin-top:${isOtras ? '16px' : '8px'}; margin-bottom:8px;">
                <i data-lucide="${icon}" style="width:16px;height:16px;color:${color};"></i>
                <h4 style="font-size:13px;font-weight:700;color:#334155;text-transform:uppercase;letter-spacing:0.05em;margin:0;white-space:nowrap;">${title}</h4>
                <div style="flex:1;height:1px;background:#e2e8f0;"></div>
            </div>`;
        }

        categories.forEach(cat => {
            const favIconFill = cat.es_favorita ? 'currentColor' : 'none';
            const favIconColor = cat.es_favorita ? '#f43f5e' : '#cbd5e1';
            const favActiveClass = cat.es_favorita ? 'picker-cat-fav-btn--active' : '';
            const tipoLower = cat.tipo ? cat.tipo.toLowerCase() : 'default';
            const mainIcon = cat.tipo === 'INGRESO' ? 'trending-up' : (cat.tipo === 'EGRESO' ? 'trending-down' : 'piggy-bank');
            
            out += `
            <button type="button" class="picker-cat-card picker-cat-card--${tipoLower}" data-id="${cat.id}" data-nombre="${cat.nombre}" data-tipo="${cat.tipo}">
              <div class="picker-cat-icon">
                <i data-lucide="${mainIcon}" style="width:18px;height:18px;"></i>
              </div>
              <span class="picker-cat-nombre">${cat.nombre}</span>
              <div class="picker-cat-fav-btn ${favActiveClass}" data-id="${cat.id}" style="color:${favIconColor};">
                <i data-lucide="heart" fill="${favIconFill}" style="width:16px;height:16px;"></i>
              </div>
            </button>
            `;
        });

        return out;
    }
};

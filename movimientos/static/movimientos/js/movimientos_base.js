'use strict';
/**
 * GestorMovimientos — Clase base para Ingresos y Egresos.
 * Encapsula CRUD, modales, picker, buscador, paginación y reportes.
 */
class GestorMovimientos {
  constructor(config) {
    this.tipo        = config.tipo;          // 'INGRESO' | 'EGRESO'
    this.tipoLabel   = config.tipoLabel;     // 'ingreso' | 'egreso'
    this.color       = config.color;         // '#10b981' | '#e11d48'
    this.montoClass  = config.montoClass;    // 'monto--ingreso' | 'monto--egreso'
    this.dpAcento    = config.dpAcento || {};
    this.onPostSave  = config.onPostSave || null;

    this.movimientoEditandoId   = null;
    this.movimientoEliminandoId = null;
    this.categoriaActualId      = null;
    this.paginaActual           = 1;
    this.guardandoEnCurso       = false;
    this.debounceTimer          = null;
    this.formatoReporte         = 'csv';
    this.dpDesde = null;
    this.dpHasta = null;
    this.dpFecha = null;

    this.modalMovimiento    = document.getElementById('modal-movimiento');
    this.modalRegistros     = document.getElementById('modal-registros');
    this.modalConfirmar     = document.getElementById('modal-confirmar-eliminar');
    this.modalReporte       = document.getElementById('modal-reporte');
    this.formMovimiento     = document.getElementById('form-movimiento');
    this.tablaRegistrosBody = document.getElementById('tabla-registros-body');
    this.btnGuardar         = document.getElementById('btn-guardar');

    this.URL_EXPORTAR = { csv: URL_EXPORTAR_CSV, excel: URL_EXPORTAR_EXCEL, pdf: URL_EXPORTAR_PDF };
    this.LABEL_FORMATO = { csv: 'CSV', excel: 'Excel (.xlsx)', pdf: 'PDF' };

    this._bindAll();
    this._initProgress();
    this._initPicker();
    this._initBuscador();
    this._initReportes();
    this._initFormateoMonto();
    this._initDatepickerFecha();
    
    // Ajustar tamaños de fuente inicialmente
    setTimeout(() => this._ajustarTamanoTextos(), 50);
  }

  /* ── Auto-ajustar Textos Largos ── */
  _ajustarTamanoTextos() {
    const total = document.querySelector('.hero-total__value');
    if (total) {
      const len = total.textContent.trim().length;
      total.style.fontSize = len > 12 ? '1.5rem' : (len > 9 ? '1.9rem' : '');
    }
    document.querySelectorAll('.hero-stat__value, .categoria-card__monto').forEach(el => {
      const len = el.textContent.trim().length;
      el.style.fontSize = len > 12 ? '0.95rem' : (len > 9 ? '1.15rem' : '');
    });
  }

  /* ── Toast ── */
  mostrarToast(msg, tipo = 'ok') {
    const t = document.createElement('div');
    t.className = `toast toast--${tipo}`;
    t.textContent = msg;
    document.getElementById('toast-container').appendChild(t);
    setTimeout(() => t.remove(), 3200);
  }

  /* ── Errores ── */
  limpiarErrores() {
    document.querySelectorAll('.form-error').forEach(el => el.textContent = '');
    document.querySelectorAll('.form-control').forEach(el => el.style.borderColor = '');
  }
  mostrarErrores(errors) {
    Object.entries(errors).forEach(([campo, msgs]) => {
      const el = document.getElementById(`error-${campo}`);
      if (el) el.textContent = Array.isArray(msgs) ? msgs[0] : msgs;
      const inp = document.querySelector(`[name="${campo}"]`);
      if (inp) inp.style.borderColor = '#ef4444';
    });
  }

  /* ── Modal CRUD ── */
  abrirModalNuevo() {
    this.movimientoEditandoId = null;
    document.getElementById('modal-titulo').textContent = `Nuevo ${this.tipoLabel}`;
    this.formMovimiento.reset();
    if (this.dpFecha) this.dpFecha.limpiar();
    this.limpiarErrores();
    this.modalRegistros.setAttribute('hidden', '');
    this.modalMovimiento.removeAttribute('hidden');
    this._resetPicker();
    this._renderChipsCategorias();
    this._setFechaRapida('hoy');
  }

  abrirModalEditar(id, descripcion, monto, fechaRaw, categoriaId) {
    this.movimientoEditandoId = id;
    document.getElementById('modal-titulo').textContent = `Editar ${this.tipoLabel}`;
    this.modalRegistros.setAttribute('hidden', '');
    this.modalMovimiento.removeAttribute('hidden');
    document.getElementById('campo-descripcion').value = descripcion;
    if (this.dpFecha && fechaRaw) {
      this.dpFecha.setValor(fechaRaw);
    } else if (this.dpFecha) {
      this.dpFecha.limpiar();
    }
    document.getElementById('campo-categoria').value = categoriaId;
    const montoInput = document.getElementById('campo-monto');
    montoInput.value = this._formatearNumero(monto);
    montoInput.dataset.raw = monto;
    this.limpiarErrores();
    this._renderChipsCategorias();
    this._syncPickerLabel(categoriaId);
    const hoy = this._isoDesdeHoy(0);
    const ayer = this._isoDesdeHoy(-1);
    if (!fechaRaw || fechaRaw === hoy) this._setFechaRapida('hoy');
    else if (fechaRaw === ayer) this._setFechaRapida('ayer');
    else this._setFechaRapida('otra', fechaRaw);
  }

  cerrarModalMovimiento() {
    this.modalMovimiento.setAttribute('hidden', '');
    this.formMovimiento.reset();
    this.limpiarErrores();
    if (this.categoriaActualId) this.modalRegistros.removeAttribute('hidden');
    this._resetPicker();
  }

  /* ── Confirmar eliminar ── */
  abrirModalConfirmar(id) {
    this.movimientoEliminandoId = id;
    this.modalConfirmar.removeAttribute('hidden');
  }
  cerrarModalConfirmar() {
    this.modalConfirmar.setAttribute('hidden', '');
  }

  /* ── Grid ── */
  async actualizarGrid() {
    try {
      const selectMes = document.getElementById('select-mes');
      const selectAnio = document.getElementById('select-anio');
      let url = `${URL_RESUMEN}?tipo=${this.tipo}`;
      if (selectMes && selectAnio) {
          url += `&mes=${selectMes.value}&anio=${selectAnio.value}`;
      }
      
      const res = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      const data = await res.json();
      if (!data.ok) return;

      const heroValue = document.querySelector('.hero-total__value');
      if (heroValue) heroValue.textContent = `$${parseInt(data.total_mes).toLocaleString('es-CO')}`;
      const heroStats = document.querySelectorAll('.hero-stat__value');
      if (heroStats[0]) heroStats[0].textContent = data.cantidad_mes;
      if (heroStats[1]) heroStats[1].textContent = data.categorias.length;
      if (heroStats[2]) heroStats[2].textContent = `$${parseInt(data.promedio_mes).toLocaleString('es-CO')}`;

      const grid = document.getElementById('grid-categorias');
      if (!grid) return;

      if (data.categorias.length === 0) {
        grid.innerHTML = `<div class="grid-empty">Sin ${this.tipoLabel}s registrados este mes</div>`;
        return;
      }

      // Misma estructura que la card del template (ver static/css/gastu_card.css)
      const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
      grid.innerHTML = data.categorias.map(cat => `
        <div class="categoria-card" tabindex="0"
             data-categoria-id="${cat.id}"
             data-search-text="${esc(cat.nombre.toLowerCase())}"
             data-icono="${esc(cat.icono || 'tag')}"
             data-activo="${cat.activo ? 'true' : 'false'}">
          <div class="categoria-card__header">
            <div class="categoria-card__icon"><i data-lucide="${esc(cat.icono || 'tag')}"></i></div>
            <div class="categoria-card__titulo">
              <p class="categoria-card__nombre">
                ${esc(cat.nombre)}
                ${!cat.activo ? '<span class="badge-inactiva">Inactiva</span>' : ''}
              </p>
              <p class="categoria-card__cantidad">${cat.cantidad} registro${cat.cantidad !== 1 ? 's' : ''} · último ${esc(cat.ultimo_corto)}</p>
            </div>
            <span class="categoria-card__pct">${cat.porcentaje}%</span>
          </div>
          <p class="categoria-card__monto font-display">$${Math.round(Number(cat.total)).toLocaleString('es-CO')}</p>
          <div class="progress-bar">
            <div class="progress-bar__fill" data-porcentaje="${cat.porcentaje}"></div>
          </div>
        </div>`).join('');

      document.querySelectorAll('.progress-bar__fill').forEach(el => {
        el.style.width = (parseFloat(el.dataset.porcentaje) || 0) + '%';
      });
      this.bindearCards();
      lucide.createIcons();
      this._ajustarTamanoTextos();
    } catch (e) {
      console.error('actualizarGrid error:', e);
    }
  }

  /* ── Submit ── */
  async _handleSubmit(e) {
    e.preventDefault();
    if (this.guardandoEnCurso) return;
    this.guardandoEnCurso = true;
    this.btnGuardar.disabled = true;
    this.btnGuardar.textContent = 'Guardando...';
    this.limpiarErrores();
    const catGuardada = document.getElementById('campo-categoria').value;
    const url = this.movimientoEditandoId
      ? `${URL_EDITAR}${this.movimientoEditandoId}/`
      : URL_GUARDAR;

    try {
      const formData = new FormData(this.formMovimiento);
      const montoInput = document.getElementById('campo-monto');
      if (montoInput.dataset.raw) formData.set('monto', montoInput.dataset.raw);
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': CSRF_TOKEN },
        body: formData,
      });
      const data = await res.json();

      if (data.ok) {
        const wasEditing = this.movimientoEditandoId;
        this.cerrarModalMovimiento();
        this.mostrarToast(wasEditing ? `${this.tipoLabel.charAt(0).toUpperCase()+this.tipoLabel.slice(1)} actualizado.` : `${this.tipoLabel.charAt(0).toUpperCase()+this.tipoLabel.slice(1)} registrado.`, 'ok');
        await this.actualizarGrid();
        if (this.categoriaActualId) this.cargarRegistros(this.categoriaActualId, this.paginaActual);
        if (this.onPostSave && catGuardada) this.onPostSave(catGuardada);
      } else {
        this.mostrarErrores(data.errors || {});
        this.mostrarToast('Revisa los campos del formulario.', 'error');
      }
    } catch (e) {
      this.mostrarToast('Error de conexión. Intenta de nuevo.', 'error');
    } finally {
      this.guardandoEnCurso = false;
      this.btnGuardar.disabled = false;
      this.btnGuardar.textContent = 'Guardar';
    }
  }

  /* ── Eliminar ── */
  async ejecutarEliminar(id) {
    try {
      const res = await fetch(`${URL_ELIMINAR}${id}/`, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': CSRF_TOKEN },
      });
      const data = await res.json();
      if (data.ok) {
        this.mostrarToast(`${this.tipoLabel.charAt(0).toUpperCase()+this.tipoLabel.slice(1)} eliminado.`, 'ok');
        await this.actualizarGrid();
        const filasRestantes = this.tablaRegistrosBody.querySelectorAll('tr[data-id]').length;
        if (filasRestantes <= 1) {
          this.modalRegistros.setAttribute('hidden', '');
          this.categoriaActualId = null;
        } else {
          this.cargarRegistros(this.categoriaActualId, this.paginaActual);
        }
      } else {
        const errorMsg = data.error || 'No se pudo eliminar.';
        this.mostrarToast(errorMsg, 'error');
      }
    } catch (e) {
      this.mostrarToast('Error de conexión. Intenta de nuevo.', 'error');
    }
  }

  /* ── Cards ── */
  bindearCards() {
    document.querySelectorAll('.categoria-card').forEach(card => {
      card.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); card.click(); }
      });
      card.addEventListener('click', () => {
        this.categoriaActualId = card.dataset.categoriaId;
        this.paginaActual = 1;
        document.getElementById('modal-registros-titulo').textContent =
          card.querySelector('.categoria-card__nombre').textContent.replace('Inactiva', '').trim();
          
        const btnNuevo = document.getElementById('btn-nuevo-desde-registros');
        const tooltipNuevo = document.getElementById('tooltip-nuevo');
        if (btnNuevo) {
          const esActiva = card.dataset.activo === 'true';
          if (!esActiva) {
            btnNuevo.disabled = true;
            btnNuevo.style.opacity = '0.5';
            btnNuevo.style.cursor = 'not-allowed';
            if (tooltipNuevo) tooltipNuevo.style.display = 'block';
          } else {
            btnNuevo.disabled = false;
            btnNuevo.style.opacity = '1';
            btnNuevo.style.cursor = 'pointer';
            if (tooltipNuevo) tooltipNuevo.style.display = 'none';
          }
        }
        
        this.modalRegistros.removeAttribute('hidden');
        this.cargarRegistros(this.categoriaActualId, this.paginaActual);
      });
    });
  }

  /* ── Registros ── */
  async cargarRegistros(categoriaId, pagina) {
    this.tablaRegistrosBody.innerHTML = '<tr><td colspan="4" class="table-empty">Cargando...</td></tr>';
    try {
      const res = await fetch(
        `${URL_REGISTROS}?categoria=${categoriaId}&page=${pagina}`,
        { headers: { 'X-Requested-With': 'XMLHttpRequest' } }
      );
      if (!res.ok) {
        const texto = await res.text();
        console.error(`[registros] HTTP ${res.status}:`, texto);
        this.tablaRegistrosBody.innerHTML = `<tr><td colspan="4" class="table-empty">Error ${res.status}</td></tr>`;
        return;
      }
      const data = await res.json();
      const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

      this.tablaRegistrosBody.innerHTML = data.registros.length
        ? data.registros.map(r => `
            <tr data-id="${esc(r.id)}">
              <td>${esc(r.descripcion)}</td>
              <td class="text-muted">${esc(r.fecha)}</td>
              <td><span class="monto ${this.montoClass}">${esc(r.monto_fmt)}</span></td>
              <td class="table-actions">
                <button class="btn-icon btn-editar"
                        data-id="${esc(r.id)}"
                        data-descripcion="${esc(r.descripcion)}"
                        data-monto="${esc(r.monto)}"
                        data-fecha="${esc(r.fecha_raw)}"
                        data-categoria="${esc(r.categoria_id)}"
                        title="Editar"><i data-lucide="pencil"></i></button>
                <button class="btn-icon btn-eliminar" data-id="${esc(r.id)}" title="Eliminar">
                  <i data-lucide="trash-2"></i>
                </button>
              </td>
            </tr>`).join('')
        : '<tr><td colspan="4" class="table-empty">Sin registros en esta categoría</td></tr>';

      lucide.createIcons();

      document.getElementById('pagination-info').textContent =
        data.total > 0 ? `Mostrando ${data.desde}–${data.hasta} de ${data.total}` : '';
      document.getElementById('pagination-pagina').textContent =
        data.total_paginas > 1 ? `${pagina} / ${data.total_paginas}` : '';
      document.getElementById('modal-registros-subtitulo').textContent =
        `${data.total} registro${data.total !== 1 ? 's' : ''}`;
      document.getElementById('btn-pag-anterior').disabled = pagina <= 1;
      document.getElementById('btn-pag-siguiente').disabled = pagina >= data.total_paginas;

      this.tablaRegistrosBody.querySelectorAll('.btn-editar').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          this.abrirModalEditar(btn.dataset.id, btn.dataset.descripcion, btn.dataset.monto, btn.dataset.fecha, btn.dataset.categoria);
        });
      });
      this.tablaRegistrosBody.querySelectorAll('.btn-eliminar').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const id = btn.dataset.id;
          if (window.GastuAlerts) {
              window.GastuAlerts.confirmar(
                  '¿Eliminar movimiento?',
                  'Esta acción no se puede deshacer.',
                  'Sí, eliminar'
              ).then((isConfirmed) => {
                  if (isConfirmed) {
                      this.ejecutarEliminar(id);
                  }
              });
          } else {
              this.abrirModalConfirmar(id);
          }
        });
      });
    } catch (e) {
      this.tablaRegistrosBody.innerHTML = '<tr><td colspan="4" class="table-empty">Error al cargar registros.</td></tr>';
    }
  }

  /* ── Buscador ── */
  _initBuscador() {
    const self = this;
    document.getElementById('buscador').addEventListener('input', (e) => {
      const q = e.target.value.trim();
      clearTimeout(self.debounceTimer);
      if (!q) {
        document.querySelectorAll('.categoria-card').forEach(card => {
          card.style.display = '';
          card.style.outline = '';
        });
        return;
      }
      self.debounceTimer = setTimeout(async () => {
        const qLower = q.toLowerCase();
        document.querySelectorAll('.categoria-card').forEach(card => {
          card.style.display = card.dataset.searchText.includes(qLower) ? '' : 'none';
          card.style.outline = '';
        });
        try {
          const res = await fetch(
            `${URL_BUSCAR}?q=${encodeURIComponent(q)}&tipo=${self.tipo}`,
            { headers: { 'X-Requested-With': 'XMLHttpRequest' } }
          );
          const data = await res.json();
          if (!data.ok) return;
          const ids = new Set(data.categoria_ids.map(String));
          if (ids.size > 0) {
            document.querySelectorAll('.categoria-card').forEach(card => {
              const tiene = ids.has(card.dataset.categoriaId);
              card.style.display = tiene ? '' : 'none';
              card.style.outline = tiene ? `2px solid ${self.color}` : '';
            });
          }
        } catch (err) { console.error('buscar error:', err); }
      }, 300);
    });
  }

  /* ── Picker ── */
  _initPicker() {
    const modalPicker  = document.getElementById('modal-picker-cat');
    const btnPicker    = document.getElementById('btn-picker-categoria');
    const pickerLabel  = document.getElementById('picker-cat-label');
    const inputCat     = document.getElementById('campo-categoria');
    const buscadorPick = document.getElementById('picker-buscador');
    if (!modalPicker || !btnPicker) return;
    const self = this;

    this._pickerEls = { modalPicker, btnPicker, pickerLabel, inputCat, buscadorPick };

    if (window.CategoryPicker) {
      CategoryPicker.init({
        containerId: 'picker-grid',
        tipo: this.tipo.toUpperCase(),
        context: 'movimientos',
        onSelect: (cat) => {
          self._setCategoria(cat.id, cat.nombre, cat.icono);
          cerrarPicker();
        }
      });
    }

    function abrirPicker() {
      if (buscadorPick) buscadorPick.value = '';
      if (window.CategoryPicker) CategoryPicker.filter('');
      
      const selId = inputCat.value;
      const selLabel = document.getElementById('picker-seleccionado-label');
      if (selLabel) {
        if (selId && window.CategoryPicker) {
          const cat = window.CategoryPicker.allCategories.find(c => c.id == selId);
          selLabel.textContent = cat ? `Seleccionado: ${cat.nombre}` : '';
        } else {
          selLabel.textContent = '';
        }
      }
      
      modalPicker.removeAttribute('hidden');
      setTimeout(() => buscadorPick && buscadorPick.focus(), 50);
    }
    
    function cerrarPicker() { modalPicker.setAttribute('hidden', ''); }

    btnPicker.addEventListener('click', (e) => { e.preventDefault(); abrirPicker(); });
    document.getElementById('btn-cerrar-picker')?.addEventListener('click', cerrarPicker);
    document.getElementById('btn-cancelar-picker')?.addEventListener('click', cerrarPicker);
    modalPicker.addEventListener('click', (e) => { if (e.target === modalPicker) cerrarPicker(); });
    
    if (buscadorPick) {
      buscadorPick.addEventListener('input', (e) => {
        if (window.CategoryPicker) CategoryPicker.filter(e.target.value);
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !modalPicker.hasAttribute('hidden')) { e.stopImmediatePropagation(); cerrarPicker(); }
    }, true);

    /* Nuevo desde registros */
    document.getElementById('btn-nuevo-desde-registros')?.addEventListener('click', () => {
      const catId = self.categoriaActualId;
      const catNombre = document.getElementById('modal-registros-titulo').textContent;
      self.abrirModalNuevo();
      if (catId) self._setCategoria(catId, catNombre, self._iconoDe(catId));
    });
  }

  _resetPicker() {
    if (!this._pickerEls) return;
    this._setCategoria('', 'Seleccionar categoría', null);
  }
  _syncPickerLabel(categoriaId) {
    if (!this._pickerEls) return;
    const cat = window.CategoryPicker?.allCategories?.find(c => c.id == categoriaId);
    const card = document.querySelector(`.categoria-card[data-categoria-id="${categoriaId}"]`);
    const nombre = cat?.nombre
      || card?.querySelector('.categoria-card__nombre')?.textContent.replace('Inactiva', '').trim()
      || document.querySelector(`.picker-cat-card[data-id="${categoriaId}"]`)?.dataset.nombre;
    if (nombre) this._setCategoria(categoriaId, nombre, this._iconoDe(categoriaId));
  }

  /** Icono de una categoria segun el picker o la card de la pagina. */
  _iconoDe(categoriaId) {
    const cat = window.CategoryPicker?.allCategories?.find(c => c.id == categoriaId);
    if (cat?.icono) return cat.icono;
    return document.querySelector(`.categoria-card[data-categoria-id="${categoriaId}"]`)?.dataset.icono || null;
  }

  /** Fija la categoria elegida: valor, texto, icono del boton y de la cabecera, y atajo activo. */
  _setCategoria(id, nombre, icono) {
    if (!this._pickerEls) return;
    const { inputCat, pickerLabel, btnPicker } = this._pickerEls;
    inputCat.value = id || '';
    pickerLabel.textContent = nombre;
    pickerLabel.style.color = id ? 'var(--slate-900)' : '';
    btnPicker.classList.toggle('has-value', !!id);

    const iconoPicker = document.getElementById('picker-cat-icono');
    if (iconoPicker) iconoPicker.innerHTML = `<i data-lucide="${id && icono ? icono : 'tag'}"></i>`;
    const badge = document.getElementById('modal-tipo-badge');
    if (badge) {
      if (this._badgeOriginal === undefined) this._badgeOriginal = badge.innerHTML;
      badge.innerHTML = id && icono ? `<i data-lucide="${icono}"></i>` : this._badgeOriginal;
    }
    document.querySelectorAll('#mov-chips-categorias .mov-chip').forEach(chip => {
      chip.classList.toggle('is-activo', chip.dataset.id == id);
    });
    if (window.lucide) lucide.createIcons();
  }

  /** Atajos con las categorias que mas usa el usuario (las primeras cards de la pagina). */
  _renderChipsCategorias() {
    const cont = document.getElementById('mov-chips-categorias');
    if (!cont) return;
    const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const cards = [...document.querySelectorAll('#grid-categorias .categoria-card[data-activo="true"]')].slice(0, 4);
    cont.innerHTML = cards.map(card => {
      const nombre = card.querySelector('.categoria-card__nombre').textContent.trim();
      return `<button type="button" class="mov-chip" data-id="${esc(card.dataset.categoriaId)}" data-nombre="${esc(nombre)}" data-icono="${esc(card.dataset.icono || 'tag')}">
        <i data-lucide="${esc(card.dataset.icono || 'tag')}"></i>${esc(nombre)}</button>`;
    }).join('');
    cont.querySelectorAll('.mov-chip').forEach(chip => {
      chip.addEventListener('click', () => this._setCategoria(chip.dataset.id, chip.dataset.nombre, chip.dataset.icono));
    });
    if (window.lucide) lucide.createIcons();
  }

  _isoDesdeHoy(dias) {
    const f = new Date();
    f.setDate(f.getDate() + dias);
    return `${f.getFullYear()}-${String(f.getMonth() + 1).padStart(2, '0')}-${String(f.getDate()).padStart(2, '0')}`;
  }

  /** Atajos de fecha: hoy, ayer u otra fecha (muestra el calendario). */
  _setFechaRapida(modo, fechaIso) {
    const cont = document.getElementById('dp-fecha-container');
    document.querySelectorAll('#mov-chips-fecha .mov-chip').forEach(chip => {
      chip.classList.toggle('is-activo', chip.dataset.fecha === modo);
    });
    if (cont) cont.hidden = modo !== 'otra';
    if (!this.dpFecha) return;
    if (modo === 'hoy') this.dpFecha.setValor(this._isoDesdeHoy(0));
    else if (modo === 'ayer') this.dpFecha.setValor(this._isoDesdeHoy(-1));
    else if (fechaIso) this.dpFecha.setValor(fechaIso);
  }

  /* ── Datepicker Fecha (formulario CRUD) ── */
  _initDatepickerFecha() {
    const inputFecha = document.getElementById('campo-fecha');
    const container  = document.getElementById('dp-fecha-container');
    if (!inputFecha || !container) return;
    this.dpFecha = new MiniDatepicker(inputFecha, this.dpAcento);
    container.appendChild(this.dpFecha.wrapper);
    document.querySelectorAll('#mov-chips-fecha .mov-chip').forEach(chip => {
      chip.addEventListener('click', () => this._setFechaRapida(chip.dataset.fecha));
    });
  }

  /* ── Reportes ── */
  _initReportes() {
    const self = this;
    function _initDP() {
      if (!self.dpDesde) {
        const iD = document.getElementById('dp-input-desde');
        const iH = document.getElementById('dp-input-hasta');
        if (!iD || !iH) return;
        self.dpDesde = new MiniDatepicker(iD, self.dpAcento);
        self.dpHasta = new MiniDatepicker(iH, self.dpAcento);
        iD.parentNode.appendChild(self.dpDesde.wrapper);
        iH.parentNode.appendChild(self.dpHasta.wrapper);
      }
    }
    function abrirModalReporte(formato) {
      self.formatoReporte = formato;
      document.getElementById('modal-reporte-formato-label').textContent = 'Formato: ' + self.LABEL_FORMATO[formato];
      _initDP();
      const hoy = new Date();
      const p = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
      self.dpDesde.setValor(p.toISOString().split('T')[0]);
      self.dpHasta.setValor(hoy.toISOString().split('T')[0]);
      cargarCats();
      self.modalReporte.removeAttribute('hidden');
      lucide.createIcons();
    }
    function cargarCats() {
      const cont = document.getElementById('reporte-categorias');
      const cards = document.querySelectorAll('.categoria-card');
      if (!cards.length) { cont.innerHTML = '<span style="font-size:.78rem;color:var(--slate-500);">Sin categorías con actividad este mes.</span>'; updateCount(); return; }
      cont.innerHTML = Array.from(cards).map(c => {
        const id = c.dataset.categoriaId, n = c.querySelector('.categoria-card__nombre').textContent;
        return `<label style="display:inline-flex;align-items:center;gap:.3rem;font-size:.78rem;cursor:pointer;padding:.25rem .5rem;border-radius:.375rem;border:1px solid var(--border);background:#fff;white-space:nowrap;"><input type="checkbox" value="${id}" class="cat-check" checked style="accent-color:${self.color};"> ${n}</label>`;
      }).join('');
      updateCount();
    }
    function updateCount() {
      const t = document.querySelectorAll('.cat-check').length, m = document.querySelectorAll('.cat-check:checked').length;
      const el = document.getElementById('reporte-count');
      if (el) el.textContent = `${m} de ${t} categoría${t !== 1 ? 's' : ''} seleccionada${t !== 1 ? 's' : ''}`;
    }
    function cerrarModalReporte() { self.modalReporte.setAttribute('hidden', ''); }

    document.getElementById('reporte-categorias').addEventListener('change', updateCount);
    document.getElementById('btn-todas-cats').addEventListener('click', () => { document.querySelectorAll('.cat-check').forEach(c => c.checked = true); updateCount(); });
    document.getElementById('btn-ninguna-cat').addEventListener('click', () => { document.querySelectorAll('.cat-check').forEach(c => c.checked = false); updateCount(); });
    document.getElementById('btn-descargar-reporte').addEventListener('click', () => {
      const desde = self.dpDesde ? self.dpDesde.getValor() : '', hasta = self.dpHasta ? self.dpHasta.getValor() : '';
      const checkedCats = document.querySelectorAll('.cat-check:checked');
      if (checkedCats.length === 0) {
          if (window.GastuAlerts) window.GastuAlerts.error('Sin datos', 'No hay movimientos para exportar.');
          return;
      }
      const catIds = Array.from(checkedCats).map(c => c.value).join(',');
      const params = new URLSearchParams({ tipo: self.tipo, fecha_desde: desde, fecha_hasta: hasta });
      if (catIds) params.set('categorias', catIds);
      window.location.href = `${self.URL_EXPORTAR[self.formatoReporte]}?${params.toString()}`;
      cerrarModalReporte();
    });
    document.getElementById('btn-cerrar-reporte').addEventListener('click', cerrarModalReporte);
    document.getElementById('btn-cancelar-reporte').addEventListener('click', cerrarModalReporte);
    self.modalReporte.addEventListener('click', (e) => { if (e.target === self.modalReporte) cerrarModalReporte(); });
    document.querySelector('.btn-export--pdf').addEventListener('click', () => abrirModalReporte('pdf'));
    document.querySelector('.btn-export--excel').addEventListener('click', () => abrirModalReporte('excel'));
    document.querySelector('.btn-export--csv').addEventListener('click', () => abrirModalReporte('csv'));
  }

  /* ── Formateo de monto en tiempo real ── */
  _formatearNumero(raw) {
    if (!raw) return '';
    const entero = String(raw).split('.')[0].replace(/\D/g, '');
    if (!entero) return '';
    return entero.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  _initFormateoMonto() {
    const input = document.getElementById('campo-monto');
    input.addEventListener('input', function () {
      const el = this;
      const oldLen = el.value.length;
      const start = el.selectionStart;
      let digitCount = 0;
      for (let i = 0; i < start; i++) {
        if (/\d/.test(el.value[i])) digitCount++;
      }
      const digitos = el.value.replace(/\D/g, '');
      if (!digitos) { el.dataset.raw = ''; el.value = ''; return; }
      const formatted = digitos.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
      el.dataset.raw = digitos;
      el.value = formatted;
      let newPos = formatted.length;
      if (start < oldLen) {
        let dc = 0;
        for (let i = 0; i < formatted.length; i++) {
          if (dc >= digitCount) { newPos = i; break; }
          if (/\d/.test(formatted[i])) dc++;
          newPos = i + 1;
        }
      }
      el.setSelectionRange(newPos, newPos);
    });
  }

  /* ── Progress bars init ── */
  _initProgress() {
    document.querySelectorAll('.progress-bar__fill').forEach(el => {
      el.style.width = (parseFloat(el.dataset.porcentaje) || 0) + '%';
    });
    this.bindearCards();
    lucide.createIcons();
  }

  /* ── Bindear todos los eventos ── */
  _bindAll() {
    const self = this;
    // Form submit
    this.formMovimiento.addEventListener('submit', (e) => self._handleSubmit(e));
    // Botón nuevo
    document.getElementById('btn-nuevo').addEventListener('click', () => self.abrirModalNuevo());
    // Cerrar modales
    document.getElementById('btn-cerrar-modal').addEventListener('click', () => self.cerrarModalMovimiento());
    document.getElementById('btn-cancelar-modal').addEventListener('click', () => self.cerrarModalMovimiento());
    document.getElementById('btn-cerrar-registros').addEventListener('click', () => { self.modalRegistros.setAttribute('hidden', ''); self.categoriaActualId = null; });
    this.modalMovimiento.addEventListener('click', (e) => { if (e.target === self.modalMovimiento) self.cerrarModalMovimiento(); });
    this.modalRegistros.addEventListener('click', (e) => { if (e.target === self.modalRegistros) { self.modalRegistros.setAttribute('hidden', ''); self.categoriaActualId = null; } });
    // Confirmar eliminar
    document.getElementById('btn-cerrar-confirmar').addEventListener('click', () => { self.movimientoEliminandoId = null; self.cerrarModalConfirmar(); });
    document.getElementById('btn-cancelar-eliminar').addEventListener('click', () => { self.movimientoEliminandoId = null; self.cerrarModalConfirmar(); });
    this.modalConfirmar.addEventListener('click', (e) => { if (e.target === self.modalConfirmar) { self.movimientoEliminandoId = null; self.cerrarModalConfirmar(); } });
    document.getElementById('btn-confirmar-eliminar').addEventListener('click', async () => {
      const id = self.movimientoEliminandoId;
      if (!id) return;
      self.movimientoEliminandoId = null;
      self.cerrarModalConfirmar();
      await self.ejecutarEliminar(id);
    });
    // Paginación
    document.getElementById('btn-pag-anterior').addEventListener('click', () => { if (self.paginaActual > 1) self.cargarRegistros(self.categoriaActualId, --self.paginaActual); });
    document.getElementById('btn-pag-siguiente').addEventListener('click', () => { self.cargarRegistros(self.categoriaActualId, ++self.paginaActual); });
    // Escape
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      if (!self.modalConfirmar.hasAttribute('hidden')) { self.movimientoEliminandoId = null; self.cerrarModalConfirmar(); }
      else if (!self.modalMovimiento.hasAttribute('hidden')) { self.cerrarModalMovimiento(); }
      else if (!self.modalRegistros.hasAttribute('hidden')) { self.modalRegistros.setAttribute('hidden', ''); self.categoriaActualId = null; }
    });
  }
}

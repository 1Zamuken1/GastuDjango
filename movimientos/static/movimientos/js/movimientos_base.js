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
    this.limpiarErrores();
    this.modalRegistros.setAttribute('hidden', '');
    this.modalMovimiento.removeAttribute('hidden');
    this._resetPicker();
  }

  abrirModalEditar(id, descripcion, monto, fechaRaw, categoriaId) {
    this.movimientoEditandoId = id;
    document.getElementById('modal-titulo').textContent = `Editar ${this.tipoLabel}`;
    this.modalRegistros.setAttribute('hidden', '');
    this.modalMovimiento.removeAttribute('hidden');
    document.getElementById('campo-descripcion').value = descripcion;
    document.getElementById('campo-monto').value = monto;
    document.getElementById('campo-categoria').value = categoriaId;
    this.limpiarErrores();
    this._syncPickerLabel(categoriaId);
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
      const res = await fetch(`${URL_RESUMEN}?tipo=${this.tipo}`, {
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

      grid.innerHTML = data.categorias.map(cat => `
        <div class="categoria-card"
             data-categoria-id="${cat.id}"
             data-search-text="${cat.nombre.toLowerCase()}"
             data-activo="${cat.activo ? 'true' : 'false'}">
          <div class="categoria-card__header">
            <div>
              <p class="categoria-card__nombre">
                ${cat.nombre}
                ${!cat.activo ? '<span style="font-size: 0.65rem; background: #fee2e2; color: #ef4444; padding: 2px 6px; border-radius: 4px; margin-left: 4px; font-weight: 700; vertical-align: middle;">Inactiva</span>' : ''}
              </p>
              <p class="categoria-card__cantidad">${cat.cantidad} registro${cat.cantidad !== 1 ? 's' : ''}</p>
            </div>
            <div class="categoria-card__icon"><i data-lucide="folder"></i></div>
          </div>
          <p class="categoria-card__monto font-display">${cat.total_fmt}</p>
          <div style="display:flex;align-items:center;gap:.5rem;margin:.5rem 0 .25rem;">
            <div class="progress-bar" style="flex:1;margin:0;">
              <div class="progress-bar__fill" data-porcentaje="${cat.porcentaje}"></div>
            </div>
            <span style="font-size:.72rem;font-weight:700;color:${this.color};white-space:nowrap;min-width:2.5rem;text-align:right;">${cat.porcentaje}%</span>
          </div>
          <div class="categoria-card__footer">
            <i data-lucide="clock"></i> Último: ${cat.ultimo_registro}
          </div>
        </div>`).join('');

      document.querySelectorAll('.progress-bar__fill').forEach(el => {
        el.style.width = (parseFloat(el.dataset.porcentaje) || 0) + '%';
      });
      this.bindearCards();
      lucide.createIcons();
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
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': CSRF_TOKEN },
        body: new FormData(this.formMovimiento),
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
      card.addEventListener('click', () => {
        this.categoriaActualId = card.dataset.categoriaId;
        this.paginaActual = 1;
        document.getElementById('modal-registros-titulo').textContent =
          card.querySelector('.categoria-card__nombre').textContent.replace('Inactiva', '').trim();
          
        const btnNuevo = document.getElementById('btn-nuevo-desde-registros');
        if (btnNuevo) {
          const esActiva = card.dataset.activo === 'true';
          if (!esActiva) {
            btnNuevo.disabled = true;
            btnNuevo.style.opacity = '0.5';
            btnNuevo.title = 'Categoría inactiva. No permite nuevos registros.';
            btnNuevo.style.cursor = 'not-allowed';
          } else {
            btnNuevo.disabled = false;
            btnNuevo.style.opacity = '1';
            btnNuevo.title = '';
            btnNuevo.style.cursor = 'pointer';
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

      this.tablaRegistrosBody.innerHTML = data.registros.length
        ? data.registros.map(r => `
            <tr data-id="${r.id}">
              <td>${r.descripcion}</td>
              <td class="text-muted">${r.fecha}</td>
              <td><span class="monto ${this.montoClass}">${r.monto_fmt}</span></td>
              <td class="table-actions">
                <button class="btn-icon btn-editar"
                        data-id="${r.id}"
                        data-descripcion="${r.descripcion.replace(/"/g,'&quot;')}"
                        data-monto="${r.monto}"
                        data-fecha="${r.fecha_raw}"
                        data-categoria="${r.categoria_id}"
                        title="Editar"><i data-lucide="pencil"></i></button>
                <button class="btn-icon btn-eliminar" data-id="${r.id}" title="Eliminar">
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

    function abrirPicker() {
      buscadorPick.value = '';
      filtrarPicker('');
      const selId = inputCat.value;
      document.querySelectorAll('.picker-cat-card').forEach(c => c.classList.toggle('selected', c.dataset.id === selId));
      const selLabel = document.getElementById('picker-seleccionado-label');
      if (selLabel) {
        const sc = document.querySelector(`.picker-cat-card[data-id="${selId}"]`);
        selLabel.textContent = sc ? `Seleccionado: ${sc.dataset.nombre}` : '';
      }
      modalPicker.removeAttribute('hidden');
      lucide.createIcons();
      setTimeout(() => buscadorPick.focus(), 50);
    }
    function cerrarPicker() { modalPicker.setAttribute('hidden', ''); }
    function filtrarPicker(q) {
      const qL = q.toLowerCase().trim();
      document.querySelectorAll('.picker-cat-card').forEach(c => {
        c.style.display = c.dataset.nombre.toLowerCase().includes(qL) ? '' : 'none';
      });
    }
    function seleccionarCategoria(id, nombre) {
      inputCat.value = id;
      pickerLabel.textContent = nombre;
      pickerLabel.style.color = 'var(--slate-900)';
      btnPicker.style.borderColor = '';
      document.querySelectorAll('.picker-cat-card').forEach(c => c.classList.toggle('selected', c.dataset.id === id));
      cerrarPicker();
    }

    btnPicker.addEventListener('click', (e) => { e.stopPropagation(); abrirPicker(); });
    document.getElementById('btn-cerrar-picker').addEventListener('click', cerrarPicker);
    document.getElementById('btn-cancelar-picker').addEventListener('click', cerrarPicker);
    modalPicker.addEventListener('click', (e) => { if (e.target === modalPicker) cerrarPicker(); });
    document.getElementById('picker-grid').addEventListener('click', (e) => {
      const card = e.target.closest('.picker-cat-card');
      if (card) seleccionarCategoria(card.dataset.id, card.dataset.nombre);
    });
    buscadorPick.addEventListener('input', (e) => filtrarPicker(e.target.value));
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !modalPicker.hasAttribute('hidden')) { e.stopImmediatePropagation(); cerrarPicker(); }
    }, true);

    /* Nuevo desde registros */
    document.getElementById('btn-nuevo-desde-registros').addEventListener('click', () => {
      const catId = self.categoriaActualId;
      const catNombre = document.getElementById('modal-registros-titulo').textContent;
      self.abrirModalNuevo();
      if (inputCat && pickerLabel && catId) {
        inputCat.value = catId;
        pickerLabel.textContent = catNombre;
        pickerLabel.style.color = 'var(--slate-900)';
        document.querySelectorAll('.picker-cat-card').forEach(c => c.classList.toggle('selected', c.dataset.id === catId));
      }
    });
  }

  _resetPicker() {
    if (!this._pickerEls) return;
    this._pickerEls.inputCat.value = '';
    this._pickerEls.pickerLabel.textContent = 'Seleccionar categoría';
    this._pickerEls.pickerLabel.style.color = '';
  }
  _syncPickerLabel(categoriaId) {
    if (!this._pickerEls) return;
    const card = document.querySelector(`.picker-cat-card[data-id="${categoriaId}"]`);
    if (card) {
      this._pickerEls.pickerLabel.textContent = card.dataset.nombre;
      this._pickerEls.pickerLabel.style.color = 'var(--slate-900)';
    }
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

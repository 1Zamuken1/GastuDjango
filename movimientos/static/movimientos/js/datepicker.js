/**
 * MiniDatepicker
 * Datepicker ligero y estético integrado con el design system de GastuApp.
 * Soporta 3 vistas: calendario (días), selector de meses y selector de años.
 * Uso: new MiniDatepicker(inputEl, { onChange: (isoDate) => {} })
 */
'use strict';

class MiniDatepicker {
  constructor(inputEl, opciones = {}) {
    this.input    = inputEl;
    this.onChange  = opciones.onChange || null;
    this.acento   = opciones.acento   || 'ingreso';
    this.valor    = null;
    this.hoy      = new Date();
    this.vistaAno = this.hoy.getFullYear();
    this.vistaMes = this.hoy.getMonth();
    this.modo     = 'dias'; // 'dias' | 'meses' | 'anios'
    this.paginaAnio = Math.floor(this.hoy.getFullYear() / 12) * 12;

    this._construir();
    this._bindear();

    if (inputEl.value) this.setValor(inputEl.value);
  }

  /* ── Construcción del DOM ─────────────────────────── */
  _construir() {
    this.wrapper = document.createElement('div');
    this.wrapper.className = 'dp-wrapper';
    this.wrapper.dataset.acento = this.acento;

    this.display = document.createElement('button');
    this.display.type = 'button';
    this.display.className = 'dp-display';
    this.display.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <rect x="3" y="4" width="18" height="18" rx="2"/>
        <path d="M16 2v4M8 2v4M3 10h18"/>
      </svg>
      <span class="dp-display-text">Seleccionar fecha</span>`;

    this.panel = document.createElement('div');
    this.panel.className = 'dp-panel';
    this.panel.setAttribute('hidden', '');

    this.wrapper.appendChild(this.display);
    this.wrapper.appendChild(this.panel);

    // Reemplazar el input original con el wrapper
    this.input.style.display = 'none';
    this.input.parentNode.insertBefore(this.wrapper, this.input.nextSibling);
  }

  /* ── Constantes ──────────────────────────────────── */
  static get MESES() {
    return ['Ene','Feb','Mar','Abr','May','Jun',
            'Jul','Ago','Sep','Oct','Nov','Dic'];
  }
  static get MESES_FULL() {
    return ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
            'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
  }
  static get DIAS() {
    return ['Lu','Ma','Mi','Ju','Vi','Sa','Do'];
  }

  /* ── Render principal (despacha al modo activo) ──── */
  _renderPanel() {
    switch (this.modo) {
      case 'meses': this._renderMeses(); break;
      case 'anios': this._renderAnios(); break;
      default:      this._renderDias();  break;
    }
  }

  /* ── Vista de DÍAS (calendario) ──────────────────── */
  _renderDias() {
    const primerDia = new Date(this.vistaAno, this.vistaMes, 1);
    const totalDias = new Date(this.vistaAno, this.vistaMes + 1, 0).getDate();
    let offsetInicio = primerDia.getDay() - 1;
    if (offsetInicio < 0) offsetInicio = 6;

    const valorSel = this.valor
      ? `${this.valor.getFullYear()}-${this.valor.getMonth()}-${this.valor.getDate()}`
      : null;
    const hoyKey = `${this.hoy.getFullYear()}-${this.hoy.getMonth()}-${this.hoy.getDate()}`;

    let celdasHTML = MiniDatepicker.DIAS.map(d => `<span class="dp-dow">${d}</span>`).join('');

    for (let i = 0; i < offsetInicio; i++) {
      celdasHTML += `<span class="dp-day dp-day--vacio"></span>`;
    }
    for (let d = 1; d <= totalDias; d++) {
      const key = `${this.vistaAno}-${this.vistaMes}-${d}`;
      const esHoy = key === hoyKey;
      const esSel = valorSel && key === valorSel;
      celdasHTML += `<button type="button" class="dp-day${esHoy ? ' dp-day--hoy' : ''}${esSel ? ' dp-day--sel' : ''}"
                             data-d="${d}">${d}</button>`;
    }

    this.panel.innerHTML = `
      <div class="dp-header">
        <button type="button" class="dp-nav" data-nav="-1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <div class="dp-header-centro">
          <button type="button" class="dp-header-btn" data-cambio="meses">${MiniDatepicker.MESES_FULL[this.vistaMes]}</button>
          <button type="button" class="dp-header-btn" data-cambio="anios">${this.vistaAno}</button>
        </div>
        <button type="button" class="dp-nav" data-nav="1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
        </button>
      </div>
      <div class="dp-grid">${celdasHTML}</div>
      <div class="dp-footer">
        <button type="button" class="dp-btn-hoy">Hoy</button>
        <button type="button" class="dp-btn-limpiar">Limpiar</button>
      </div>`;
  }

  /* ── Vista de MESES (grilla 4×3) ─────────────────── */
  _renderMeses() {
    let celdasHTML = '';
    for (let m = 0; m < 12; m++) {
      const esActual = (m === this.hoy.getMonth() && this.vistaAno === this.hoy.getFullYear());
      const esSel    = (m === this.vistaMes);
      celdasHTML += `<button type="button" class="dp-celda${esActual ? ' dp-celda--hoy' : ''}${esSel ? ' dp-celda--sel' : ''}"
                             data-mes="${m}">${MiniDatepicker.MESES[m]}</button>`;
    }

    this.panel.innerHTML = `
      <div class="dp-header">
        <button type="button" class="dp-nav" data-nav-anio="-1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <button type="button" class="dp-header-btn dp-header-btn--titulo" data-cambio="anios">${this.vistaAno}</button>
        <button type="button" class="dp-nav" data-nav-anio="1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
        </button>
      </div>
      <div class="dp-grid-pick">${celdasHTML}</div>`;
  }

  /* ── Vista de AÑOS (grilla 4×3) ──────────────────── */
  _renderAnios() {
    const inicio = this.paginaAnio;
    let celdasHTML = '';
    for (let i = 0; i < 12; i++) {
      const y = inicio + i;
      const esActual = (y === this.hoy.getFullYear());
      const esSel    = (y === this.vistaAno);
      celdasHTML += `<button type="button" class="dp-celda${esActual ? ' dp-celda--hoy' : ''}${esSel ? ' dp-celda--sel' : ''}"
                             data-anio="${y}">${y}</button>`;
    }

    this.panel.innerHTML = `
      <div class="dp-header">
        <button type="button" class="dp-nav" data-nav-pagina="-1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <span class="dp-header-rango">${inicio} — ${inicio + 11}</span>
        <button type="button" class="dp-nav" data-nav-pagina="1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
        </button>
      </div>
      <div class="dp-grid-pick">${celdasHTML}</div>`;
  }

  /* ── Eventos ──────────────────────────────────────── */
  _bindear() {
    this.display.addEventListener('click', (e) => {
      e.stopPropagation();
      const abierto = !this.panel.hasAttribute('hidden');
      document.querySelectorAll('.dp-panel').forEach(p => {
          p.setAttribute('hidden', '');
          p.classList.remove('dp-panel--arriba');
        });
      if (!abierto) {
        this.modo = 'dias';
        this._renderPanel();
        this.panel.removeAttribute('hidden');

        requestAnimationFrame(() => {
          const displayRect = this.display.getBoundingClientRect();
          const panelH      = this.panel.offsetHeight;
          const espacioAbajo = window.innerHeight - displayRect.bottom - 8;
          const espacioArriba = displayRect.top - 8;
          const inModal = this.wrapper.closest('.modal__body');

          if (inModal || espacioAbajo >= panelH || espacioAbajo >= espacioArriba) {
            this.panel.classList.remove('dp-panel--arriba');
          } else {
            this.panel.classList.add('dp-panel--arriba');
          }
        });
      }
    });

    this.panel.addEventListener('click', (e) => {
      e.stopPropagation();

      /* ── Cambiar modo (mes ↔ año ↔ días) ─── */
      const cambioBtn = e.target.closest('[data-cambio]');
      if (cambioBtn) {
        this.modo = cambioBtn.dataset.cambio;
        if (this.modo === 'anios') this.paginaAnio = Math.floor(this.vistaAno / 12) * 12;
        this._renderPanel();
        return;
      }

      /* ── Seleccionar un mes ─── */
      const mesBtn = e.target.closest('[data-mes]');
      if (mesBtn) {
        this.vistaMes = parseInt(mesBtn.dataset.mes);
        this.modo = 'dias';
        this._renderPanel();
        return;
      }

      /* ── Seleccionar un año ─── */
      const anioBtn = e.target.closest('[data-anio]');
      if (anioBtn) {
        this.vistaAno = parseInt(anioBtn.dataset.anio);
        this.modo = 'meses';
        this._renderPanel();
        return;
      }

      /* ── Navegar año en vista meses ─── */
      const navAnio = e.target.closest('[data-nav-anio]');
      if (navAnio) {
        this.vistaAno += parseInt(navAnio.dataset.navAnio);
        this._renderPanel();
        return;
      }

      /* ── Navegar página en vista años ─── */
      const navPagina = e.target.closest('[data-nav-pagina]');
      if (navPagina) {
        this.paginaAnio += parseInt(navPagina.dataset.navPagina) * 12;
        this._renderPanel();
        return;
      }

      /* ── Navegar mes a mes (flechas en vista días) ─── */
      const navBtn = e.target.closest('.dp-nav');
      if (navBtn && navBtn.dataset.nav) {
        this.vistaMes += parseInt(navBtn.dataset.nav);
        if (this.vistaMes < 0)  { this.vistaMes = 11; this.vistaAno--; }
        if (this.vistaMes > 11) { this.vistaMes = 0;  this.vistaAno++; }
        this._renderPanel();
        return;
      }

      /* ── Seleccionar día ─── */
      const dayBtn = e.target.closest('.dp-day');
      if (dayBtn && dayBtn.dataset.d) {
        this._seleccionarFecha(
          new Date(this.vistaAno, this.vistaMes, parseInt(dayBtn.dataset.d))
        );
        this.panel.setAttribute('hidden', '');
        return;
      }

      if (e.target.classList.contains('dp-btn-hoy')) {
        this._seleccionarFecha(new Date());
        this.panel.setAttribute('hidden', '');
        return;
      }

      if (e.target.classList.contains('dp-btn-limpiar')) {
        this.limpiar();
        this.panel.setAttribute('hidden', '');
        return;
      }
    });

    document.addEventListener('click', () => {
      this.panel.setAttribute('hidden', '');
    });
  }

  /* ── API pública ──────────────────────────────────── */
  _seleccionarFecha(fecha) {
    this.valor    = fecha;
    this.vistaAno = fecha.getFullYear();
    this.vistaMes = fecha.getMonth();

    const iso = fecha.toISOString().split('T')[0];
    this.input.value = iso;

    const dd = String(fecha.getDate()).padStart(2,'0');
    const mm = String(fecha.getMonth()+1).padStart(2,'0');
    const aaaa = fecha.getFullYear();
    this.display.querySelector('.dp-display-text').textContent = `${dd}/${mm}/${aaaa}`;

    if (this.onChange) this.onChange(iso);
  }

  setValor(isoStr) {
    if (!isoStr) return;
    const [y, m, d] = isoStr.split('-').map(Number);
    this._seleccionarFecha(new Date(y, m - 1, d));
  }

  getValor() {
    return this.input.value;
  }

  limpiar() {
    this.valor = null;
    this.input.value = '';
    this.display.querySelector('.dp-display-text').textContent = 'Seleccionar fecha';
    if (this.onChange) this.onChange('');
  }
}
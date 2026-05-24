/**
 * MiniDatepicker
 * Datepicker ligero y estético integrado con el design system de GastuApp.
 * Uso: new MiniDatepicker(inputEl, { onChange: (isoDate) => {} })
 */
'use strict';

class MiniDatepicker {
  constructor(inputEl, opciones = {}) {
    this.input    = inputEl;
    this.onChange = opciones.onChange || null;
    this.acento   = opciones.acento   || 'ingreso';
    this.valor    = null;
    this.hoy      = new Date();
    this.vistaAno = this.hoy.getFullYear();
    this.vistaMes = this.hoy.getMonth();

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

  _renderPanel() {
    const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                   'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    const DIAS  = ['Lu','Ma','Mi','Ju','Vi','Sa','Do'];

    const primerDia = new Date(this.vistaAno, this.vistaMes, 1);
    const totalDias = new Date(this.vistaAno, this.vistaMes + 1, 0).getDate();
    // lunes=0 ... domingo=6
    let offsetInicio = primerDia.getDay() - 1;
    if (offsetInicio < 0) offsetInicio = 6;

    const valorSeleccionado = this.valor
      ? `${this.valor.getFullYear()}-${this.valor.getMonth()}-${this.valor.getDate()}`
      : null;

    const hoyKey = `${this.hoy.getFullYear()}-${this.hoy.getMonth()}-${this.hoy.getDate()}`;

    let celdasHTML = DIAS.map(d => `<span class="dp-dow">${d}</span>`).join('');

    for (let i = 0; i < offsetInicio; i++) {
      celdasHTML += `<span class="dp-day dp-day--vacio"></span>`;
    }
    for (let d = 1; d <= totalDias; d++) {
      const key = `${this.vistaAno}-${this.vistaMes}-${d}`;
      const esHoy = key === hoyKey;
      const esSel = valorSeleccionado && key === valorSeleccionado;
      celdasHTML += `<button type="button" class="dp-day${esHoy ? ' dp-day--hoy' : ''}${esSel ? ' dp-day--sel' : ''}"
                             data-d="${d}">${d}</button>`;
    }

    this.panel.innerHTML = `
      <div class="dp-header">
        <button type="button" class="dp-nav" data-nav="-1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <span class="dp-mes-anio">${MESES[this.vistaMes]} ${this.vistaAno}</span>
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
        this._renderPanel();
        this.panel.removeAttribute('hidden');

        /* Medir espacio real con rAF (panel ya en DOM pero aún no repintado) */
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

      const navBtn = e.target.closest('.dp-nav');
      if (navBtn && navBtn.dataset.nav) {
        this.vistaMes += parseInt(navBtn.dataset.nav);
        if (this.vistaMes < 0)  { this.vistaMes = 11; this.vistaAno--; }
        if (this.vistaMes > 11) { this.vistaMes = 0;  this.vistaAno++; }
        this._renderPanel();
        return;
      }

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
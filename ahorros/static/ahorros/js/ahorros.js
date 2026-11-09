/**
 * ahorros.js
 * Vista de Ahorros: filtros, detalle de meta con aportes, formulario de
 * crear/editar, borrado y exportacion. Las cards se renderizan en el servidor.
 * Depende de gastu_planificacion.js (GastuPlan), category-picker.js y datepicker.js.
 */
'use strict';

(function () {
  const P = window.GastuPlan;
  const $ = id => document.getElementById(id);
  const app = $('ahorros-app');
  if (!app) return;

  const csrf = () => app.querySelector('[name=csrfmiddlewaretoken]').value;

  const estado = {
    filtro: 'en_curso',
    busqueda: '',
    plazo: 'cuotas',
    fechaCreacion: null,
    dpFecha: null,
    formato: 'csv',
    estadoReporte: '',
  };

  /* Igual que DELTA_FRECUENCIA en ahorros/services.py */
  const PERIODO = {
    DIARIA: { dias: 1 }, SEMANAL: { dias: 7 }, QUINCENAL: { dias: 15 },
    MENSUAL: { meses: 1 }, TRIMESTRAL: { meses: 3 }, SEMESTRAL: { meses: 6 }, ANUAL: { meses: 12 },
  };

  /** Fecha de la cuota n (0 = primera), calculada desde la primera para no correr el dia. */
  function fechaCuota(inicio, frecuencia, n) {
    const p = PERIODO[frecuencia] || PERIODO.MENSUAL;
    if (p.dias) return new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate() + p.dias * n);
    const destino = new Date(inicio.getFullYear(), inicio.getMonth() + p.meses * n, 1);
    const ultimoDia = new Date(destino.getFullYear(), destino.getMonth() + 1, 0).getDate();
    destino.setDate(Math.min(inicio.getDate(), ultimoDia));
    return destino;
  }

  async function enviarFormulario(url, datos) {
    const fd = new FormData();
    Object.entries(datos).forEach(([k, v]) => fd.append(k, v ?? ''));
    fd.append('csrfmiddlewaretoken', csrf());
    let respuesta;
    try {
      respuesta = await fetch(url, { method: 'POST', body: fd, headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' });
    } catch (e) {
      throw new Error('No se pudo conectar con el servidor.');
    }
    let json = null;
    try { json = await respuesta.json(); } catch (e) { json = null; }
    if (!respuesta.ok || !json || json.ok === false) {
      const error = new Error(json?.error || 'No se pudo completar la acción.');
      error.errores = json?.errors;
      throw error;
    }
    return json;
  }

  function recargarCon(mensaje) {
    P.toast(mensaje);
    setTimeout(() => window.location.reload(), 650);
  }

  /* ── Barras y filtros ────────────────────────────────────── */
  function animarBarras(raiz) {
    raiz.querySelectorAll('.plan-progreso__relleno').forEach(barra => {
      requestAnimationFrame(() => { barra.style.width = `${Math.min(Number(barra.dataset.pct) || 0, 100)}%`; });
    });
  }

  function aplicarFiltros() {
    const cards = [...app.querySelectorAll('#grid-metas .plan-card')];
    let visibles = 0;
    cards.forEach(card => {
      const pasaEstado = estado.filtro === 'todas' || card.dataset.grupo === estado.filtro;
      const pasaTexto = !estado.busqueda || (card.dataset.buscar || '').includes(estado.busqueda);
      card.hidden = !(pasaEstado && pasaTexto);
      if (!card.hidden) visibles += 1;
    });
    if (!cards.length) return;
    const vacio = $('metas-vacio');
    vacio.hidden = visibles > 0;
    if (!visibles) {
      $('metas-vacio-titulo').textContent = 'Sin resultados';
      $('metas-vacio-texto').textContent = estado.busqueda
        ? 'Ninguna meta coincide con tu búsqueda.'
        : estado.filtro === 'en_curso' ? 'No tienes metas en curso.' : 'No hay metas en este filtro.';
      $('btn-nueva-meta-empty').hidden = !(estado.filtro === 'en_curso' && !estado.busqueda);
    }
  }

  /* ── Detalle de meta ─────────────────────────────────────── */
  const overlayDetalle = $('modal-overlay-aporte');

  async function abrirDetalle(url) {
    overlayDetalle.innerHTML = '<div class="plan-modal ahorro-cargando"><span>Cargando meta...</span></div>';
    P.abrirModal('modal-overlay-aporte');
    let html;
    try {
      const r = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' });
      if (!r.ok) throw new Error();
      html = await r.text();
    } catch (e) {
      P.cerrarModal('modal-overlay-aporte');
      P.toast('No pudimos abrir el detalle de la meta.', 'error');
      return;
    }
    overlayDetalle.innerHTML = html;
    P.iconos();
    animarBarras(overlayDetalle);
    overlayDetalle.querySelectorAll('[data-monto]').forEach(input => {
      P.initMonto(input);
      if (input.dataset.inicial) P.setMonto(input, input.dataset.inicial);
    });
    overlayDetalle.querySelectorAll('[data-cerrar-detalle]').forEach(b => b.addEventListener('click', () => P.cerrarModal('modal-overlay-aporte')));
    overlayDetalle.querySelectorAll('.form-aporte-modal').forEach(form => form.addEventListener('submit', enviarAporte));
  }

  function errorDetalle(mensaje) {
    const caja = overlayDetalle.querySelector('#detalle-error');
    if (!caja) { P.toast(mensaje, 'error'); return; }
    caja.querySelector('#detalle-error-texto').textContent = mensaje;
    caja.hidden = false;
    caja.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  async function enviarAporte(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const input = form.querySelector('[data-monto]');
    const monto = P.leerMonto(input);
    if (!monto) { errorDetalle('Escribe el monto del aporte.'); return; }

    const datos = { aporte: monto };
    form.querySelectorAll('input[type=hidden]').forEach(h => { if (h.name !== 'csrfmiddlewaretoken') datos[h.name] = h.value; });
    const boton = form.querySelector('button[type=submit]');
    boton.disabled = true;
    try {
      const json = await enviarFormulario(form.action, datos);
      P.cerrarModal('modal-overlay-aporte');
      recargarCon(json.message || 'Aporte registrado');
    } catch (err) {
      errorDetalle(err.message);
      boton.disabled = false;
    }
  }

  /* ── Formulario crear / editar ───────────────────────────── */
  function setCategoria(id, nombre) {
    $('meta-categoria').value = id || '';
    $('meta-categoria-texto').textContent = nombre || 'Selecciona una categoría de ahorro';
    $('meta-categoria-btn').classList.toggle('has-value', !!id);
  }

  function setFrecuencia(valor) {
    $('meta-frecuencia').value = valor || '';
    app.querySelectorAll('#meta-frecuencias .plan-opcion').forEach(b => b.classList.toggle('is-activo', b.dataset.frecuencia === valor));
    actualizarCalendario();
  }

  function setPlazo(modo) {
    estado.plazo = modo;
    app.querySelectorAll('#meta-plazo [data-plazo]').forEach(b => {
      const activo = b.dataset.plazo === modo;
      b.classList.toggle('is-activo', activo);
      b.setAttribute('aria-selected', String(activo));
    });
    $('meta-plazo-cuotas').hidden = modo !== 'cuotas';
    $('meta-plazo-fecha').hidden = modo !== 'fecha';
    actualizarCalendario();
  }

  /** Vista previa del plan: valor de cada cuota y fecha de la ultima. */
  function actualizarCalendario() {
    const hint = $('meta-calendario');
    const frecuencia = $('meta-frecuencia').value;
    const monto = P.leerMonto($('meta-monto'));
    const base = estado.fechaCreacion ? P.parseISO(estado.fechaCreacion) : P.parseISO(P.hoyISO());
    const inicio = new Date(base.getFullYear(), base.getMonth(), base.getDate() + 1);
    let cuotas = 0;
    if (frecuencia && estado.plazo === 'cuotas') {
      cuotas = parseInt($('meta-cuotas').value, 10) || 0;
    } else if (frecuencia && estado.plazo === 'fecha' && $('meta-fecha').value) {
      const limite = P.parseISO($('meta-fecha').value);
      cuotas = 1;
      while (fechaCuota(inicio, frecuencia, cuotas) <= limite && cuotas < 3650) cuotas += 1;
    }
    if (!frecuencia || cuotas < 1) { hint.textContent = ''; return; }
    const ultima = fechaCuota(inicio, frecuencia, cuotas - 1);
    const valor = monto ? `de ${P.formatMonto(monto / cuotas)} ` : '';
    hint.textContent = `${P.plural(cuotas, 'cuota', 'cuotas')} ${valor}· la primera el ${P.formatFecha(P.aISO(inicio))}, la última el ${P.formatFecha(P.aISO(ultima))}`;
  }

  function mostrarErroresMeta(mensaje) {
    $('meta-errores-texto').textContent = mensaje;
    $('meta-errores').hidden = !mensaje;
  }

  function abrirFormulario(datos) {
    const editando = !!datos;
    mostrarErroresMeta('');
    $('meta-url').value = editando ? datos.url : app.dataset.urlCrear;
    $('modal-meta-titulo').textContent = editando ? 'Editar meta de ahorro' : 'Nueva meta de ahorro';
    $('modal-meta-subtitulo').textContent = editando ? (datos.categoria_nombre || '') : 'Cuánto quieres ahorrar y en cuánto tiempo';
    $('meta-guardar-texto').textContent = editando ? 'Guardar cambios' : 'Crear meta';
    estado.fechaCreacion = editando ? datos.fecha_creacion : null;

    setCategoria(editando ? datos.categoria_id : '', editando ? datos.categoria_nombre : '');
    P.setMonto($('meta-monto'), editando ? datos.monto_meta : '');
    const minimo = editando ? Number(datos.total_acumulado) : 0;
    $('meta-monto').dataset.minimo = minimo || '';
    $('meta-monto-hint').textContent = minimo ? `Ya ahorraste ${P.formatMonto(minimo)}; la meta no puede ser menor.` : '';
    $('meta-descripcion').value = editando ? datos.descripcion : '';
    $('meta-descripcion-contador').textContent = `${$('meta-descripcion').value.length}/150`;
    $('meta-cuotas').value = editando ? datos.cantidad_cuotas : '';
    $('meta-cuotas').min = editando && datos.cuotas_minimas ? datos.cuotas_minimas : 1;
    estado.dpFecha?.limpiar();
    setFrecuencia(editando ? datos.frecuencia : 'MENSUAL');
    setPlazo('cuotas');
    P.abrirModal('modal-meta');
  }

  async function abrirEdicion(url) {
    try {
      const r = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' });
      const json = await r.json();
      if (!json.ok) throw new Error();
      abrirFormulario({ ...json.ahorro, url });
    } catch (e) {
      P.toast('No pudimos cargar la meta.', 'error');
    }
  }

  async function guardarMeta(e) {
    e.preventDefault();
    const datos = {
      categoria: $('meta-categoria').value,
      monto_meta: P.leerMonto($('meta-monto')),
      frecuencia: $('meta-frecuencia').value,
      cantidad_cuotas: estado.plazo === 'cuotas' ? $('meta-cuotas').value : '',
      fecha_meta: estado.plazo === 'fecha' ? $('meta-fecha').value : '',
      descripcion: $('meta-descripcion').value.trim(),
    };
    const minimo = Number($('meta-monto').dataset.minimo) || 0;
    if (!datos.categoria) return mostrarErroresMeta('Selecciona una categoría.');
    if (!datos.monto_meta) return mostrarErroresMeta('El monto meta debe ser mayor a 0.');
    if (minimo && datos.monto_meta < minimo) return mostrarErroresMeta(`La meta no puede ser menor a lo que ya ahorraste (${P.formatMonto(minimo)}).`);
    if (!datos.frecuencia) return mostrarErroresMeta('Selecciona la frecuencia de ahorro.');
    if (estado.plazo === 'cuotas' && !(parseInt(datos.cantidad_cuotas, 10) >= 1)) return mostrarErroresMeta('Indica en cuántas cuotas quieres ahorrar.');
    if (estado.plazo === 'fecha' && !datos.fecha_meta) return mostrarErroresMeta('Elige la fecha meta.');

    const boton = $('meta-guardar');
    boton.disabled = true;
    try {
      const json = await enviarFormulario($('meta-url').value, datos);
      P.cerrarModal('modal-meta');
      recargarCon(json.message || 'Meta guardada');
    } catch (err) {
      const mensajes = err.errores ? Object.values(err.errores).flat().join(' ') : err.message;
      mostrarErroresMeta(mensajes);
      boton.disabled = false;
    }
  }

  function abrirCategorias() {
    $('buscador-categorias').value = '';
    window.CategoryPicker?.init({
      containerId: 'picker-grid',
      context: 'ahorros',
      tipo: 'AHORRO',
      onSelect: cat => {
        setCategoria(cat.id, cat.nombre);
        P.cerrarModal('modal-categorias');
      },
    });
    P.abrirModal('modal-categorias');
    setTimeout(() => $('buscador-categorias').focus(), 50);
  }

  /* ── Eliminar ────────────────────────────────────────────── */
  async function eliminar(btn) {
    const acumulado = Number(btn.dataset.acumulado) || 0;
    const extra = acumulado ? ` Lo que ya ahorraste (${P.formatMonto(acumulado)}) vuelve a tu disponible.` : '';
    const ok = await P.confirmarEliminar('Eliminar meta', `Se eliminará "${btn.dataset.nombre}" con todo su historial de cuotas.${extra}`);
    if (!ok) return;
    try {
      const json = await enviarFormulario(btn.dataset.url, {});
      recargarCon(json.message || 'Meta eliminada');
    } catch (e) {
      P.toast(e.message, 'error');
    }
  }

  /* ── Exportar ────────────────────────────────────────────── */
  const FORMATOS = { csv: 'CSV', excel: 'Excel (.xlsx)', pdf: 'PDF' };

  function abrirReporte(formato) {
    estado.formato = formato;
    $('modal-reporte-formato').textContent = `Formato ${FORMATOS[formato]}`;
    P.abrirModal('modal-reporte');
  }

  function descargarReporte() {
    const urls = { csv: app.dataset.urlExportarCsv, excel: app.dataset.urlExportarExcel, pdf: app.dataset.urlExportarPdf };
    const params = estado.estadoReporte ? `?estado=${encodeURIComponent(estado.estadoReporte)}` : '';
    window.location.href = urls[estado.formato] + params;
    P.cerrarModal('modal-reporte');
  }

  /* ── Eventos ─────────────────────────────────────────────── */
  function bindear() {
    P.initModales();
    P.initMonto($('meta-monto'), actualizarCalendario);
    estado.dpFecha = P.crearDatepicker($('meta-fecha'), actualizarCalendario, { acento: 'ahorro' });

    $('buscador-metas').addEventListener('input', e => {
      estado.busqueda = e.target.value.trim().toLowerCase();
      aplicarFiltros();
    });
    $('filtro-estado').addEventListener('click', e => {
      const btn = e.target.closest('[data-filtro]');
      if (!btn) return;
      estado.filtro = btn.dataset.filtro;
      app.querySelectorAll('#filtro-estado .plan-filtro__opcion').forEach(b => b.classList.toggle('is-activo', b === btn));
      aplicarFiltros();
    });

    $('btn-nueva-meta').addEventListener('click', () => abrirFormulario(null));
    $('form-meta').addEventListener('submit', guardarMeta);
    $('meta-categoria-btn').addEventListener('click', abrirCategorias);
    $('buscador-categorias').addEventListener('input', e => window.CategoryPicker?.filter(e.target.value));
    $('meta-cuotas').addEventListener('input', actualizarCalendario);
    $('meta-descripcion').addEventListener('input', e => { $('meta-descripcion-contador').textContent = `${e.target.value.length}/150`; });
    $('meta-frecuencias').addEventListener('click', e => {
      const btn = e.target.closest('[data-frecuencia]');
      if (btn) setFrecuencia(btn.dataset.frecuencia);
    });
    $('meta-plazo').addEventListener('click', e => {
      const btn = e.target.closest('[data-plazo]');
      if (btn) setPlazo(btn.dataset.plazo);
    });

    app.querySelectorAll('[data-exportar]').forEach(b => b.addEventListener('click', () => abrirReporte(b.dataset.exportar)));
    $('reporte-estados').addEventListener('click', e => {
      const btn = e.target.closest('[data-estado]');
      if (!btn) return;
      estado.estadoReporte = btn.dataset.estado;
      app.querySelectorAll('#reporte-estados .plan-opcion').forEach(b => b.classList.toggle('is-activo', b === btn));
    });
    $('btn-descargar-reporte').addEventListener('click', descargarReporte);

    app.addEventListener('click', e => {
      const btn = e.target.closest('[data-accion]');
      if (!btn || !app.contains(btn)) return;
      switch (btn.dataset.accion) {
        case 'detalle': abrirDetalle(btn.dataset.url); break;
        case 'editar': abrirEdicion(btn.dataset.url); break;
        case 'eliminar': eliminar(btn); break;
        case 'nueva': abrirFormulario(null); break;
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    window.CURRENT_MODULE = 'ahorros';
    if (window.GastuTours) window.GastuTours.init(window.CURRENT_MODULE);
    bindear();
    aplicarFiltros();
    animarBarras(app);
  });
})();

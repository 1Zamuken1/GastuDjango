/**
 * programaciones.js
 * Vista de Programaciones: hero, pendientes por confirmar, filtros, cards y formulario.
 * Depende de gastu_planificacion.js (GastuPlan), category-picker.js y datepicker.js.
 */
'use strict';

(function () {
  const P = window.GastuPlan;
  const API = '/api/programaciones/';

  /* Veces que ocurre cada frecuencia en un mes promedio (igual que FACTOR_MENSUAL en services.py). */
  const FACTOR_MENSUAL = {
    DIARIO: 30, SEMANAL: 52 / 12, QUINCENAL: 2, MENSUAL: 1,
    BIMESTRAL: 1 / 2, TRIMESTRAL: 1 / 3, SEMESTRAL: 1 / 6, ANUAL: 1 / 12,
  };

  const estado = {
    programaciones: [],
    pendientes: [],
    filtroTipo: 'todos',
    filtroEstado: 'activas',
    busqueda: '',
    dpInicio: null,
    dpFin: null,
    procesando: false,
  };

  const $ = id => document.getElementById(id);

  /* ── Estados ─────────────────────────────────────────────── */
  function terminada(p) {
    return !!p.fecha_fin && P.diasHasta(p.fecha_fin) < 0;
  }

  function estadoDe(p) {
    if (!p.activo) return (terminada(p) || (!p.proxima_ejecucion && p.fecha_fin)) ? 'finalizada' : 'pausada';
    if (p.proxima_ejecucion && P.diasHasta(p.proxima_ejecucion) <= 0) return 'pendiente';
    return 'activa';
  }

  const CHIP = {
    activa: ['programado', 'Activa'],
    pendiente: ['pendiente', 'Por confirmar'],
    pausada: ['inactiva', 'Pausada'],
    finalizada: ['inactiva', 'Finalizada'],
  };

  /* ── Carga ───────────────────────────────────────────────── */
  async function cargar() {
    try {
      const data = await P.api(API);
      estado.programaciones = Array.isArray(data) ? data : (data.results || []);
    } catch (e) {
      $('cards-programacion').innerHTML = vacio('alert-circle', 'No pudimos cargar tus programaciones', e.message, false);
      P.iconos();
      return;
    }
    renderHero();
    renderConteos();
    renderCards();
  }

  async function cargarPendientes(abrirSiHay) {
    try {
      const data = await P.api(`${API}pendientes/`);
      estado.pendientes = data.pendientes || [];
    } catch (e) {
      estado.pendientes = [];
    }
    renderBannerPendientes();
    renderHero();
    if (!$('modal-pendientes').hidden) renderListaPendientes();

    if (abrirSiHay && estado.pendientes.length) {
      const firma = estado.pendientes.map(p => `${p.id}:${p.fecha_pendiente}`).join('|');
      if (P.leerSesion('programaciones_pendientes_vistos') !== firma) {
        P.guardarSesion('programaciones_pendientes_vistos', firma);
        abrirPendientes();
      }
    }
  }

  /* ── Hero ────────────────────────────────────────────────── */
  function renderHero() {
    const activas = estado.programaciones.filter(p => p.activo);
    const ingresos = activas.filter(p => p.tipo === 'INGRESO').reduce((s, p) => s + (p.monto_mensual || 0), 0);
    const egresos = activas.filter(p => p.tipo === 'EGRESO').reduce((s, p) => s + (p.monto_mensual || 0), 0);
    const balance = ingresos - egresos;

    $('stat-balance').textContent = `${balance < 0 ? '-' : ''}${P.formatMonto(Math.abs(balance))}`;
    $('stat-badge').textContent = activas.length
      ? `${P.plural(activas.length, 'activa', 'activas')} de ${estado.programaciones.length}`
      : 'Sin programaciones activas';
    $('stat-ingresos').textContent = P.formatMonto(ingresos);
    $('stat-egresos').textContent = P.formatMonto(egresos);
    $('stat-pendientes').textContent = estado.pendientes.length;

    const proxima = activas
      .filter(p => p.proxima_ejecucion && P.diasHasta(p.proxima_ejecucion) > 0)
      .sort((a, b) => a.proxima_ejecucion.localeCompare(b.proxima_ejecucion))[0];
    $('stat-proxima').textContent = proxima ? (proxima.descripcion || proxima.categoria_nombre) : 'Sin fechas';
    $('stat-proxima').title = $('stat-proxima').textContent;
    $('stat-proxima-fecha').textContent = proxima
      ? `${P.formatFecha(proxima.proxima_ejecucion, true)}, ${P.textoRelativo(proxima.proxima_ejecucion)}`
      : '—';
  }

  function renderBannerPendientes() {
    const n = estado.pendientes.length;
    $('banner-pendientes').hidden = !n;
    if (n) {
      $('banner-pendientes-titulo').textContent = n === 1
        ? 'Tienes un movimiento programado por confirmar'
        : `Tienes ${n} movimientos programados por confirmar`;
    }
  }

  /* ── Filtros ─────────────────────────────────────────────── */
  function coincideFiltro(p) {
    if (estado.filtroTipo !== 'todos' && p.tipo !== estado.filtroTipo) return false;
    if (estado.filtroEstado === 'activas' && !p.activo) return false;
    if (estado.filtroEstado === 'inactivas' && p.activo) return false;
    if (estado.busqueda) {
      const texto = `${p.categoria_nombre} ${p.descripcion || ''}`.toLowerCase();
      if (!texto.includes(estado.busqueda)) return false;
    }
    return true;
  }

  function renderConteos() {
    const base = estado.programaciones.filter(p => estado.filtroTipo === 'todos' || p.tipo === estado.filtroTipo);
    const activas = base.filter(p => p.activo).length;
    const conteos = { activas, inactivas: base.length - activas, todas: base.length };
    document.querySelectorAll('#filtro-estado [data-conteo]').forEach(el => {
      el.textContent = conteos[el.dataset.conteo];
    });
  }

  /* ── Cards ───────────────────────────────────────────────── */
  function vacio(icono, titulo, texto, conBoton) {
    return `
      <div class="plan-vacio">
        <div class="plan-vacio__icono"><i data-lucide="${icono}"></i></div>
        <p class="plan-vacio__titulo">${P.esc(titulo)}</p>
        <p class="plan-vacio__texto">${P.esc(texto)}</p>
        ${conBoton ? '<button type="button" class="btn-plan btn-plan--chico" data-accion="nuevo"><i data-lucide="plus"></i> Crear programación</button>' : ''}
      </div>`;
  }

  function renderCards() {
    const contenedor = $('cards-programacion');
    if (!estado.programaciones.length) {
      contenedor.innerHTML = vacio('calendar-range', 'Aún no tienes programaciones',
        'Agrega tus pagos fijos, como el arriendo o las suscripciones, y tu salario. Te recordaremos registrarlos en su fecha.', true);
      P.iconos();
      return;
    }
    const lista = estado.programaciones
      .filter(coincideFiltro)
      .sort((a, b) => {
        if (a.activo !== b.activo) return a.activo ? -1 : 1;
        return (a.proxima_ejecucion || '9999').localeCompare(b.proxima_ejecucion || '9999');
      });
    if (!lista.length) {
      contenedor.innerHTML = vacio('search-x', 'Sin resultados',
        estado.busqueda ? 'Ninguna programación coincide con tu búsqueda.' : 'No hay programaciones en este filtro.', false);
      P.iconos();
      return;
    }
    contenedor.innerHTML = lista.map(cardHTML).join('');
    P.iconos();
  }

  function cardHTML(p) {
    const est = estadoDe(p);
    const [chipClase, chipTexto] = CHIP[est];
    const esIngreso = p.tipo === 'INGRESO';
    const tipoClase = esIngreso ? 'ingreso' : 'egreso';
    const titulo = p.descripcion || p.categoria_nombre;
        const equivalente = p.frecuencia !== 'MENSUAL' && p.monto_mensual
      ? `<p class="plan-card__equivalente">Equivale a ${P.formatMonto(p.monto_mensual)} al mes</p>` : '';

    let proxima = '—';
    let cuando = '—';
    if (p.activo && p.proxima_ejecucion) {
      proxima = P.formatFecha(p.proxima_ejecucion, true);
      cuando = est === 'pendiente' ? 'pendiente' : P.textoRelativo(p.proxima_ejecucion);
    }
    const fin = p.fecha_fin ? P.formatFecha(p.fecha_fin, true) : 'Sin fin';
    const id = Number(p.id);

    const accionPrincipal = est === 'pendiente'
      ? `<button type="button" class="plan-card-btn plan-card-btn--acento" data-accion="revisar-pendientes"><i data-lucide="check"></i> Confirmar</button>`
      : est !== 'finalizada'
        ? `<button type="button" class="plan-card-btn plan-card-btn--acento" data-accion="toggle" data-id="${id}"><i data-lucide="${p.activo ? 'pause' : 'play'}"></i> ${p.activo ? 'Pausar' : 'Reanudar'}</button>`
        : '';
    const claseEstado = p.activo ? `plan-card--${tipoClase}` : 'plan-card--inactiva';

    return `
      <article class="plan-card ${claseEstado}" data-id="${id}">
        <header class="plan-card__cabecera">
          <div class="plan-card__principal">
            <p class="plan-card__cifra font-display">${esIngreso ? '+' : '-'}${P.formatMonto(p.monto_programado)}<small>${P.esc(p.frecuencia_label.toLowerCase())}</small></p>
            <p class="plan-card__etiqueta" title="${P.esc(titulo)}">${P.esc(titulo)}</p>
            <p class="plan-card__sub">${P.esc(p.descripcion ? p.categoria_nombre : (esIngreso ? 'Ingreso' : 'Egreso'))}</p>
          </div>
          <div class="plan-card__lado">
            <div class="plan-card__icono plan-card__icono--${tipoClase}"><i data-lucide="${esIngreso ? 'trending-up' : 'trending-down'}"></i></div>
            <span class="plan-chip plan-chip--${chipClase}">${chipTexto}</span>
          </div>
        </header>

        <div class="plan-card__cuerpo">
          <dl class="plan-card__datos">
            <div><dt>Próxima</dt><dd>${proxima}</dd></div>
            <div><dt>Cuándo</dt><dd class="${est === 'pendiente' ? 'is-pendiente' : ''}">${P.esc(cuando)}</dd></div>
            <div><dt>Termina</dt><dd>${fin}</dd></div>
          </dl>
          ${equivalente}
          <p class="plan-card__periodo"><i data-lucide="calendar"></i>Desde ${P.formatFecha(p.fecha_inicio, true)}</p>
        </div>

        <footer class="plan-card__pie">
          ${accionPrincipal}
          <button type="button" class="plan-card-btn" data-accion="editar" data-id="${id}"><i data-lucide="pencil"></i> Editar</button>
          <button type="button" class="plan-card-btn plan-card-btn--peligro" data-accion="eliminar" data-id="${id}" title="Eliminar" aria-label="Eliminar"><i data-lucide="trash-2"></i></button>
        </footer>
      </article>`;
  }

  /* ── Pendientes ──────────────────────────────────────────── */
  function abrirPendientes() {
    renderListaPendientes();
    P.abrirModal('modal-pendientes');
  }

  function renderListaPendientes() {
    const lista = $('lista-pendientes');
    $('btn-registrar-todas').hidden = estado.pendientes.length < 2;
    if (!estado.pendientes.length) {
      lista.innerHTML = '<li class="plan-lista__vacio">No tienes movimientos por confirmar. Todo está al día.</li>';
      return;
    }
    lista.innerHTML = estado.pendientes.map(p => {
      const nombre = p.descripcion || p.categoria_nombre;
      const meta = [p.descripcion ? p.categoria_nombre : null, p.frecuencia_label,
        `programado para el ${P.formatFecha(p.fecha_pendiente)}`].filter(Boolean).join(' · ');
      return `
        <li class="plan-lista__item">
          <div class="plan-card__icono plan-card__icono--${p.tipo === 'INGRESO' ? 'ingreso' : 'egreso'}">
            <i data-lucide="${p.tipo === 'INGRESO' ? 'trending-up' : 'trending-down'}"></i>
          </div>
          <div class="plan-lista__info">
            <p class="plan-lista__nombre">${P.esc(nombre)}</p>
            <p class="plan-lista__meta">${P.esc(meta)}</p>
          </div>
          <span class="plan-lista__monto plan-lista__monto--${p.tipo === 'INGRESO' ? 'INGRESO' : 'EGRESO'}">${p.tipo === 'INGRESO' ? '+' : '-'}${P.formatMonto(p.monto_programado)}</span>
          <div class="plan-lista__acciones">
            <button type="button" class="plan-lista__btn plan-lista__btn--omitir" data-ejecutar="rechazar" data-id="${Number(p.id)}">Omitir</button>
            <button type="button" class="plan-lista__btn plan-lista__btn--registrar" data-ejecutar="aceptar" data-id="${Number(p.id)}">Registrar</button>
          </div>
        </li>`;
    }).join('');
    P.iconos();
  }

  async function ejecutar(id, accion) {
    const respuesta = await P.api(`${API}${id}/ejecutar/`, { method: 'POST', body: { accion } });
    return respuesta;
  }

  async function procesarUno(id, accion, boton) {
    if (estado.procesando) return;
    estado.procesando = true;
    const fila = boton?.closest('.plan-lista__item');
    fila?.querySelectorAll('button').forEach(b => { b.disabled = true; });
    try {
      await ejecutar(id, accion);
      P.toast(accion === 'aceptar' ? 'Movimiento registrado' : 'Movimiento omitido', accion === 'aceptar' ? 'success' : 'info');
    } catch (e) {
      P.toast(e.message, 'error');
      fila?.querySelectorAll('button').forEach(b => { b.disabled = false; });
    } finally {
      estado.procesando = false;
    }
    await Promise.all([cargarPendientes(false), cargar()]);
  }

  async function registrarTodas() {
    if (estado.procesando || !estado.pendientes.length) return;
    estado.procesando = true;
    const boton = $('btn-registrar-todas');
    boton.disabled = true;
    let registrados = 0;
    let error = null;
    for (const p of [...estado.pendientes]) {
      try {
        await ejecutar(p.id, 'aceptar');
        registrados += 1;
      } catch (e) {
        error = `${p.descripcion || p.categoria_nombre}: ${e.message}`;
        break;
      }
    }
    estado.procesando = false;
    boton.disabled = false;
    if (registrados) P.toast(`${P.plural(registrados, 'movimiento registrado', 'movimientos registrados')}`);
    if (error) P.toast(error, 'error');
    await Promise.all([cargarPendientes(false), cargar()]);
  }

  /* ── Acciones de card ────────────────────────────────────── */
  function buscar(id) {
    return estado.programaciones.find(p => p.id === Number(id));
  }

  async function toggle(id) {
    const p = buscar(id);
    if (!p) return;
    try {
      await P.api(`${API}${p.id}/`, { method: 'PATCH', body: { activo: !p.activo } });
      P.toast(p.activo ? 'Programación pausada' : 'Programación reanudada');
      await Promise.all([cargar(), cargarPendientes(false)]);
    } catch (e) {
      P.toast(e.message, 'error');
    }
  }

  async function eliminar(id) {
    const p = buscar(id);
    const nombre = p ? (p.descripcion || p.categoria_nombre) : 'esta programación';
    const ok = await P.confirmarEliminar('Eliminar programación',
      `Se eliminará "${nombre}". Los movimientos que ya registraste no se borran.`);
    if (!ok) return;
    try {
      await P.api(`${API}${id}/`, { method: 'DELETE' });
      P.toast('Programación eliminada');
      await Promise.all([cargar(), cargarPendientes(false)]);
    } catch (e) {
      P.toast(e.message, 'error');
    }
  }

  /* ── Formulario ──────────────────────────────────────────── */
  function setCategoria(id, nombre, tipo) {
    $('programacion-categoria').value = id || '';
    $('programacion-categoria-texto').textContent = nombre || 'Selecciona una categoría';
    $('programacion-categoria-btn').classList.toggle('has-value', !!id);
    const chip = $('programacion-categoria-tipo');
    chip.hidden = !tipo;
    chip.className = `picker-trigger-tipo picker-trigger-tipo--${tipo || ''}`;
    chip.textContent = tipo === 'INGRESO' ? 'Ingreso' : tipo === 'EGRESO' ? 'Egreso' : '';
  }

  function setFrecuencia(valor) {
    $('programacion-frecuencia').value = valor || '';
    document.querySelectorAll('#programacion-frecuencias .plan-opcion').forEach(b => {
      b.classList.toggle('is-activo', b.dataset.frecuencia === valor);
    });
    actualizarEquivalente();
  }

  function actualizarEquivalente() {
    const monto = P.leerMonto($('programacion-monto'));
    const frecuencia = $('programacion-frecuencia').value;
    const hint = $('programacion-equivalente');
    if (!monto || !frecuencia || frecuencia === 'MENSUAL') { hint.textContent = ''; return; }
    hint.textContent = `Equivale a unos ${P.formatMonto(monto * FACTOR_MENSUAL[frecuencia])} al mes`;
  }

  function actualizarContador() {
    const largo = $('programacion-descripcion').value.length;
    $('programacion-descripcion-contador').textContent = `${largo}/100`;
  }

  function abrirFormulario(p) {
    const editando = !!p;
    $('programacion-id').value = editando ? p.id : '';
    $('modal-programacion-titulo').textContent = editando ? 'Editar programación' : 'Nueva programación';
    $('programacion-guardar-texto').textContent = editando ? 'Guardar cambios' : 'Crear programación';
    setCategoria(editando ? p.categoria : '', editando ? p.categoria_nombre : '', editando ? p.tipo : '');
    P.setMonto($('programacion-monto'), editando ? p.monto_programado : '');
    setFrecuencia(editando ? p.frecuencia : 'MENSUAL');
    $('programacion-descripcion').value = editando ? (p.descripcion || '') : '';
    actualizarContador();
    estado.dpInicio?.setValor(editando ? p.fecha_inicio : P.hoyISO());
    if (editando && p.fecha_fin) estado.dpFin?.setValor(p.fecha_fin);
    else estado.dpFin?.limpiar();
    P.abrirModal('modal-programacion');
  }

  async function guardar(e) {
    e.preventDefault();
    const id = $('programacion-id').value;
    const cuerpo = {
      categoria: $('programacion-categoria').value,
      monto_programado: P.leerMonto($('programacion-monto')),
      frecuencia: $('programacion-frecuencia').value,
      descripcion: $('programacion-descripcion').value.trim() || null,
      fecha_inicio: $('programacion-inicio').value,
      fecha_fin: $('programacion-fin').value || null,
    };
    if (!cuerpo.categoria) return P.toast('Selecciona una categoría.', 'info');
    if (!cuerpo.monto_programado) return P.toast('El monto debe ser mayor a 0.', 'info');
    if (!cuerpo.frecuencia) return P.toast('Selecciona una frecuencia.', 'info');
    if (!cuerpo.fecha_inicio) return P.toast('Indica la primera fecha.', 'info');
    if (cuerpo.fecha_fin && cuerpo.fecha_fin <= cuerpo.fecha_inicio) return P.toast('La fecha de fin debe ser posterior a la primera fecha.', 'info');
    if (!id) cuerpo.activo = true;

    const boton = $('programacion-guardar');
    boton.disabled = true;
    try {
      await P.api(id ? `${API}${id}/` : API, { method: id ? 'PATCH' : 'POST', body: cuerpo });
      P.cerrarModal('modal-programacion');
      P.toast(id ? 'Cambios guardados' : 'Programación creada');
      await Promise.all([cargar(), cargarPendientes(false)]);
    } catch (err) {
      P.toast(err.message, 'error');
    } finally {
      boton.disabled = false;
    }
  }

  function abrirCategorias() {
    $('buscador-categorias').value = '';
    if (window.CategoryPicker) {
      window.CategoryPicker.init({
        containerId: 'picker-grid',
        context: 'programaciones',
        tipo: '',
        onSelect: cat => {
          setCategoria(cat.id, cat.nombre, cat.tipo);
          P.cerrarModal('modal-categorias');
        },
      });
    }
    P.abrirModal('modal-categorias');
    setTimeout(() => $('buscador-categorias').focus(), 50);
  }

  function marcarFiltro(grupoId, valor) {
    document.querySelectorAll(`#${grupoId} .plan-filtro__opcion`).forEach(b => {
      b.classList.toggle('is-activo', b.dataset.filtro === valor);
    });
  }

  /* ── Eventos ─────────────────────────────────────────────── */
  function bindear() {
    P.initModales();
    P.initMonto($('programacion-monto'), actualizarEquivalente);
    estado.dpInicio = P.crearDatepicker($('programacion-inicio'));
    estado.dpFin = P.crearDatepicker($('programacion-fin'));

    $('btn-nuevo').addEventListener('click', () => abrirFormulario(null));
    $('form-programacion').addEventListener('submit', guardar);
    $('programacion-categoria-btn').addEventListener('click', abrirCategorias);
    $('buscador-categorias').addEventListener('input', e => window.CategoryPicker?.filter(e.target.value));
    $('programacion-descripcion').addEventListener('input', actualizarContador);
    $('programacion-frecuencias').addEventListener('click', e => {
      const btn = e.target.closest('[data-frecuencia]');
      if (btn) setFrecuencia(btn.dataset.frecuencia);
    });

    $('buscador').addEventListener('input', e => {
      estado.busqueda = e.target.value.trim().toLowerCase();
      renderCards();
    });
    $('filtro-tipo').addEventListener('click', e => {
      const btn = e.target.closest('[data-filtro]');
      if (!btn) return;
      estado.filtroTipo = btn.dataset.filtro;
      marcarFiltro('filtro-tipo', estado.filtroTipo);
      renderConteos();
      renderCards();
    });
    $('filtro-estado').addEventListener('click', e => {
      const btn = e.target.closest('[data-filtro]');
      if (!btn) return;
      estado.filtroEstado = btn.dataset.filtro;
      marcarFiltro('filtro-estado', estado.filtroEstado);
      renderCards();
    });

    $('lista-pendientes').addEventListener('click', e => {
      const btn = e.target.closest('[data-ejecutar]');
      if (btn) procesarUno(btn.dataset.id, btn.dataset.ejecutar, btn);
    });
    $('btn-registrar-todas').addEventListener('click', registrarTodas);

    $('programaciones-app').addEventListener('click', e => {
      const btn = e.target.closest('[data-accion]');
      if (!btn) return;
      const id = btn.dataset.id;
      switch (btn.dataset.accion) {
        case 'nuevo': abrirFormulario(null); break;
        case 'editar': abrirFormulario(buscar(id)); break;
        case 'toggle': toggle(id); break;
        case 'eliminar': eliminar(id); break;
        case 'revisar-pendientes': abrirPendientes(); break;
      }
    });
  }

  document.addEventListener('DOMContentLoaded', async () => {
    window.CURRENT_MODULE = 'programaciones';
    if (window.GastuTours) window.GastuTours.init(window.CURRENT_MODULE);
    bindear();
    await cargar();
    cargarPendientes(true);
  });
})();

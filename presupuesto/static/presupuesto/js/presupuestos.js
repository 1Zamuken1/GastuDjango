/**
 * presupuestos.js
 * Vista de Presupuestos: hero, avisos, filtros, cards, formulario y renovación.
 * Depende de gastu_planificacion.js (GastuPlan), category-picker.js y datepicker.js.
 */
'use strict';

(function () {
  const P = window.GastuPlan;
  const API = '/api/presupuestos/';

  const estado = {
    presupuestos: [],
    filtro: 'activos',
    busqueda: '',
    dpInicio: null,
    dpFin: null,
  };

  const $ = id => document.getElementById(id);

  /* ── Niveles de consumo ──────────────────────────────────── */
  function nivelDe(p) {
    if (!p.is_activo) return 'inactiva';
    if (P.diasHasta(p.fecha_inicio) > 0) return 'programado';
    const pct = p.porcentaje || 0;
    if (pct >= 100) return 'excedido';
    if (pct >= 80) return 'alerta';
    if (pct >= 50) return 'cuidado';
    return 'normal';
  }

  const ETIQUETAS = {
    normal: 'En control',
    cuidado: 'Cuidado',
    alerta: 'En alerta',
    excedido: 'Excedido',
    inactiva: 'Inactivo',
    programado: 'Programado',
  };

  function estaVencido(p) {
    return P.diasHasta(p.fecha_fin) < 0;
  }

  /* ── Carga ───────────────────────────────────────────────── */
  async function cargar() {
    let desactivados = [];
    try {
      const resultado = await P.api(`${API}verificar_vencidos/`, { method: 'POST', body: {} });
      desactivados = resultado.desactivados || [];
    } catch (e) { /* no bloquea la carga */ }

    try {
      const respuesta = await P.api(`${API}con_estado/`);
      estado.presupuestos = respuesta.data || [];
    } catch (e) {
      $('cards-presupuesto').innerHTML = vacio('alert-circle', 'No pudimos cargar tus presupuestos', e.message, false);
      P.iconos();
      return;
    }

    renderHero();
    renderBannerAlertas();
    renderBannerVencidos(desactivados);
    renderConteos();
    renderCards();
  }

  /* ── Hero ────────────────────────────────────────────────── */
  function renderHero() {
    const activos = estado.presupuestos.filter(p => p.is_activo);
    const totalLimite = activos.reduce((s, p) => s + Number(p.limite), 0);
    const totalGastado = activos.reduce((s, p) => s + (p.gastado || 0), 0);
    const disponible = activos.reduce((s, p) => s + Math.max(p.disponible || 0, 0), 0);
    const enAlerta = activos.filter(p => (p.porcentaje || 0) >= 80).length;
    const vencen = activos.filter(p => {
      const dias = P.diasHasta(p.fecha_fin);
      return dias >= 0 && dias <= 7;
    }).length;

    $('stat-disponible').textContent = P.formatMonto(disponible);
    $('stat-badge').textContent = activos.length
      ? `${P.plural(activos.length, 'activo', 'activos')} de ${estado.presupuestos.length}`
      : 'Sin presupuestos activos';
    $('stat-limite').textContent = P.formatMonto(totalLimite);
    $('stat-gastado').textContent = P.formatMonto(totalGastado);
    $('stat-gastado-sub').textContent = totalLimite
      ? `${Math.round((totalGastado / totalLimite) * 100)}% del total`
      : 'sin límites activos';
    $('stat-alerta').textContent = enAlerta;
    $('stat-vencen').textContent = vencen;
  }

  /* ── Avisos (reemplazan las alertas emergentes en cascada) ─ */
  function renderBannerAlertas() {
    const banner = $('banner-alertas');
    const enAlerta = estado.presupuestos
      .filter(p => p.is_activo && (p.porcentaje || 0) >= 80)
      .sort((a, b) => b.porcentaje - a.porcentaje);

    const firma = enAlerta.map(p => `${p.id}:${nivelDe(p)}`).join('|');
    if (!enAlerta.length || P.leerSesion('presupuestos_alerta_cerrada') === firma) {
      banner.hidden = true;
      return;
    }
    banner.dataset.firma = firma;

    const excedidos = enAlerta.filter(p => p.porcentaje >= 100).length;
    $('banner-alertas-titulo').textContent = excedidos
      ? `${P.plural(excedidos, 'presupuesto superó', 'presupuestos superaron')} su límite`
      : `${P.plural(enAlerta.length, 'presupuesto está', 'presupuestos están')} cerca del límite`;
    $('banner-alertas-texto').textContent = 'Revisa tus gastos en estas categorías antes de que termine el período.';
    $('banner-alertas-items').innerHTML = enAlerta.map(p => `
      <span class="plan-banner__item plan-banner__item--${p.porcentaje >= 100 ? 'excedido' : 'alerta'}">
        ${P.esc(p.categoria_nombre)} <b>${Math.round(p.porcentaje)}%</b>
      </span>`).join('');
    banner.hidden = false;
  }

  function renderBannerVencidos(desactivados) {
    const banner = $('banner-vencidos');
    if (!desactivados.length) { banner.hidden = true; return; }
    $('banner-vencidos-titulo').textContent = desactivados.length === 1
      ? 'Un presupuesto terminó su período'
      : `${desactivados.length} presupuestos terminaron su período`;
    $('banner-vencidos-items').innerHTML = desactivados.map(d => `
      <span class="plan-banner__item">
        ${P.esc(d.categoria__nombre)}
        <button type="button" class="plan-banner__accion" data-accion="renovar" data-id="${Number(d.id)}">Renovar</button>
      </span>`).join('');
    banner.hidden = false;
  }

  /* ── Filtros ─────────────────────────────────────────────── */
  function coincideFiltro(p) {
    if (estado.filtro === 'activos' && !p.is_activo) return false;
    if (estado.filtro === 'inactivos' && p.is_activo) return false;
    if (estado.busqueda && !p.categoria_nombre.toLowerCase().includes(estado.busqueda)) return false;
    return true;
  }

  function renderConteos() {
    const activos = estado.presupuestos.filter(p => p.is_activo).length;
    const conteos = { activos, inactivos: estado.presupuestos.length - activos, todos: estado.presupuestos.length };
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
        ${conBoton ? '<button type="button" class="btn-plan btn-plan--chico" data-accion="nuevo"><i data-lucide="plus"></i> Crear presupuesto</button>' : ''}
      </div>`;
  }

  function renderCards() {
    const contenedor = $('cards-presupuesto');
    if (!estado.presupuestos.length) {
      contenedor.innerHTML = vacio('target', 'Aún no tienes presupuestos',
        'Ponle un límite a las categorías donde más gastas y te avisaremos cuando te acerques.', true);
      P.iconos();
      return;
    }
    const lista = estado.presupuestos.filter(coincideFiltro);
    if (!lista.length) {
      const texto = estado.busqueda
        ? 'Ningún presupuesto coincide con tu búsqueda.'
        : estado.filtro === 'activos' ? 'No tienes presupuestos activos en este momento.' : 'No hay presupuestos en este filtro.';
      contenedor.innerHTML = vacio('search-x', 'Sin resultados', texto, estado.filtro === 'activos' && !estado.busqueda);
      P.iconos();
      return;
    }
    contenedor.innerHTML = lista.map(cardHTML).join('');
    contenedor.querySelectorAll('.progress-bar__fill').forEach(barra => {
      requestAnimationFrame(() => { barra.style.width = `${Math.min(Number(barra.dataset.pct) || 0, 100)}%`; });
    });
    P.iconos();
  }

  /* Color de la barra segun el consumo (clases de css/gastu_card.css) */
  const BARRA = { normal: 'bien', cuidado: 'cuidado', alerta: 'alerta', excedido: 'peligro' };

  function cardHTML(p) {
    const nivel = nivelDe(p);
    const pct = Math.round(p.porcentaje || 0);
    const disponible = p.disponible || 0;
    const vencido = estaVencido(p);
    const id = Number(p.id);
    const periodo = `${P.formatFecha(p.fecha_inicio, true)} – ${P.formatFecha(p.fecha_fin, true)}`;

    let sub = periodo;
    let info;
    if (vencido) {
      info = `<i data-lucide="calendar-x"></i> Terminó el ${P.formatFecha(p.fecha_fin, true)}`;
    } else if (nivel === 'programado') {
      sub = `${periodo} · inicia ${P.textoRelativo(p.fecha_inicio)}`;
      info = `<i data-lucide="calendar-clock"></i> Disponible <b>${P.formatMonto(disponible)}</b>`;
    } else if (disponible < 0) {
      info = `<i data-lucide="alert-circle"></i> Excedido por <b>${P.formatMonto(Math.abs(disponible))}</b>`;
    } else {
      const dias = p.dias_restantes === 1 ? 'último día' : P.plural(p.dias_restantes, 'día', 'días');
      sub = `${periodo} · ${dias}`;
      const porDia = p.gasto_diario !== null && p.gasto_diario !== undefined ? `<span class="categoria-card__info-extra"> · ${P.formatMonto(p.gasto_diario)}/día</span>` : '';
      info = `<i data-lucide="wallet"></i> Disponible <b>${P.formatMonto(disponible)}</b>${porDia}`;
    }

    const renovar = vencido
      ? `<button type="button" class="categoria-card__accion" data-accion="renovar" data-id="${id}"><i data-lucide="refresh-cw"></i><span>Renovar</span></button>`
      : `<button type="button" class="categoria-card__btn" data-accion="toggle" data-id="${id}" title="${p.is_activo ? 'Desactivar' : 'Activar'}" aria-label="${p.is_activo ? 'Desactivar' : 'Activar'}"><i data-lucide="${p.is_activo ? 'pause' : 'play'}"></i></button>`;

    return `
      <article class="categoria-card ${BARRA[nivel] ? `categoria-card--${BARRA[nivel]}` : ''}" data-activo="${p.is_activo && !vencido}"
               tabindex="0" role="button" aria-label="Editar presupuesto de ${P.esc(p.categoria_nombre)}"
               data-accion="editar" data-id="${id}">
        <div class="categoria-card__header">
          <div class="categoria-card__icon"><i data-lucide="${P.esc(p.categoria_icono || 'target')}"></i></div>
          <div class="categoria-card__titulo">
            <p class="categoria-card__nombre">${P.esc(p.categoria_nombre)}</p>
            <p class="categoria-card__cantidad">${P.esc(sub)}</p>
          </div>
          <span class="plan-chip plan-chip--${nivel}">${ETIQUETAS[nivel]}</span>
        </div>
        <p class="categoria-card__monto font-display">${P.formatMonto(p.gastado)}<small>de ${P.formatMonto(p.limite)} · ${pct}%</small></p>
        <div class="progress-bar"><div class="progress-bar__fill" data-pct="${pct}"></div></div>
        <div class="categoria-card__pie">
          <p class="categoria-card__info${disponible < 0 && !vencido ? ' categoria-card__info--aviso' : ''}">${info}</p>
          <div class="categoria-card__acciones">
            ${renovar}
            <button type="button" class="categoria-card__btn categoria-card__btn--peligro" data-accion="eliminar" data-id="${id}" title="Eliminar" aria-label="Eliminar"><i data-lucide="trash-2"></i></button>
          </div>
        </div>
      </article>`;
  }

  /* ── Acciones ────────────────────────────────────────────── */
  function buscar(id) {
    return estado.presupuestos.find(p => p.id === Number(id));
  }

  async function toggle(id) {
    const p = buscar(id);
    if (!p) return;
    try {
      await P.api(`${API}${p.id}/`, { method: 'PATCH', body: { is_activo: !p.is_activo } });
      P.toast(p.is_activo ? 'Presupuesto desactivado' : 'Presupuesto activado');
      cargar();
    } catch (e) {
      P.toast(e.message, 'error');
    }
  }

  async function renovar(id) {
    try {
      const respuesta = await P.api(`${API}${id}/renovar/`, { method: 'POST', body: {} });
      const nuevo = respuesta.data;
      P.toast(`Renovado del ${P.formatFecha(nuevo.fecha_inicio, true)} al ${P.formatFecha(nuevo.fecha_fin, true)}`);
      estado.filtro = 'activos';
      marcarFiltro();
      cargar();
    } catch (e) {
      P.toast(e.message, 'error');
    }
  }

  async function eliminar(id) {
    const p = buscar(id);
    const nombre = p ? p.categoria_nombre : 'este presupuesto';
    const ok = await P.confirmarEliminar('Eliminar presupuesto', `Se eliminará el presupuesto de "${nombre}". Esta acción no se puede deshacer.`);
    if (!ok) return;
    try {
      await P.api(`${API}${id}/`, { method: 'DELETE' });
      P.toast('Presupuesto eliminado');
      cargar();
    } catch (e) {
      P.toast(e.message, 'error');
    }
  }

  /* ── Formulario ──────────────────────────────────────────── */
  function setCategoria(id, nombre) {
    $('presupuesto-categoria').value = id || '';
    $('presupuesto-categoria-texto').textContent = nombre || 'Selecciona una categoría de egreso';
    $('presupuesto-categoria-btn').classList.toggle('has-value', !!id);
  }

  function marcarAtajo(clave) {
    document.querySelectorAll('#presupuesto-atajos .plan-opcion').forEach(b => {
      b.classList.toggle('is-activo', b.dataset.atajo === clave);
    });
  }

  function rangoAtajo(clave) {
    const hoy = P.parseISO(P.hoyISO());
    const y = hoy.getFullYear();
    const m = hoy.getMonth();
    const sumarDias = (f, n) => new Date(f.getFullYear(), f.getMonth(), f.getDate() + n);
    switch (clave) {
      case 'este-mes': return [hoy, new Date(y, m + 1, 0)];
      case 'proximo-mes': return [new Date(y, m + 1, 1), new Date(y, m + 2, 0)];
      case 'quincena': return [hoy, sumarDias(hoy, 14)];
      case '30-dias': return [hoy, sumarDias(hoy, 29)];
      default: return null;
    }
  }

  function aplicarAtajo(clave) {
    const rango = rangoAtajo(clave);
    if (!rango) return;
    estado.aplicandoAtajo = true;
    estado.dpInicio?.setValor(P.aISO(rango[0]));
    estado.dpFin?.setValor(P.aISO(rango[1]));
    estado.aplicandoAtajo = false;
    marcarAtajo(clave);
    actualizarRitmo();
  }

  /** Muestra cuánto se podría gastar por día con el límite y el período elegidos. */
  function actualizarRitmo() {
    const limite = P.leerMonto($('presupuesto-limite'));
    const inicio = $('presupuesto-inicio').value;
    const fin = $('presupuesto-fin').value;
    const hint = $('presupuesto-ritmo');
    if (!limite || !inicio || !fin || fin <= inicio) { hint.textContent = ''; return; }
    const dias = Math.round((P.parseISO(fin) - P.parseISO(inicio)) / 86400000) + 1;
    hint.textContent = `Equivale a ${P.formatMonto(limite / dias)} por día durante ${P.plural(dias, 'día', 'días')}`;
  }

  function abrirFormulario(p) {
    const editando = !!p;
    $('presupuesto-id').value = editando ? p.id : '';
    $('modal-presupuesto-titulo').textContent = editando ? 'Editar presupuesto' : 'Nuevo presupuesto';
    $('presupuesto-guardar-texto').textContent = editando ? 'Guardar cambios' : 'Crear presupuesto';
    setCategoria(editando ? p.categoria : '', editando ? p.categoria_nombre : '');
    P.setMonto($('presupuesto-limite'), editando ? p.limite : '');
    marcarAtajo(null);
    if (editando) {
      estado.dpInicio?.setValor(p.fecha_inicio);
      estado.dpFin?.setValor(p.fecha_fin);
    } else {
      aplicarAtajo('este-mes');
    }
    actualizarRitmo();
    P.abrirModal('modal-presupuesto');
  }

  async function guardar(e) {
    e.preventDefault();
    const id = $('presupuesto-id').value;
    const cuerpo = {
      categoria: $('presupuesto-categoria').value,
      limite: P.leerMonto($('presupuesto-limite')),
      fecha_inicio: $('presupuesto-inicio').value,
      fecha_fin: $('presupuesto-fin').value,
    };
    if (!cuerpo.categoria) return P.toast('Selecciona una categoría.', 'info');
    if (!cuerpo.limite) return P.toast('El límite debe ser mayor a 0.', 'info');
    if (!cuerpo.fecha_inicio || !cuerpo.fecha_fin) return P.toast('Indica las fechas del período.', 'info');
    if (cuerpo.fecha_fin <= cuerpo.fecha_inicio) return P.toast('La fecha final debe ser posterior a la inicial.', 'info');
    if (!id) cuerpo.is_activo = true;

    const boton = $('presupuesto-guardar');
    boton.disabled = true;
    try {
      await P.api(id ? `${API}${id}/` : API, { method: id ? 'PATCH' : 'POST', body: cuerpo });
      P.cerrarModal('modal-presupuesto');
      P.toast(id ? 'Cambios guardados' : 'Presupuesto creado');
      cargar();
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
        context: 'presupuestos',
        tipo: 'EGRESO',
        onSelect: cat => {
          setCategoria(cat.id, cat.nombre);
          P.cerrarModal('modal-categorias');
        },
      });
    }
    P.abrirModal('modal-categorias');
    setTimeout(() => $('buscador-categorias').focus(), 50);
  }

  function marcarFiltro() {
    document.querySelectorAll('#filtro-estado .plan-filtro__opcion').forEach(b => {
      b.classList.toggle('is-activo', b.dataset.filtro === estado.filtro);
    });
  }

  /* ── Eventos ─────────────────────────────────────────────── */
  function bindear() {
    P.initModales();
    P.initMonto($('presupuesto-limite'), actualizarRitmo);

    const alCambiarFecha = () => {
      if (!estado.aplicandoAtajo) marcarAtajo(null);
      actualizarRitmo();
    };
    estado.dpInicio = P.crearDatepicker($('presupuesto-inicio'), alCambiarFecha);
    estado.dpFin = P.crearDatepicker($('presupuesto-fin'), alCambiarFecha);

    $('btn-nuevo').addEventListener('click', () => abrirFormulario(null));
    $('form-presupuesto').addEventListener('submit', guardar);
    $('presupuesto-categoria-btn').addEventListener('click', abrirCategorias);
    $('buscador-categorias').addEventListener('input', e => window.CategoryPicker?.filter(e.target.value));
    $('presupuesto-atajos').addEventListener('click', e => {
      const btn = e.target.closest('[data-atajo]');
      if (btn) aplicarAtajo(btn.dataset.atajo);
    });

    $('buscador').addEventListener('input', e => {
      estado.busqueda = e.target.value.trim().toLowerCase();
      renderCards();
    });
    $('filtro-estado').addEventListener('click', e => {
      const btn = e.target.closest('[data-filtro]');
      if (!btn) return;
      estado.filtro = btn.dataset.filtro;
      marcarFiltro();
      renderCards();
    });

    document.querySelectorAll('[data-cerrar-banner]').forEach(btn => {
      btn.addEventListener('click', () => {
        const banner = $(btn.dataset.cerrarBanner);
        if (banner.id === 'banner-alertas') P.guardarSesion('presupuestos_alerta_cerrada', banner.dataset.firma || '');
        banner.hidden = true;
      });
    });

    P.activarCardsTeclado($('presupuestos-app'));
    $('presupuestos-app').addEventListener('click', e => {
      const btn = e.target.closest('[data-accion]');
      if (!btn) return;
      const id = btn.dataset.id;
      switch (btn.dataset.accion) {
        case 'nuevo': abrirFormulario(null); break;
        case 'editar': abrirFormulario(buscar(id)); break;
        case 'toggle': toggle(id); break;
        case 'renovar': renovar(id); break;
        case 'eliminar': eliminar(id); break;
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    window.CURRENT_MODULE = 'presupuestos';
    if (window.GastuTours) window.GastuTours.init(window.CURRENT_MODULE);
    bindear();
    cargar();
  });
})();

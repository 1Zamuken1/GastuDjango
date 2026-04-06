'use strict';

let movimientoEditandoId   = null;
let movimientoEliminandoId = null;
let categoriaActualId      = null;
let paginaActual           = 1;
let guardandoEnCurso       = false;

const modalMovimiento    = document.getElementById('modal-movimiento');
const modalRegistros     = document.getElementById('modal-registros');
const modalConfirmar     = document.getElementById('modal-confirmar-eliminar');
const formMovimiento     = document.getElementById('form-movimiento');
const tablaRegistrosBody = document.getElementById('tabla-registros-body');
const btnGuardar         = document.getElementById('btn-guardar');

/* ── Toast ──────────────────────────────────────────── */
function mostrarToast(msg, tipo = 'ok') {
  const t = document.createElement('div');
  t.className = `toast toast--${tipo}`;
  t.textContent = msg;
  document.getElementById('toast-container').appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

/* ── Errores ─────────────────────────────────────────── */
function limpiarErrores() {
  document.querySelectorAll('.form-error').forEach(el => el.textContent = '');
  document.querySelectorAll('.form-control').forEach(el => el.style.borderColor = '');
}
function mostrarErrores(errors) {
  Object.entries(errors).forEach(([campo, msgs]) => {
    const el = document.getElementById(`error-${campo}`);
    if (el) el.textContent = Array.isArray(msgs) ? msgs[0] : msgs;
    const inp = document.querySelector(`[name="${campo}"]`);
    if (inp) inp.style.borderColor = '#ef4444';
  });
}

/* ── Modal CRUD ──────────────────────────────────────── */
function abrirModalNuevo() {
  movimientoEditandoId = null;
  document.getElementById('modal-titulo').textContent = 'Nuevo egreso';
  formMovimiento.reset();
  limpiarErrores();
  /* Cerrar registros si está abierto — solo 1 modal a la vez */
  modalRegistros.setAttribute('hidden', '');
  modalMovimiento.removeAttribute('hidden');
}

function abrirModalEditar(id, descripcion, monto, fechaRaw, categoriaId) {
  movimientoEditandoId = id;
  document.getElementById('modal-titulo').textContent = 'Editar egreso';
  /* Cerrar registros primero — solo 1 modal a la vez */
  modalRegistros.setAttribute('hidden', '');
  /* Mostrar modal ANTES de poblar, para que el DOM esté activo */
  modalMovimiento.removeAttribute('hidden');
  /* Poblar campos */
  document.getElementById('campo-descripcion').value = descripcion;
  document.getElementById('campo-monto').value        = monto;
  document.getElementById('campo-categoria').value    = categoriaId;
  limpiarErrores();
}

function cerrarModalMovimiento() {
  modalMovimiento.setAttribute('hidden', '');
  formMovimiento.reset();
  limpiarErrores();
  /* Reabrir registros si había una categoría activa */
  if (categoriaActualId) {
    modalRegistros.removeAttribute('hidden');
  }
}

/* ── Modal confirmación eliminar ─────────────────────── */
function abrirModalConfirmar(id) {
  movimientoEliminandoId = id;
  modalConfirmar.removeAttribute('hidden');
}
function cerrarModalConfirmar() {
  /* NO limpiar movimientoEliminandoId aquí — lo usa el handler del botón confirmar */
  modalConfirmar.setAttribute('hidden', '');
}

document.getElementById('btn-cerrar-confirmar').addEventListener('click', () => {
  movimientoEliminandoId = null;
  cerrarModalConfirmar();
});
document.getElementById('btn-cancelar-eliminar').addEventListener('click', () => {
  movimientoEliminandoId = null;
  cerrarModalConfirmar();
});
modalConfirmar.addEventListener('click', (e) => {
  if (e.target === modalConfirmar) {
    movimientoEliminandoId = null;
    cerrarModalConfirmar();
  }
});

document.getElementById('btn-confirmar-eliminar').addEventListener('click', async () => {
  /* Capturar id ANTES de cerrar el modal (que no limpia la variable) */
  const id = movimientoEliminandoId;
  if (!id) return;
  movimientoEliminandoId = null;
  cerrarModalConfirmar();
  await ejecutarEliminar(id);
});

/* ── Actualizar grid sin recargar ────────────────────── */
async function actualizarGrid() {
  try {
    const res = await fetch(`${URL_RESUMEN}?tipo=EGRESO`, {
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
      grid.innerHTML = '<div class="grid-empty">Sin egresos registrados este mes</div>';
      return;
    }

    grid.innerHTML = data.categorias.map(cat => `
      <div class="categoria-card"
           data-categoria-id="${cat.id}"
           data-search-text="${cat.nombre.toLowerCase()}">
        <div class="categoria-card__header">
          <div>
            <p class="categoria-card__nombre">${cat.nombre}</p>
            <p class="categoria-card__cantidad">${cat.cantidad} registro${cat.cantidad !== 1 ? 's' : ''}</p>
          </div>
          <div class="categoria-card__icon"><i data-lucide="folder"></i></div>
        </div>
        <p class="categoria-card__monto font-display">${cat.total_fmt}</p>
        <div style="display:flex;align-items:center;gap:.5rem;margin:.5rem 0 .25rem;">
          <div class="progress-bar" style="flex:1;margin:0;">
            <div class="progress-bar__fill" data-porcentaje="${cat.porcentaje}"></div>
          </div>
          <span style="font-size:.72rem;font-weight:700;color:#e11d48;white-space:nowrap;min-width:2.5rem;text-align:right;">${cat.porcentaje}%</span>
        </div>
        <div class="categoria-card__footer">
          <i data-lucide="clock"></i> Último: ${cat.ultimo_registro}
        </div>
      </div>`).join('');

    document.querySelectorAll('.progress-bar__fill').forEach(el => {
      el.style.width = (parseFloat(el.dataset.porcentaje) || 0) + '%';
    });
    bindearCards();
    lucide.createIcons();
  } catch (e) {
    console.error('actualizarGrid error:', e);
  }
}

/* ── Submit form ─────────────────────────────────────── */
formMovimiento.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (guardandoEnCurso) return;
  guardandoEnCurso = true;
  btnGuardar.disabled = true;
  btnGuardar.textContent = 'Guardando...';
  limpiarErrores();
  const catGuardada = document.getElementById('campo-categoria').value;
  const url = movimientoEditandoId
    ? `${URL_EDITAR}${movimientoEditandoId}/`
    : URL_GUARDAR;

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': CSRF_TOKEN },
      body: new FormData(formMovimiento),
    });
    const data = await res.json();

    if (data.ok) {
      cerrarModalMovimiento();
      mostrarToast(movimientoEditandoId ? 'Egreso actualizado.' : 'Egreso registrado.', 'ok');
      await actualizarGrid();
      if (categoriaActualId) cargarRegistros(categoriaActualId, paginaActual);
      console.log('>>> catGuardada antes de check:', catGuardada);
      if (catGuardada) checkAlertasPresupuesto(catGuardada);
    } else {
      mostrarErrores(data.errors || {});
      mostrarToast('Revisa los campos del formulario.', 'error');
    }
  } catch (e) {
    mostrarToast('Error de conexión. Intenta de nuevo.', 'error');
  } finally {
    guardandoEnCurso = false;
    btnGuardar.disabled = false;
    btnGuardar.textContent = 'Guardar';
  }
});

/* ── Eliminar ────────────────────────────────────────── */
async function ejecutarEliminar(id) {
  try {
    const res = await fetch(`${URL_ELIMINAR}${id}/`, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': CSRF_TOKEN },
    });
    const data = await res.json();

    if (data.ok) {
      mostrarToast('Egreso eliminado.', 'ok');
      await actualizarGrid();

      const filasRestantes = tablaRegistrosBody.querySelectorAll('tr[data-id]').length;
      if (filasRestantes <= 1) {
        /* Era el último registro — cerrar modal de registros */
        modalRegistros.setAttribute('hidden', '');
        categoriaActualId = null;
      } else {
        cargarRegistros(categoriaActualId, paginaActual);
      }
    } else {
      mostrarToast('No se pudo eliminar.', 'error');
    }
  } catch (e) {
    mostrarToast('Error de conexión. Intenta de nuevo.', 'error');
  }
}

/* ── Modal registros ─────────────────────────────────── */
function bindearCards() {
  document.querySelectorAll('.categoria-card').forEach(card => {
    card.addEventListener('click', () => {
      categoriaActualId = card.dataset.categoriaId;
      paginaActual = 1;
      document.getElementById('modal-registros-titulo').textContent =
        card.querySelector('.categoria-card__nombre').textContent;
      modalRegistros.removeAttribute('hidden');
      cargarRegistros(categoriaActualId, paginaActual);
    });
  });
}

async function cargarRegistros(categoriaId, pagina) {
  tablaRegistrosBody.innerHTML =
    '<tr><td colspan="4" class="table-empty">Cargando...</td></tr>';

  try {
    const res = await fetch(
      `${URL_REGISTROS}?categoria=${categoriaId}&page=${pagina}`,
      { headers: { 'X-Requested-With': 'XMLHttpRequest' } }
    );

    // ← NUEVO: detectar respuestas no-JSON antes de parsear
    if (!res.ok) {
      const texto = await res.text();
      console.error(`[registros] HTTP ${res.status}:`, texto);
      tablaRegistrosBody.innerHTML =
        `<tr><td colspan="4" class="table-empty">Error ${res.status} — revisa la consola.</td></tr>`;
      return;
    }

    const data = await res.json();
    // ... resto igual

    tablaRegistrosBody.innerHTML = data.registros.length
      ? data.registros.map(r => `
          <tr data-id="${r.id}">
            <td>${r.descripcion}</td>
            <td class="text-muted">${r.fecha}</td>
            <td><span class="monto monto--egreso">${r.monto_fmt}</span></td>
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

    tablaRegistrosBody.querySelectorAll('.btn-editar').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        abrirModalEditar(
          btn.dataset.id,
          btn.dataset.descripcion,
          btn.dataset.monto,
          btn.dataset.fecha,
          btn.dataset.categoria
        );
      });
    });
    tablaRegistrosBody.querySelectorAll('.btn-eliminar').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        abrirModalConfirmar(btn.dataset.id);
      });
    });
  } catch (e) {
    tablaRegistrosBody.innerHTML =
      '<tr><td colspan="4" class="table-empty">Error al cargar registros.</td></tr>';
  }
}

document.getElementById('btn-pag-anterior').addEventListener('click', () => {
  if (paginaActual > 1) cargarRegistros(categoriaActualId, --paginaActual);
});
document.getElementById('btn-pag-siguiente').addEventListener('click', () => {
  cargarRegistros(categoriaActualId, ++paginaActual);
});

/* ── Buscador ────────────────────────────────────────── */
let debounceTimer = null;

document.getElementById('buscador').addEventListener('input', (e) => {
  const q = e.target.value.trim();
  clearTimeout(debounceTimer);

  if (!q) {
    /* Sin query: restaurar todas las cards */
    document.querySelectorAll('.categoria-card').forEach(card => {
      card.style.display = '';
      card.style.outline = '';
    });
    return;
  }

  debounceTimer = setTimeout(async () => {
    const qLower = q.toLowerCase();

    /* Filtro DOM inmediato por nombre de categoría mientras llega el fetch */
    document.querySelectorAll('.categoria-card').forEach(card => {
      card.style.display = card.dataset.searchText.includes(qLower) ? '' : 'none';
      card.style.outline = '';
    });

    /* Fetch al backend — busca en descripción, monto y fecha */
    try {
      const res = await fetch(
        `${URL_BUSCAR}?q=${encodeURIComponent(q)}&tipo=EGRESO`,
        { headers: { 'X-Requested-With': 'XMLHttpRequest' } }
      );
      const data = await res.json();
      if (!data.ok) return;

      const idsConResultados = new Set(data.categoria_ids.map(String));

      /* Si el backend encontró resultados, usarlos como fuente de verdad */
      if (idsConResultados.size > 0) {
        document.querySelectorAll('.categoria-card').forEach(card => {
          const tiene = idsConResultados.has(card.dataset.categoriaId);
          card.style.display = tiene ? '' : 'none';
          card.style.outline = tiene ? '2px solid #e11d48' : '';
        });
      }
    } catch (err) {
      console.error('buscar error:', err);
    }
  }, 300);
});

/* ── Eventos cierre ──────────────────────────────────── */
document.getElementById('btn-nuevo').addEventListener('click', abrirModalNuevo);
document.getElementById('btn-cerrar-modal').addEventListener('click', cerrarModalMovimiento);
document.getElementById('btn-cancelar-modal').addEventListener('click', cerrarModalMovimiento);
document.getElementById('btn-cerrar-registros').addEventListener('click', () => {
  modalRegistros.setAttribute('hidden', '');
  categoriaActualId = null;
});
modalMovimiento.addEventListener('click', (e) => {
  if (e.target === modalMovimiento) cerrarModalMovimiento();
});
modalRegistros.addEventListener('click', (e) => {
  if (e.target === modalRegistros) {
    modalRegistros.setAttribute('hidden', '');
    categoriaActualId = null;
  }
});
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  if (!modalConfirmar.hasAttribute('hidden')) {
    movimientoEliminandoId = null;
    cerrarModalConfirmar();
  } else if (!modalMovimiento.hasAttribute('hidden')) {
    cerrarModalMovimiento();
  } else if (!modalRegistros.hasAttribute('hidden')) {
    modalRegistros.setAttribute('hidden', '');
    categoriaActualId = null;
  }
});

/* ── Init ────────────────────────────────────────────── */
document.querySelectorAll('.progress-bar__fill').forEach(el => {
  el.style.width = (parseFloat(el.dataset.porcentaje) || 0) + '%';
});
bindearCards();
lucide.createIcons();

/* ── Picker de categorías ────────────────────────────── */
(function () {
  const modalPicker   = document.getElementById('modal-picker-cat');
  const btnPicker     = document.getElementById('btn-picker-categoria');
  const pickerLabel   = document.getElementById('picker-cat-label');
  const inputCat      = document.getElementById('campo-categoria');
  const buscadorPick  = document.getElementById('picker-buscador');

  if (!modalPicker || !btnPicker) return;

  function abrirPicker() {
    buscadorPick.value = '';
    filtrarPicker('');
    /* Marcar la card ya seleccionada */
    const selId = inputCat.value;
    document.querySelectorAll('.picker-cat-card').forEach(card => {
      card.classList.toggle('selected', card.dataset.id === selId);
    });
    /* Actualizar label del footer */
    const selLabel = document.getElementById('picker-seleccionado-label');
    if (selLabel) {
      const selCard = document.querySelector(`.picker-cat-card[data-id="${selId}"]`);
      selLabel.textContent = selCard ? `Seleccionado: ${selCard.dataset.nombre}` : '';
    }
    modalPicker.removeAttribute('hidden');
    lucide.createIcons();
    setTimeout(() => buscadorPick.focus(), 50);
  }

  function cerrarPicker() {
    modalPicker.setAttribute('hidden', '');
  }

  function filtrarPicker(q) {
    const qLower = q.toLowerCase().trim();
    document.querySelectorAll('.picker-cat-card').forEach(card => {
      const nombre = card.dataset.nombre.toLowerCase();
      card.style.display = nombre.includes(qLower) ? '' : 'none';
    });
  }

  function seleccionarCategoria(id, nombre) {
    inputCat.value          = id;
    pickerLabel.textContent = nombre;
    pickerLabel.style.color = 'var(--slate-900)';
    btnPicker.style.borderColor = '';
    /* Marcar card seleccionada visualmente */
    document.querySelectorAll('.picker-cat-card').forEach(card => {
      card.classList.toggle('selected', card.dataset.id === id);
    });
    cerrarPicker();
  }

  btnPicker.addEventListener('click', (e) => {
    e.stopPropagation();
    abrirPicker();
  });

  document.getElementById('btn-cerrar-picker').addEventListener('click', cerrarPicker);
  document.getElementById('btn-cancelar-picker').addEventListener('click', cerrarPicker);
  modalPicker.addEventListener('click', (e) => {
    if (e.target === modalPicker) cerrarPicker();
  });

  document.getElementById('picker-grid').addEventListener('click', (e) => {
    const card = e.target.closest('.picker-cat-card');
    if (card) seleccionarCategoria(card.dataset.id, card.dataset.nombre);
  });

  buscadorPick.addEventListener('input', (e) => {
    filtrarPicker(e.target.value);
  });

  /* Integrar con el ciclo de vida de los modales CRUD */
  const _origNuevo  = window.abrirModalNuevo  || abrirModalNuevo;
  const _origEditar = window.abrirModalEditar || abrirModalEditar;
  const _origCerrar = window.cerrarModalMovimiento || cerrarModalMovimiento;

  window.abrirModalNuevo = function () {
    _origNuevo();
    inputCat.value = '';
    pickerLabel.textContent = 'Seleccionar categoría';
    pickerLabel.style.color = '';
  };

  window.abrirModalEditar = function (id, descripcion, monto, fechaRaw, categoriaId) {
    _origEditar(id, descripcion, monto, fechaRaw, categoriaId);
    /* Buscar el nombre de la categoría en las cards del picker */
    const card = document.querySelector(`.picker-cat-card[data-id="${categoriaId}"]`);
    if (card) {
      pickerLabel.textContent = card.dataset.nombre;
      pickerLabel.style.color = 'var(--slate-900)';
    }
  };

  window.cerrarModalMovimiento = function () {
    _origCerrar();
    inputCat.value = '';
    pickerLabel.textContent = 'Seleccionar categoría';
    pickerLabel.style.color = '';
  };

  /* Escape cierra el picker con prioridad */
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modalPicker.hasAttribute('hidden')) {
      e.stopImmediatePropagation();
      cerrarPicker();
    }
  }, true);
})();

/* ── Nuevo desde modal registros (hereda categoría) ─── */
document.getElementById('btn-nuevo-desde-registros').addEventListener('click', () => {
  /* Guardar categoría activa antes de que abrirModalNuevo cierre el modal */
  const catId     = categoriaActualId;
  const catNombre = document.getElementById('modal-registros-titulo').textContent;

  /* Abrir el modal CRUD limpio */
  window.abrirModalNuevo();

  /* Preseleccionar la categoría heredada en el picker */
  const inputCat    = document.getElementById('campo-categoria');
  const pickerLabel = document.getElementById('picker-cat-label');
  if (inputCat && pickerLabel && catId) {
    inputCat.value          = catId;
    pickerLabel.textContent = catNombre;
    pickerLabel.style.color = 'var(--slate-900)';
    /* Marcar visualmente la card en el picker */
    document.querySelectorAll('.picker-cat-card').forEach(card => {
      card.classList.toggle('selected', card.dataset.id === catId);
    });
  }
});

/* ── Modal de reporte ────────────────────────────────── */
const modalReporte = document.getElementById('modal-reporte');
let formatoReporte = 'csv';
let dpDesde = null;
let dpHasta = null;

const URL_EXPORTAR = {
  csv:   URL_EXPORTAR_CSV,
  excel: URL_EXPORTAR_EXCEL,
  pdf:   URL_EXPORTAR_PDF,
};

const LABEL_ICONO = { csv: 'file-spreadsheet', excel: 'table-2', pdf: 'file-text' };
const LABEL_FORMATO = { csv: 'CSV', excel: 'Excel (.xlsx)', pdf: 'PDF' };

function _inicializarDatepickers() {
  if (!dpDesde) {
    const inputDesde = document.getElementById('dp-input-desde');
    const inputHasta = document.getElementById('dp-input-hasta');
    if (!inputDesde || !inputHasta) return;

    const lblDesde = inputDesde.parentNode;
    const lblHasta = inputHasta.parentNode;

    dpDesde = new MiniDatepicker(inputDesde, { acento: 'egreso' });
    dpHasta = new MiniDatepicker(inputHasta, { acento: 'egreso' });

    /* Reordenar: label luego dp-wrapper */
    lblDesde.appendChild(dpDesde.wrapper);
    lblHasta.appendChild(dpHasta.wrapper);
  }
}

function abrirModalReporte(formato) {
  formatoReporte = formato;
  document.getElementById('modal-reporte-formato-label').textContent =
    'Formato: ' + LABEL_FORMATO[formato];

  _inicializarDatepickers();

  /* Fechas por defecto: primer día del mes actual hasta hoy */
  const hoy = new Date();
  const primerDia = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
  dpDesde.setValor(primerDia.toISOString().split('T')[0]);
  dpHasta.setValor(hoy.toISOString().split('T')[0]);

  cargarCategoriasReporte();
  modalReporte.removeAttribute('hidden');
  lucide.createIcons();
}

function cargarCategoriasReporte() {
  const contenedor = document.getElementById('reporte-categorias');
  const cards = document.querySelectorAll('.categoria-card');
  if (cards.length === 0) {
    contenedor.innerHTML = '<span style="font-size:.78rem;color:var(--slate-500);">Sin categorías con actividad este mes.</span>';
    actualizarCountReporte();
    return;
  }
  contenedor.innerHTML = Array.from(cards).map(card => {
    const id     = card.dataset.categoriaId;
    const nombre = card.querySelector('.categoria-card__nombre').textContent;
    return `<label style="display:inline-flex;align-items:center;gap:.3rem;
                          font-size:.78rem;cursor:pointer;padding:.25rem .5rem;
                          border-radius:.375rem;border:1px solid var(--border);
                          background:#fff;white-space:nowrap;transition:border-color .13s;">
      <input type="checkbox" value="${id}" class="cat-check" checked
             style="accent-color:#10b981;">
      ${nombre}
    </label>`;
  }).join('');
  actualizarCountReporte();
}

function actualizarCountReporte() {
  const total    = document.querySelectorAll('.cat-check').length;
  const marcadas = document.querySelectorAll('.cat-check:checked').length;
  const el = document.getElementById('reporte-count');
  if (el) el.textContent = `${marcadas} de ${total} categoría${total !== 1 ? 's' : ''} seleccionada${total !== 1 ? 's' : ''}`;
}

document.getElementById('reporte-categorias').addEventListener('change', actualizarCountReporte);

document.getElementById('btn-todas-cats').addEventListener('click', () => {
  document.querySelectorAll('.cat-check').forEach(c => c.checked = true);
  actualizarCountReporte();
});

document.getElementById('btn-ninguna-cat').addEventListener('click', () => {
  document.querySelectorAll('.cat-check').forEach(c => c.checked = false);
  actualizarCountReporte();
});

document.getElementById('btn-descargar-reporte').addEventListener('click', () => {
  const desde  = dpDesde ? dpDesde.getValor() : '';
  const hasta  = dpHasta ? dpHasta.getValor() : '';
  const catIds = Array.from(document.querySelectorAll('.cat-check:checked'))
                      .map(c => c.value).join(',');

  const params = new URLSearchParams({
    tipo: 'EGRESO',
    fecha_desde: desde,
    fecha_hasta: hasta,
  });
  if (catIds) params.set('categorias', catIds);

  window.location.href = `${URL_EXPORTAR[formatoReporte]}?${params.toString()}`;
  cerrarModalReporte();
});

function cerrarModalReporte() {
  modalReporte.setAttribute('hidden', '');
}

document.getElementById('btn-cerrar-reporte').addEventListener('click', cerrarModalReporte);
document.getElementById('btn-cancelar-reporte').addEventListener('click', cerrarModalReporte);
modalReporte.addEventListener('click', (e) => {
  if (e.target === modalReporte) cerrarModalReporte();
});

/* Conectar botones del toolbar */
document.querySelector('.btn-export--pdf').addEventListener('click',   () => abrirModalReporte('pdf'));
document.querySelector('.btn-export--excel').addEventListener('click', () => abrirModalReporte('excel'));
document.querySelector('.btn-export--csv').addEventListener('click',   () => abrirModalReporte('csv'));
/* ── Alertas de presupuesto al insertar egreso ───────── */
const ALERTA_CONFIGS = {
  nivel_50: { color: '#facc15', titulo: 'Presupuesto al 50%',  icono: '' },
  nivel_55: { color: '#facc15', titulo: 'Presupuesto al 55%',  icono: '' },
  nivel_60: { color: '#fb923c', titulo: 'Presupuesto al 60%',  icono: '' },
  nivel_65: { color: '#fb923c', titulo: 'Presupuesto al 65%',  icono: '' },
  nivel_70: { color: '#f97316', titulo: 'Presupuesto al 70%',  icono: '' },
  nivel_75: { color: '#f97316', titulo: 'Presupuesto al 75%',  icono: '' },
  nivel_80: { color: '#f97316', titulo: 'Presupuesto al 80%',  icono: '' },
  nivel_85: { color: '#ef4444', titulo: 'Presupuesto al 85%',  icono: '' },
  nivel_90: { color: '#ef4444', titulo: 'Presupuesto al 90%',  icono: '' },
  nivel_95: { color: '#ef4444', titulo: 'Presupuesto al 95%',  icono: '' },
  critica:  { color: '#b91c1c', titulo: '¡Límite superado!',   icono: '' },
};

function alertaPresupuestoYaVista(presupuestoId, nivel) {
  return !!localStorage.getItem(`alerta_vista_${presupuestoId}_${nivel}`);
}

function marcarAlertaPresupuestoVista(presupuestoId, nivel) {
  ['baja','nivel_50','nivel_55','nivel_60','nivel_65','nivel_70',
   'nivel_75','nivel_80','nivel_85','nivel_90','nivel_95','critica'].forEach(n => {
    localStorage.removeItem(`alerta_vista_${presupuestoId}_${n}`);
  });
  localStorage.setItem(`alerta_vista_${presupuestoId}_${nivel}`, '1');
}

function mostrarModalAlertaPresupuesto(alerta) {
  const cfg = ALERTA_CONFIGS[alerta.alerta];
  if (!cfg) return;

  document.getElementById('modal-alerta-presupuesto')?.remove();

  const modal = document.createElement('div');
  modal.id = 'modal-alerta-presupuesto';
  modal.style.cssText = `
    position:fixed; bottom:24px; right:24px; z-index:99999;
    width:min(340px,92vw); background:#fff; border-radius:12px;
    box-shadow:0 8px 32px rgba(0,0,0,0.18);
    border-left:5px solid ${cfg.color};
    padding:16px 18px 14px 16px;
    display:flex; flex-direction:column; gap:6px;
    animation:slideInRight .3s ease;
  `;
  modal.innerHTML = `
    <style>
      @keyframes slideInRight {
        from { transform:translateX(110%); opacity:0; }
        to   { transform:translateX(0);   opacity:1; }
      }
    </style>
    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
      <span style="font-size:1rem;font-weight:700;color:#0f172a;">
        ${cfg.icono} ${cfg.titulo}
      </span>
      <button id="btn-cerrar-alerta-presupuesto"
              style="background:none;border:none;cursor:pointer;color:#94a3b8;font-size:1.1rem;line-height:1;padding:0 2px;">✕</button>
    </div>
    <p style="margin:0;font-size:.85rem;color:#334155;line-height:1.45;">
      Llevas <strong>${alerta.porcentaje}%</strong> del presupuesto
      en <strong>"${alerta.categoria}"</strong>.
    </p>
    <div style="background:#f1f5f9;border-radius:6px;height:6px;margin-top:4px;">
      <div style="width:${Math.min(alerta.porcentaje,100)}%;background:${cfg.color};height:6px;border-radius:6px;"></div>
    </div>
    <p style="margin:0;font-size:.75rem;color:#94a3b8;text-align:right;">
      $${alerta.gastado.toLocaleString('es-CO')} / $${alerta.limite.toLocaleString('es-CO')}
    </p>
  `;
  document.body.appendChild(modal);

  const cerrar = () => {
    modal.style.transition = 'all .25s ease';
    modal.style.opacity    = '0';
    modal.style.transform  = 'translateX(110%)';
    setTimeout(() => modal.remove(), 260);
  };
  document.getElementById('btn-cerrar-alerta-presupuesto').addEventListener('click', cerrar);
  setTimeout(cerrar, 7000);
}

async function checkAlertasPresupuesto(categoriaId) {
  console.log('>>> CHECK llamado, categoriaId:', categoriaId);
  try {
    const res = await fetch('/api/presupuestos/alertas/', {
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': CSRF_TOKEN }
    });
    console.log('>>> HTTP status:', res.status);
    const data = await res.json();
    console.log('>>> data completa:', data);
    console.log('>>> alertas recibidas:', data.alertas);

    const filtradas = (data.alertas || []).filter(a => {
      console.log(`>>> comparando a.categoria_id=${a.categoria_id} con categoriaId=${categoriaId}, alerta=${a.alerta}`);
      return String(a.categoria_id) === String(categoriaId) && a.alerta !== 'baja';
    });

    console.log('>>> alertas filtradas:', filtradas);

    filtradas.forEach(alerta => {
      const yaVista = alertaPresupuestoYaVista(alerta.id, alerta.alerta);
      console.log(`>>> alerta id=${alerta.id} nivel=${alerta.alerta} yaVista=${yaVista}`);
      if (yaVista) return;
      mostrarModalAlertaPresupuesto(alerta);
      marcarAlertaPresupuestoVista(alerta.id, alerta.alerta);
    });
  } catch (e) {
    console.error('>>> checkAlertasPresupuesto ERROR:', e);
  }
}
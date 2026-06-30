'use strict';

/* ══════════════════════════════════════════════════════════
   ahorros.js — lógica completa de la vista lista de ahorros
   ══════════════════════════════════════════════════════════ */

/* ── URLs inyectadas desde el template via bloque <script> en lista.html
   URL_EXPORTAR_CSV, URL_EXPORTAR_EXCEL, URL_EXPORTAR_PDF
   URL_CREAR_META, URL_EDITAR_META, URL_ELIMINAR_META, CSRF_TOKEN
   ─────────────────────────────────────────────────────────────────────── */


/* ══════════════════════════════════════════════════════════
   1. BARRAS DE PROGRESO
   ══════════════════════════════════════════════════════════ */

document.querySelectorAll('.progress-bar__fill').forEach(bar => {
  const actual   = parseFloat(bar.dataset.actual)   || 0;
  const objetivo = parseFloat(bar.dataset.objetivo) || 0;
  const pct      = objetivo > 0 ? Math.min(100, (actual / objetivo) * 100) : 0;
  bar.style.width = pct.toFixed(1) + '%';

  const id  = bar.id.replace('bar-', '');
  const lbl = document.getElementById('pct-' + id);
  if (lbl) lbl.textContent = pct.toFixed(1) + '%';
});


/* ══════════════════════════════════════════════════════════
   2. BUSCADOR DE METAS
   ══════════════════════════════════════════════════════════ */

const buscador = document.getElementById('buscador-metas');
if (buscador) {
  buscador.addEventListener('input', () => {
    const q = buscador.value.toLowerCase().trim();
    document.querySelectorAll('#grid-metas .categoria-card').forEach(card => {
      const txt = (card.dataset.searchText || '').toLowerCase();
      card.style.display = txt.includes(q) ? '' : 'none';
    });
  });
}


/* ══════════════════════════════════════════════════════════
   3. TOAST
   ══════════════════════════════════════════════════════════ */

function mostrarToast(mensaje, tipo = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const colores = {
    success: { bg: '#f0fdf4', border: '#86efac', text: '#15803d', icon: 'check-circle' },
    error:   { bg: '#fef2f2', border: '#fca5a5', text: '#dc2626', icon: 'alert-circle' },
    info:    { bg: '#eff6ff', border: '#93c5fd', text: '#1d4ed8', icon: 'info' },
  };
  const c = colores[tipo] || colores.info;

  const toast = document.createElement('div');
  toast.style.cssText = `
    background:${c.bg};border:1px solid ${c.border};color:${c.text};
    padding:.75rem 1rem;border-radius:.75rem;font-size:.85rem;font-weight:600;
    display:flex;align-items:center;gap:.5rem;
    box-shadow:0 4px 16px rgba(0,0,0,.08);
    animation:fadeIn .2s ease;max-width:320px;
  `;
  toast.innerHTML = `<i data-lucide="${c.icon}" style="width:16px;height:16px;flex-shrink:0;"></i>${mensaje}`;
  container.appendChild(toast);
  lucide.createIcons();
  setTimeout(() => toast.remove(), 4000);
}


/* ══════════════════════════════════════════════════════════
   4. MODAL APORTES (fetch de parcial HTML)
   ══════════════════════════════════════════════════════════ */

const overlayAporte = document.getElementById('modal-overlay-aporte');

function abrirModalAporte(url) {
  overlayAporte.style.display = 'flex';
  overlayAporte.removeAttribute('hidden');
  overlayAporte.innerHTML = `
    <div style="background:#fff;border-radius:1.25rem;padding:2rem;color:#64748b;font-size:.85rem;
                display:flex;align-items:center;gap:.75rem;">
      <i data-lucide="loader" style="width:20px;height:20px;animation:spin .7s linear infinite;"></i>
      Cargando...
    </div>`;
  lucide.createIcons();

  fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(r => r.text())
    .then(html => {
      overlayAporte.innerHTML = html;
      lucide.createIcons();
      calcularTiemposRestantes(overlayAporte);
      
      bindMontoFormatter(overlayAporte.querySelector('#aporte-extra-monto'));

      overlayAporte.querySelectorAll('.btn-cerrar-modal-aporte').forEach(btn => {
        btn.addEventListener('click', cerrarModalAporte);
      });
      overlayAporte.querySelectorAll('.form-aporte-modal').forEach(form => {
        form.addEventListener('submit', e => enviarAporte(e, url));
      });
    })
    .catch(() => {
      overlayAporte.innerHTML = `<div style="background:#fff;border-radius:1.25rem;padding:2rem;color:#dc2626;">
        Error al cargar el modal de aporte.</div>`;
    });
}

function cerrarModalAporte() {
  overlayAporte.setAttribute('hidden', '');
  overlayAporte.style.display = 'none';
  overlayAporte.innerHTML = '';
}

function calcularTiemposRestantes(container) {
  const hoy = new Date();
  hoy.setHours(0,0,0,0);

  container.querySelectorAll('.cuotas-table__tiempo').forEach(celda => {
    const estado = celda.dataset.estado;
    if (estado === 'APORTADO') {
      celda.textContent = '—';
      return;
    }

    const fechaStr = celda.dataset.fechaLimite;
    if (!fechaStr) return;

    const partes = fechaStr.split('-');
    const limite = new Date(partes[0], partes[1] - 1, partes[2]);
    limite.setHours(0,0,0,0);

    const diffTime = limite - hoy;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays < 0) {
      celda.textContent = 'Vencida';
      celda.style.color = '#ef4444';
    } else if (diffDays === 0) {
      celda.textContent = 'Hoy';
      celda.style.color = '#eab308';
    } else if (diffDays === 1) {
      celda.textContent = '1 día';
    } else if (diffDays < 30) {
      celda.textContent = `${diffDays} días`;
    } else if (diffDays < 60) {
      celda.textContent = '1 mes';
    } else {
      const meses = Math.floor(diffDays / 30);
      celda.textContent = `${meses} meses`;
    }
  });
}

async function enviarAporte(e, url) {
  e.preventDefault();
  const form = e.currentTarget;
  const data = new FormData(form);

  const inputExtra = form.querySelector('#aporte-extra-monto');
  if (inputExtra && inputExtra.dataset.raw && form.contains(inputExtra)) {
    data.set('aporte', inputExtra.dataset.raw);
  }

  try {
    const res  = await fetch(form.action, { method: 'POST', body: data });
    const json = await res.json();

    if (json.ok) {
      cerrarModalAporte();
      mostrarToast(json.message || 'Aporte registrado', 'success');
      setTimeout(() => location.reload(), 700);
    } else {
      const errContainer = overlayAporte.querySelector('#modal-error-container');
      const errMsg       = overlayAporte.querySelector('#modal-error-message');
      if (errContainer && errMsg) {
        errMsg.textContent = json.error || 'Error al registrar el aporte.';
        errContainer.removeAttribute('hidden');
        errContainer.style.display = 'flex';
        errContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } else {
        mostrarToast(json.error || 'Error al registrar el aporte.', 'error');
      }
    }
  } catch {
    mostrarToast('Error de conexion al registrar el aporte.', 'error');
  }
}

overlayAporte.addEventListener('click', e => {
  if (e.target === overlayAporte) cerrarModalAporte();
});

document.querySelectorAll('.btn-abrir-modal-aporte').forEach(btn => {
  btn.addEventListener('click', () => abrirModalAporte(btn.dataset.url));
});


/* ══════════════════════════════════════════════════════════
   5. PICKER DE CATEGORÍAS (modal compartido entre crear/editar)
   ══════════════════════════════════════════════════════════ */

const modalPicker          = document.getElementById('modal-picker-cat');
const pickerGrid           = document.getElementById('picker-grid');
const pickerBuscador       = document.getElementById('picker-buscador');
const pickerSelLabel       = document.getElementById('picker-seleccionado-label');
let   _pickerCallback      = null;

if (window.CategoryPicker && modalPicker) {
  CategoryPicker.init({
    containerId: 'picker-grid',
    tipo: 'AHORRO',
    context: 'ahorros',
    onSelect: function(cat) {
      if (_pickerCallback) _pickerCallback(cat.id, cat.nombre);
      if (pickerSelLabel) pickerSelLabel.textContent = `Seleccionado: ${cat.nombre}`;
      cerrarPicker();
    }
  });
}

function abrirPicker(callback) {
  _pickerCallback = callback;
  if (pickerBuscador) pickerBuscador.value = '';
  if (window.CategoryPicker) CategoryPicker.filter('');
  modalPicker.removeAttribute('hidden');
  if (pickerSelLabel) pickerSelLabel.textContent = '';
}

function cerrarPicker() {
  modalPicker.setAttribute('hidden', '');
}

if (pickerBuscador) {
  pickerBuscador.addEventListener('input', () => {
    if (window.CategoryPicker) CategoryPicker.filter(pickerBuscador.value);
  });
}

document.getElementById('btn-cerrar-picker')?.addEventListener('click', cerrarPicker);
document.getElementById('btn-cancelar-picker')?.addEventListener('click', cerrarPicker);
modalPicker?.addEventListener('click', e => {
  if (e.target === modalPicker) cerrarPicker();
});


/* ══════════════════════════════════════════════════════════
   6. PLAZO TOGGLE — selector mutuamente exclusivo cuotas / fecha
   ══════════════════════════════════════════════════════════ */

/**
 * Cambia el panel activo del toggle de plazo.
 * Al cambiar, limpia el campo del otro panel para que el backend
 * nunca reciba cuotas y fecha al mismo tiempo.
 *
 * @param {string} prefix  - 'crear' | 'editar'
 * @param {string} modo    - 'cuotas' | 'fecha'
 */
function switchPlazo(prefix, modo) {
  const panelCuotas = document.getElementById(`panel-${prefix}-cuotas`);
  const panelFecha  = document.getElementById(`panel-${prefix}-fecha`);
  const tabCuotas   = document.getElementById(`tab-${prefix}-cuotas`);
  const tabFecha    = document.getElementById(`tab-${prefix}-fecha`);
  const inputCuotas = document.getElementById(`${prefix}-cuotas`);
  const inputFecha  = document.getElementById(`${prefix}-fecha-meta`);

  // Leer el datepicker en el momento de ejecucion (las variables dpCrear/dpEditar
  // son null al inicio del script y se asignan en DOMContentLoaded; leerlas aqui
  // garantiza que siempre tengamos la instancia real, no el null inicial)
  const dpActual = prefix === 'crear' ? dpCrear : dpEditar;

  if (modo === 'cuotas') {
    panelCuotas.removeAttribute('hidden');
    panelFecha.setAttribute('hidden', '');
    tabCuotas.classList.add('active');
    tabCuotas.setAttribute('aria-selected', 'true');
    tabFecha.classList.remove('active');
    tabFecha.setAttribute('aria-selected', 'false');
    // limpiar() resetea this.valor, el input hidden Y el texto visual del display
    // setValor('') no sirve porque tiene un guard "if (!isoStr) return" al inicio
    if (dpActual && typeof dpActual.limpiar === 'function') dpActual.limpiar();


  } else {
    panelFecha.removeAttribute('hidden');
    panelCuotas.setAttribute('hidden', '');
    tabFecha.classList.add('active');
    tabFecha.setAttribute('aria-selected', 'true');
    tabCuotas.classList.remove('active');
    tabCuotas.setAttribute('aria-selected', 'false');
    // Limpiar cuotas para que el backend no reciba ambos
    if (inputCuotas) inputCuotas.value = '';
    // Limpiar tambien el datepicker por si vuelve al panel de fecha tras haber
    // estado en cuotas (el display mostraria una fecha vieja de una sesion anterior)
    if (dpActual && typeof dpActual.limpiar === 'function') dpActual.limpiar();
  }

  lucide.createIcons();
}

/**
 * Inicializa el toggle al abrir un modal.
 * Detecta el modo correcto según los valores existentes (útil para editar).
 *
 * @param {string}      prefix           - 'crear' | 'editar'
 * @param {string|null} fechaExistente   - 'YYYY-MM-DD' o null
 * @param {number|null} cuotasExistentes - número o null
 */
function initPlazoToggle(prefix, fechaExistente = null, cuotasExistentes = null) {
  // Si hay fecha y NO hay cuotas → modo fecha; en cualquier otro caso → cuotas (default)
  const modoInicial = (fechaExistente && !cuotasExistentes) ? 'fecha' : 'cuotas';
  switchPlazo(prefix, modoInicial);

  if (cuotasExistentes) {
    const inp = document.getElementById(`${prefix}-cuotas`);
    if (inp) inp.value = cuotasExistentes;
  }
  if (fechaExistente) {
    const inp = document.getElementById(`${prefix}-fecha-meta`);
    if (inp) inp.value = fechaExistente;
    const dpVar = prefix === 'crear' ? dpCrear : dpEditar;
    if (dpVar && typeof dpVar.setValor === 'function') dpVar.setValor(fechaExistente);
  }
}


/* ══════════════════════════════════════════════════════════
   7. MODAL CREAR META
   ══════════════════════════════════════════════════════════ */

const modalCrear     = document.getElementById('modal-crear-meta');
const formCrear      = document.getElementById('form-crear-meta');
const crearErrors    = document.getElementById('crear-errors');
const crearErrorsTxt = document.getElementById('crear-errors-text');

function abrirModalCrear() {
  formCrear.reset();
  document.getElementById('crear-categoria').value = '';
  document.getElementById('crear-cat-label').textContent = 'Seleccionar categoría';
  document.getElementById('crear-cat-btn').classList.remove('selected');

  const fLabel = document.getElementById('crear-frecuencia-label');
  if (fLabel) {
    document.getElementById('crear-frecuencia').value = '';
    fLabel.textContent = 'Seleccionar Frecuencia';
    fLabel.style.color = 'var(--slate-500)';
  }

  ocultarErroresCrear();
  modalCrear.removeAttribute('hidden');
  lucide.createIcons();
  // Inicializar toggle en modo cuotas por defecto
  initPlazoToggle('crear', null, null);
  modalCrear.querySelector('.modal__body').scrollTop = 0;
}

function cerrarModalCrear() {
  modalCrear.setAttribute('hidden', '');
}

function mostrarErroresCrear(errors) {
  const msgs = Object.values(errors).flat().join(' · ');
  crearErrorsTxt.textContent = msgs;
  crearErrors.style.display = 'flex';
  lucide.createIcons();
  crearErrors.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function ocultarErroresCrear() {
  crearErrors.style.display = 'none';
  crearErrorsTxt.textContent = '';
}

document.getElementById('crear-cat-btn').addEventListener('click', () => {
  abrirPicker((id, nombre) => {
    document.getElementById('crear-categoria').value = id;
    const lbl = document.getElementById('crear-cat-label');
    lbl.textContent = nombre;
    document.getElementById('crear-cat-btn').classList.add('selected');
  });
});

document.getElementById('btn-nueva-meta').addEventListener('click', abrirModalCrear);
const btnNuevaMetaEmpty = document.getElementById('btn-nueva-meta-empty');
if (btnNuevaMetaEmpty) btnNuevaMetaEmpty.addEventListener('click', abrirModalCrear);

document.getElementById('btn-cerrar-crear').addEventListener('click', cerrarModalCrear);
document.getElementById('btn-cancelar-crear').addEventListener('click', cerrarModalCrear);
modalCrear.addEventListener('click', e => { if (e.target === modalCrear) cerrarModalCrear(); });

document.getElementById('btn-guardar-crear').addEventListener('click', async () => {
  const data = new FormData(formCrear);
  const m = document.getElementById('crear-monto-meta');
  if (m && m.dataset.raw) data.set('monto_meta', m.dataset.raw);

  try {
    const res  = await fetch(URL_CREAR_META, {
      method: 'POST', body: data,
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const json = await res.json();
    if (json.ok) {
      cerrarModalCrear();
      mostrarToast(json.message || 'Meta creada exitosamente', 'success');
      setTimeout(() => location.reload(), 700);
    } else {
      mostrarErroresCrear(json.errors || {});
    }
  } catch {
    mostrarToast('Error de conexión al crear la meta.', 'error');
  }
});


/* ══════════════════════════════════════════════════════════
   8. MODAL EDITAR META
   ══════════════════════════════════════════════════════════ */

const modalEditar     = document.getElementById('modal-editar-meta');
const formEditar      = document.getElementById('form-editar-meta');
const editarErrors    = document.getElementById('editar-errors');
const editarErrorsTxt = document.getElementById('editar-errors-text');
let   _editarUrl      = '';

function cerrarModalEditar() {
  modalEditar.setAttribute('hidden', '');
}

function mostrarErroresEditar(errors) {
  const msgs = Object.values(errors).flat().join(' · ');
  editarErrorsTxt.textContent = msgs;
  editarErrors.style.display = 'flex';
  lucide.createIcons();
  editarErrors.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function ocultarErroresEditar() {
  editarErrors.style.display = 'none';
  editarErrorsTxt.textContent = '';
}

document.getElementById('editar-cat-btn').addEventListener('click', () => {
  abrirPicker((id, nombre) => {
    document.getElementById('editar-categoria').value = id;
    const lbl = document.getElementById('editar-cat-label');
    lbl.textContent = nombre;
    document.getElementById('editar-cat-btn').classList.add('selected');
  });
});

document.querySelectorAll('.btn-editar-meta').forEach(btn => {
  btn.addEventListener('click', async () => {
    const url = btn.dataset.url;
    _editarUrl = url;
    ocultarErroresEditar();

    try {
      const res  = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      const json = await res.json();
      if (!json.ok) { mostrarToast('Error al cargar los datos.', 'error'); return; }

      const a = json.ahorro;
      document.getElementById('editar-ahorro-id').value = a.id;
      const inputEditMonto = document.getElementById('editar-monto-meta');
      inputEditMonto.value = formatearNumeroStr(a.monto_meta);
      inputEditMonto.dataset.raw = a.monto_meta;

      document.getElementById('editar-frecuencia').value = a.frecuencia;
      const fLabelEdit = document.getElementById('editar-frecuencia-label');
      if (fLabelEdit) {
        const freqMap = { 'DIARIA':'Diaria', 'SEMANAL':'Semanal', 'QUINCENAL':'Quincenal', 'MENSUAL':'Mensual', 'TRIMESTRAL':'Trimestral', 'SEMESTRAL':'Semestral', 'ANUAL':'Anual' };
        fLabelEdit.textContent = freqMap[a.frecuencia] || 'Seleccionar Frecuencia';
        fLabelEdit.style.color = a.frecuencia ? 'var(--slate-900)' : 'var(--slate-500)';
      }

      document.getElementById('editar-descripcion').value = a.descripcion;
      document.getElementById('editar-categoria').value = a.categoria_id;

      const inputCuotas = document.getElementById('editar-cuotas');
      if (inputCuotas) {
        if (a.cuotas_minimas > 0) {
          inputCuotas.min = a.cuotas_minimas;
          inputCuotas.title = `Mínimo ${a.cuotas_minimas} (ya aportadas)`;
        } else {
          inputCuotas.min = 1;
          inputCuotas.title = '';
        }
      }

      const catLbl = document.getElementById('editar-cat-label');
      catLbl.textContent = a.categoria_nombre || 'Seleccionar categoría';
      const catBtn = document.getElementById('editar-cat-btn');
      catBtn.classList.toggle('selected', !!a.categoria_id);

      const subtitulo = document.getElementById('editar-subtitulo');
      if (subtitulo) subtitulo.textContent = a.categoria_nombre || '';

      modalEditar.removeAttribute('hidden');
      lucide.createIcons();

      // Siempre iniciar en modo cuotas con el valor existente.
      // No se precarga fecha_meta para evitar que el backend reciba ambos campos
      // al mismo tiempo y lance el error de validación del form.
      initPlazoToggle('editar', null, a.cantidad_cuotas || null);
      modalEditar.querySelector('.modal__body').scrollTop = 0;

    } catch {
      mostrarToast('Error de conexión al cargar la meta.', 'error');
    }
  });
});

document.getElementById('btn-cerrar-editar').addEventListener('click', cerrarModalEditar);
document.getElementById('btn-cancelar-editar').addEventListener('click', cerrarModalEditar);
modalEditar.addEventListener('click', e => { if (e.target === modalEditar) cerrarModalEditar(); });

document.getElementById('btn-guardar-editar').addEventListener('click', async () => {
  const data = new FormData(formEditar);
  const m = document.getElementById('editar-monto-meta');
  if (m && m.dataset.raw) data.set('monto_meta', m.dataset.raw);

  try {
    const res  = await fetch(_editarUrl, {
      method: 'POST', body: data,
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const json = await res.json();
    if (json.ok) {
      cerrarModalEditar();
      mostrarToast(json.message || 'Meta actualizada', 'success');
      setTimeout(() => location.reload(), 700);
    } else {
      mostrarErroresEditar(json.errors || {});
    }
  } catch {
    mostrarToast('Error de conexión al actualizar.', 'error');
  }
});


/* ══════════════════════════════════════════════════════════
   9. MODAL ELIMINAR META
   ══════════════════════════════════════════════════════════ */

const modalEliminar = document.getElementById('modal-eliminar-meta');
let   _eliminarUrl  = '';

function cerrarModalEliminar() {
  modalEliminar.setAttribute('hidden', '');
}

document.querySelectorAll('.btn-eliminar-meta').forEach(btn => {
  btn.addEventListener('click', async () => {
    const url = btn.dataset.url;
    _eliminarUrl = url;

    try {
      const res  = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      const json = await res.json();
      const nombreEl = document.getElementById('eliminar-nombre-meta');
      if (nombreEl) nombreEl.textContent = json.nombre || 'esta meta';
      modalEliminar.removeAttribute('hidden');
      lucide.createIcons();
    } catch {
      mostrarToast('Error al cargar los datos de la meta.', 'error');
    }
  });
});

document.getElementById('btn-cerrar-eliminar').addEventListener('click', cerrarModalEliminar);
document.getElementById('btn-cancelar-eliminar').addEventListener('click', cerrarModalEliminar);
modalEliminar.addEventListener('click', e => { if (e.target === modalEliminar) cerrarModalEliminar(); });

document.getElementById('btn-confirmar-eliminar').addEventListener('click', async () => {
  const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
  const csrf      = csrfInput ? csrfInput.value : CSRF_TOKEN;
  const data      = new FormData();
  data.append('csrfmiddlewaretoken', csrf);

  try {
    const res  = await fetch(_eliminarUrl, {
      method: 'POST', body: data,
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const json = await res.json();
    if (json.ok) {
      cerrarModalEliminar();
      mostrarToast(json.message || 'Meta eliminada', 'success');
      setTimeout(() => location.reload(), 700);
    } else {
      mostrarToast('Error al eliminar la meta.', 'error');
    }
  } catch {
    mostrarToast('Error de conexión.', 'error');
  }
});


/* ══════════════════════════════════════════════════════════
   10. MODAL DE REPORTE / EXPORTACIÓN
   ══════════════════════════════════════════════════════════ */

const modalReporte  = document.getElementById('modal-reporte');
let   formatoActivo = 'csv';

const LABEL_FORMATO = { csv: 'CSV', excel: 'Excel (.xlsx)', pdf: 'PDF' };
const URL_EXPORTAR  = {
  csv:   URL_EXPORTAR_CSV,
  excel: URL_EXPORTAR_EXCEL,
  pdf:   URL_EXPORTAR_PDF,
};

function abrirReporte(formato) {
  formatoActivo = formato;
  document.getElementById('modal-reporte-formato-label').textContent =
    'Formato: ' + LABEL_FORMATO[formato];
  document.getElementById('reporte-label-formato').textContent =
    LABEL_FORMATO[formato];
  modalReporte.removeAttribute('hidden');
  lucide.createIcons();
}

function cerrarReporte() {
  modalReporte.setAttribute('hidden', '');
}

document.getElementById('btn-export-pdf').addEventListener('click',   () => abrirReporte('pdf'));
document.getElementById('btn-export-excel').addEventListener('click', () => abrirReporte('excel'));
document.getElementById('btn-export-csv').addEventListener('click',   () => abrirReporte('csv'));

document.getElementById('btn-cerrar-reporte').addEventListener('click',   cerrarReporte);
document.getElementById('btn-cancelar-reporte').addEventListener('click', cerrarReporte);
modalReporte.addEventListener('click', e => { if (e.target === modalReporte) cerrarReporte(); });

document.getElementById('btn-descargar-reporte').addEventListener('click', () => {
  const estado = document.getElementById('reporte-estado-filtro').value;
  const params = new URLSearchParams();
  if (estado) params.set('estado', estado);
  window.location.href =
    URL_EXPORTAR[formatoActivo] + (params.toString() ? '?' + params.toString() : '');
  cerrarReporte();
});


/* ══════════════════════════════════════════════════════════
   11. ESCAPE cierra modales
   ══════════════════════════════════════════════════════════ */

document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  if (!modalReporte.hasAttribute('hidden'))    { cerrarReporte();        return; }
  if (!modalEliminar.hasAttribute('hidden'))   { cerrarModalEliminar();  return; }
  if (!modalPicker.hasAttribute('hidden'))     { cerrarPicker();         return; }
  if (!modalEditar.hasAttribute('hidden'))     { cerrarModalEditar();    return; }
  if (!modalCrear.hasAttribute('hidden'))      { cerrarModalCrear();     return; }
  if (!overlayAporte.hasAttribute('hidden'))   { cerrarModalAporte();    return; }
});


/* ══════════════════════════════════════════════════════════
   12. DATEPICKER, FRECUENCIA Y FILTRO DE ESTADO
   ══════════════════════════════════════════════════════════ */

/* ══════════════════════════════════════════════════════════
   13. FORMATEO DE MONTOS
   ══════════════════════════════════════════════════════════ */
function bindMontoFormatter(el) {
  if (!el) return;
  el.addEventListener('input', function () {
    const oldLen = this.value.length;
    const start = this.selectionStart;
    let digitCount = 0;
    for (let i = 0; i < start; i++) {
      if (/\d/.test(this.value[i])) digitCount++;
    }
    const digitos = this.value.replace(/\D/g, '');
    if (!digitos) { this.dataset.raw = ''; this.value = ''; return; }
    const formatted = digitos.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    this.dataset.raw = digitos;
    this.value = formatted;
    let newPos = formatted.length;
    if (start < oldLen) {
      let dc = 0;
      for (let i = 0; i < formatted.length; i++) {
        if (dc >= digitCount) { newPos = i; break; }
        if (/\d/.test(formatted[i])) dc++;
        newPos = i + 1;
      }
    }
    this.setSelectionRange(newPos, newPos);
  });
}

function formatearNumeroStr(raw) {
  if (!raw) return '';
  const entero = String(raw).split('.')[0].replace(/\D/g, '');
  if (!entero) return '';
  return entero.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

let dpCrear  = null;
let dpEditar = null;

document.addEventListener('DOMContentLoaded', () => {
  if (typeof MiniDatepicker !== 'undefined') {
    const inputCrear = document.getElementById('crear-fecha-meta');
    if (inputCrear) {
      dpCrear = new MiniDatepicker(inputCrear, { acento: 'ahorro' });
      inputCrear.parentNode.appendChild(dpCrear.wrapper);
    }
    const inputEditar = document.getElementById('editar-fecha-meta');
    if (inputEditar) {
      dpEditar = new MiniDatepicker(inputEditar, { acento: 'ahorro' });
      inputEditar.parentNode.appendChild(dpEditar.wrapper);
    }
  }

  // Inicializar el toggle de crear en modo cuotas por defecto
  initPlazoToggle('crear', null, null);

  bindMontoFormatter(document.getElementById('crear-monto-meta'));
  bindMontoFormatter(document.getElementById('editar-monto-meta'));

  // Filtro de estado
  const btnFiltroEstado  = document.getElementById('btn-filtro-estado');
  const menuFiltroEstado = document.getElementById('menu-filtro-estado');
  if (btnFiltroEstado && menuFiltroEstado) {
    btnFiltroEstado.addEventListener('click', (e) => {
      e.stopPropagation();
      menuFiltroEstado.toggleAttribute('hidden');
    });
    document.addEventListener('click', (e) => {
      if (!menuFiltroEstado.contains(e.target) && e.target !== btnFiltroEstado) {
        menuFiltroEstado.setAttribute('hidden', '');
      }
    });

    const params       = new URLSearchParams(window.location.search);
    const estadoActual = params.get('estado');
    if (estadoActual) {
      const estadoLabels = { 'SIN_INICIAR': 'Sin Iniciar', 'ACTIVO': 'Activo', 'COMPLETADO': 'Completado', 'ABANDONADO': 'Abandonado' };
      if (estadoLabels[estadoActual]) {
        btnFiltroEstado.innerHTML = `<i data-lucide="filter"></i> Estado: ${estadoLabels[estadoActual]} <i data-lucide="chevron-down" style="width:14px;height:14px;"></i>`;
        lucide.createIcons();
      }
    }
  }

  // Picker de frecuencia
  document.querySelectorAll('.picker-frecuencia-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const target = btn.id === 'crear-frecuencia-btn' ? 'crear' : 'editar';
      const menu = document.getElementById(`${target}-frecuencia-menu`);
      if (menu) menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    });
  });

  document.querySelectorAll('.frecuencia-option').forEach(opt => {
    opt.addEventListener('click', (e) => {
      e.stopPropagation();
      const target = opt.dataset.target;
      const val    = opt.dataset.value;
      const text   = opt.textContent;

      document.getElementById(`${target}-frecuencia`).value = val;
      const label = document.getElementById(`${target}-frecuencia-label`);
      if (label) {
        label.textContent = text;
        label.style.color = 'var(--slate-900)';
      }
      const menu = document.getElementById(`${target}-frecuencia-menu`);
      if (menu) menu.style.display = 'none';
    });
  });

  document.addEventListener('click', (e) => {
    document.querySelectorAll('.frecuencia-menu').forEach(menu => {
      const target = menu.id.replace('-frecuencia-menu', '');
      const btn    = document.getElementById(`${target}-frecuencia-btn`);
      if (btn && !menu.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
        menu.style.display = 'none';
      }
    });
  });
});
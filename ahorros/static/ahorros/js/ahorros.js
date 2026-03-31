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

async function enviarAporte(e, url) {
  e.preventDefault();
  const form = e.currentTarget;
  const data = new FormData(form);

  try {
    const res  = await fetch(form.action, { method: 'POST', body: data });
    const json = await res.json();

    if (json.ok) {
      cerrarModalAporte();
      mostrarToast(json.message || 'Aporte registrado', 'success');
      setTimeout(() => location.reload(), 700);
    } else {
      // Mostrar alerta de error dentro del modal
      const errContainer = overlayAporte.querySelector('#modal-error-container');
      const errMsg       = overlayAporte.querySelector('#modal-error-message');
      if (errContainer && errMsg) {
        errMsg.textContent = json.error || 'Error al registrar el aporte.';
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
let   _pickerCallback      = null; // función a llamar al seleccionar

function abrirPicker(callback) {
  _pickerCallback = callback;
  if (pickerBuscador) pickerBuscador.value = '';
  filtrarPicker('');
  modalPicker.removeAttribute('hidden');
  pickerGrid.querySelectorAll('.picker-cat-card').forEach(c => c.classList.remove('selected'));
  if (pickerSelLabel) pickerSelLabel.textContent = '';
  lucide.createIcons();
}

function cerrarPicker() {
  modalPicker.setAttribute('hidden', '');
}

function filtrarPicker(q) {
  pickerGrid.querySelectorAll('.picker-cat-card').forEach(card => {
    const nombre = (card.dataset.nombre || '').toLowerCase();
    card.style.display = nombre.includes(q.toLowerCase()) ? '' : 'none';
  });
}

pickerGrid.addEventListener('click', e => {
  const card = e.target.closest('.picker-cat-card');
  if (!card) return;
  const id     = card.dataset.id;
  const nombre = card.dataset.nombre;
  pickerGrid.querySelectorAll('.picker-cat-card').forEach(c => c.classList.remove('selected'));
  card.classList.add('selected');
  if (pickerSelLabel) pickerSelLabel.textContent = `Seleccionado: ${nombre}`;
  if (_pickerCallback) _pickerCallback(id, nombre);
  cerrarPicker();
});

if (pickerBuscador) {
  pickerBuscador.addEventListener('input', () => filtrarPicker(pickerBuscador.value));
}

document.getElementById('btn-cerrar-picker').addEventListener('click', cerrarPicker);
document.getElementById('btn-cancelar-picker').addEventListener('click', cerrarPicker);
modalPicker.addEventListener('click', e => { if (e.target === modalPicker) cerrarPicker(); });


/* ══════════════════════════════════════════════════════════
   6. MODAL CREAR META
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
  ocultarErroresCrear();
  modalCrear.removeAttribute('hidden');
  lucide.createIcons();
}

function cerrarModalCrear() {
  modalCrear.setAttribute('hidden', '');
}

function mostrarErroresCrear(errors) {
  const msgs = Object.values(errors).flat().join(' · ');
  crearErrorsTxt.textContent = msgs;
  crearErrors.style.display = 'flex';
}

function ocultarErroresCrear() {
  crearErrors.style.display = 'none';
  crearErrorsTxt.textContent = '';
}

// Picker de categoría para crear
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
   7. MODAL EDITAR META
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
}

function ocultarErroresEditar() {
  editarErrors.style.display = 'none';
  editarErrorsTxt.textContent = '';
}

// Picker de categoría para editar
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
      document.getElementById('editar-monto-meta').value = a.monto_meta;
      document.getElementById('editar-frecuencia').value = a.frecuencia;
      document.getElementById('editar-fecha-meta').value = a.fecha_meta;
      document.getElementById('editar-cuotas').value = a.cantidad_cuotas;
      document.getElementById('editar-descripcion').value = a.descripcion;
      document.getElementById('editar-categoria').value = a.categoria_id;

      const catLbl = document.getElementById('editar-cat-label');
      catLbl.textContent = a.categoria_nombre || 'Seleccionar categoría';
      const catBtn = document.getElementById('editar-cat-btn');
      catBtn.classList.toggle('selected', !!a.categoria_id);

      const subtitulo = document.getElementById('editar-subtitulo');
      if (subtitulo) subtitulo.textContent = a.categoria_nombre || '';

      modalEditar.removeAttribute('hidden');
      lucide.createIcons();
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
   8. MODAL ELIMINAR META
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
   9. MODAL DE REPORTE / EXPORTACIÓN
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
   10. ESCAPE cierra modales
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
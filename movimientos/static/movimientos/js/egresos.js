'use strict';

let movimientoEditandoId = null;
let categoriaActualId    = null;
let paginaActual         = 1;

const modalMovimiento    = document.getElementById('modal-movimiento');
const modalRegistros     = document.getElementById('modal-registros');
const formMovimiento     = document.getElementById('form-movimiento');
const tablaRegistrosBody = document.getElementById('tabla-registros-body');

/* Toast */
function mostrarToast(msg, tipo = 'ok') {
  const t = document.createElement('div');
  t.className = `toast toast--${tipo}`;
  t.textContent = msg;
  document.getElementById('toast-container').appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

/* Errores */
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

/* Modal CRUD */
function abrirModalNuevo() {
  movimientoEditandoId = null;
  document.getElementById('modal-titulo').textContent = 'Nuevo egreso';
  formMovimiento.reset();
  limpiarErrores();
  document.getElementById('campo-fecha').value = new Date().toISOString().split('T')[0];
  modalMovimiento.removeAttribute('hidden');
}
function abrirModalEditar(id, descripcion, monto, fechaRaw, categoriaId) {
  movimientoEditandoId = id;
  document.getElementById('modal-titulo').textContent = 'Editar egreso';
  document.getElementById('campo-descripcion').value = descripcion;
  document.getElementById('campo-monto').value = monto;
  document.getElementById('campo-fecha').value = fechaRaw;
  document.getElementById('campo-categoria').value = categoriaId;
  limpiarErrores();
  modalMovimiento.removeAttribute('hidden');
}
function cerrarModalMovimiento() {
  modalMovimiento.setAttribute('hidden', '');
  formMovimiento.reset();
  limpiarErrores();
}

/* Submit form */
formMovimiento.addEventListener('submit', async (e) => {
  e.preventDefault();
  limpiarErrores();
  const url = movimientoEditandoId ? `${URL_EDITAR}${movimientoEditandoId}/` : URL_GUARDAR;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': CSRF_TOKEN },
    body: new FormData(formMovimiento),
  });
  const data = await res.json();
  if (data.ok) {
    cerrarModalMovimiento();
    mostrarToast(movimientoEditandoId ? 'Egreso actualizado.' : 'Egreso registrado.', 'ok');
    if (categoriaActualId) cargarRegistros(categoriaActualId, paginaActual);
  } else {
    mostrarErrores(data.errors || {});
    mostrarToast('Revisa los campos del formulario.', 'error');
  }
});

/* Eliminar */
async function eliminarMovimiento(id) {
  if (!confirm('¿Eliminar este egreso?')) return;
  const res = await fetch(`${URL_ELIMINAR}${id}/`, {
    method: 'POST',
    headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': CSRF_TOKEN },
  });
  const data = await res.json();
  if (data.ok) {
    tablaRegistrosBody.querySelector(`tr[data-id="${id}"]`)?.remove();
    mostrarToast('Egreso eliminado.', 'ok');
  } else {
    mostrarToast('No se pudo eliminar.', 'error');
  }
}

/* Modal registros */
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

async function cargarRegistros(categoriaId, pagina) {
  const res = await fetch(`${URL_REGISTROS}?categoria=${categoriaId}&page=${pagina}`, {
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
  });
  const data = await res.json();

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
      abrirModalEditar(btn.dataset.id, btn.dataset.descripcion, btn.dataset.monto, btn.dataset.fecha, btn.dataset.categoria);
    });
  });
  tablaRegistrosBody.querySelectorAll('.btn-eliminar').forEach(btn => {
    btn.addEventListener('click', (e) => { e.stopPropagation(); eliminarMovimiento(btn.dataset.id); });
  });
}

document.getElementById('btn-pag-anterior').addEventListener('click', () => {
  if (paginaActual > 1) cargarRegistros(categoriaActualId, --paginaActual);
});
document.getElementById('btn-pag-siguiente').addEventListener('click', () => {
  cargarRegistros(categoriaActualId, ++paginaActual);
});

/* Buscador */
document.getElementById('buscador').addEventListener('input', (e) => {
  const q = e.target.value.toLowerCase().trim();
  document.querySelectorAll('.categoria-card').forEach(card => {
    card.style.display = card.dataset.searchText.includes(q) ? '' : 'none';
  });
});

/* Eventos cierre */
document.getElementById('btn-nuevo').addEventListener('click', abrirModalNuevo);
document.getElementById('btn-cerrar-modal').addEventListener('click', cerrarModalMovimiento);
document.getElementById('btn-cancelar-modal').addEventListener('click', cerrarModalMovimiento);
document.getElementById('btn-cerrar-registros').addEventListener('click', () => modalRegistros.setAttribute('hidden', ''));
modalMovimiento.addEventListener('click', (e) => { if (e.target === modalMovimiento) cerrarModalMovimiento(); });
modalRegistros.addEventListener('click', (e) => { if (e.target === modalRegistros) modalRegistros.setAttribute('hidden', ''); });
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') { cerrarModalMovimiento(); modalRegistros.setAttribute('hidden', ''); }
});

/* Barras de progreso */
document.querySelectorAll('.progress-bar__fill').forEach(el => {
  el.style.width = (parseFloat(el.dataset.porcentaje) || 0) + '%';
});
lucide.createIcons();
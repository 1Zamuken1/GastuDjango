document.addEventListener('DOMContentLoaded', () => {

  /* ── Helpers ─────────────────────────────────────────────── */
  function getCsrf() {
    return document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] || '';
  }

  async function postForm(url, fd) {
    return fetch(url, {
      method:  'POST',
      headers: { 'X-CSRFToken': getCsrf() },
      body:    fd,
    }).then(r => r.json());
  }

  function showToast(msg, type = 'success') {
    if (type === 'success') window.GastuAlerts.toastSuccess(msg);
    else window.GastuAlerts.toastError(msg);
  }

  function openModal(id)  { document.getElementById(id)?.classList.add('open'); }
  function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }

  /* ── Cerrar modales ──────────────────────────────────────── */
  document.querySelectorAll('.js-close-modal').forEach(btn => {
    btn.addEventListener('click', () => closeModal(btn.dataset.modal));
  });
  document.querySelectorAll('.modal-overlay').forEach(m => {
    m.addEventListener('click', e => { if (e.target === m) m.classList.remove('open'); });
  });

  /* ── Abrir modal crear ───────────────────────────────────── */
  document.getElementById('btn-nueva-categoria')?.addEventListener('click', () => {
    document.getElementById('form-crear-categoria')?.reset();
    const msg = document.getElementById('msg-crear-cat');
    if (msg) msg.textContent = '';
    openModal('modal-crear-categoria');
  });

  /* ── Crear categoría ─────────────────────────────────────── */
  document.getElementById('form-crear-categoria')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const fd  = new FormData(this);
    // CREAR_CATEGORIA_URL se inyecta desde el template como variable global
    const res = await postForm(window.CREAR_CATEGORIA_URL, fd);
    const msg = document.getElementById('msg-crear-cat');
    if (res.ok) {
      showToast(res.msg);
      closeModal('modal-crear-categoria');
      setTimeout(() => location.reload(), 800);
    } else {
      if (msg) { msg.style.color = '#ef4444'; msg.textContent = res.msg; }
    }
  });

  /* ── Abrir modal editar ──────────────────────────────────── */
  document.querySelectorAll('.js-btn-editar-categoria').forEach(btn => {
    btn.addEventListener('click', async function() {
      const id  = this.dataset.id;
      const res = await fetch(`/admin-panel/categorias/${id}/detalle/`).then(r => r.json());
      document.getElementById('editar-cat-id').value      = res.id;
      document.getElementById('editar-cat-nombre').value  = res.nombre;
      document.getElementById('editar-cat-tipo').value    = res.tipo;
      document.getElementById('editar-cat-desc').value    = res.descripcion;
      const msg = document.getElementById('msg-editar-cat');
      if (msg) msg.textContent = '';
      openModal('modal-editar-categoria');
    });
  });

  /* ── Guardar edición ─────────────────────────────────────── */
  document.getElementById('form-editar-categoria')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const id  = document.getElementById('editar-cat-id').value;
    const fd  = new FormData(this);
    const res = await postForm(`/admin-panel/categorias/${id}/editar/`, fd);
    const msg = document.getElementById('msg-editar-cat');
    if (res.ok) {
      showToast(res.msg);
      closeModal('modal-editar-categoria');
      setTimeout(() => location.reload(), 800);
    } else {
      if (msg) { msg.style.color = '#ef4444'; msg.textContent = res.msg; }
    }
  });

  /* ── Toggle estado ───────────────────────────────────────── */
  document.querySelectorAll('.js-toggle-categoria').forEach(btn => {
    btn.addEventListener('change', async function() {
      const id  = this.dataset.id;
      const fd  = new FormData();
      const res = await postForm(`/admin-panel/categorias/${id}/toggle/`, fd);
      if (res.ok) {
        showToast(res.msg);
      } else {
        showToast(res.msg, 'error');
        this.checked = !this.checked;
      }
    });
  });

  /* ── Búsqueda + filtro en tiempo real ────────────────────── */
  function filtrarCategorias() {
    const term   = document.getElementById('search-cat')?.value.toLowerCase() || '';
    const tipo   = document.getElementById('filter-tipo')?.value   || '';
    const estado = document.getElementById('filter-estado')?.value || '';
    document.querySelectorAll('#tabla-categorias tbody tr').forEach(row => {
      const nombre   = row.dataset.nombre  || '';
      const rowTipo  = row.dataset.tipo    || '';
      const rowActivo = row.dataset.activo || '';
      const matchQ = nombre.includes(term);
      const matchT = !tipo   || rowTipo  === tipo;
      const matchE = !estado || rowActivo === estado;
      row.style.display = (matchQ && matchT && matchE) ? '' : 'none';
    });
  }

  document.getElementById('search-cat')?.addEventListener('input',  filtrarCategorias);
  document.getElementById('filter-tipo')?.addEventListener('change', filtrarCategorias);
  document.getElementById('filter-estado')?.addEventListener('change', filtrarCategorias);

});
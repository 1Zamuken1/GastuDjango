/* =============================================================
   usuarios.js  —  GastuApp
   Ruta: panel_admin/static/panel_admin/js/usuarios.js
   Lógica de modales, CRUD y filtros de la vista de usuarios
   ============================================================= */

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
    const t = document.createElement('div');
    t.className = `message message--${type}`;
    t.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;min-width:260px;box-shadow:0 8px 24px rgba(0,0,0,0.12);';
    t.innerHTML = `<i data-lucide="${type === 'success' ? 'check-circle' : 'alert-circle'}"></i><span style="flex:1">${msg}</span>`;
    document.body.appendChild(t);
    lucide.createIcons();
    setTimeout(() => t.remove(), 3000);
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
  document.getElementById('btn-nuevo-usuario')?.addEventListener('click', () => {
    document.getElementById('form-crear-usuario')?.reset();
    document.querySelectorAll('#form-crear-usuario .form-error').forEach(e => e.textContent = '');
    const msg = document.getElementById('msg-crear');
    if (msg) msg.textContent = '';
    openModal('modal-crear-usuario');
  });

  /* ── Crear usuario ───────────────────────────────────────── */
  document.getElementById('form-crear-usuario')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const fd  = new FormData(this);
    // CREAR_USUARIO_URL se inyecta desde el template como variable global
    const res = await postForm(window.CREAR_USUARIO_URL, fd);
    if (res.ok) {
      showToast(res.msg);
      closeModal('modal-crear-usuario');
      setTimeout(() => location.reload(), 800);
    } else {
      if (res.errores) {
        Object.entries(res.errores).forEach(([k, v]) => {
          const el = document.getElementById(`err-crear-${k}`);
          if (el) el.textContent = v;
        });
      }
      const msg = document.getElementById('msg-crear');
      if (msg) { msg.style.color = '#ef4444'; msg.textContent = res.msg || 'Corrige los errores.'; }
    }
  });

  /* ── Abrir modal editar ──────────────────────────────────── */
  document.querySelectorAll('.js-btn-editar-usuario').forEach(btn => {
    btn.addEventListener('click', async function() {
      const id  = this.dataset.id;
      const res = await fetch(`/admin-panel/usuarios/${id}/detalle/`).then(r => r.json());
      document.getElementById('editar-usuario-id').value = res.id;
      document.getElementById('editar-username').value   = res.username;
      document.getElementById('editar-email').value      = res.email;
      document.getElementById('editar-telefono').value   = res.telefono;
      const passField = document.getElementById('editar-password');
      if (passField) passField.value = '';
      const msg = document.getElementById('msg-editar');
      if (msg) msg.textContent = '';
      openModal('modal-editar-usuario');
    });
  });

  /* ── Toggle contraseña en modal editar ───────────────────── */
  document.addEventListener('click', function(e) {
    const btn = e.target.closest('#toggleEditPass');
    if (!btn) return;
    const input = document.getElementById('editar-password');
    if (!input) return;
    const isPass = input.type === 'password';
    input.type = isPass ? 'text' : 'password';
    btn.innerHTML = isPass
      ? '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>'
      : '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  });

  /* ── Guardar edición ─────────────────────────────────────── */
  document.getElementById('form-editar-usuario')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const id  = document.getElementById('editar-usuario-id').value;
    const fd  = new FormData(this);
    const res = await postForm(`/admin-panel/usuarios/${id}/editar/`, fd);
    const msg = document.getElementById('msg-editar');
    if (res.ok) {
      showToast(res.msg);
      closeModal('modal-editar-usuario');
      setTimeout(() => location.reload(), 800);
    } else {
      if (msg) { msg.style.color = '#ef4444'; msg.textContent = res.msg; }
    }
  });

  /* ── Toggle estado ───────────────────────────────────────── */
  document.querySelectorAll('.js-toggle-usuario').forEach(btn => {
    btn.addEventListener('change', async function() {
      const id  = this.dataset.id;
      const fd  = new FormData();
      const res = await postForm(`/admin-panel/usuarios/${id}/toggle/`, fd);
      if (res.ok) {
        showToast(res.msg);
      } else {
        showToast(res.msg, 'error');
        this.checked = !this.checked;
      }
    });
  });

  /* ── Cambiar rol ─────────────────────────────────────────── */
  document.querySelectorAll('.js-cambiar-rol').forEach(btn => {
    btn.addEventListener('click', async function() {
      if (!confirm('¿Cambiar el rol de este usuario?')) return;
      const id  = this.dataset.id;
      const fd  = new FormData();
      const res = await postForm(`/admin-panel/usuarios/${id}/rol/`, fd);
      if (res.ok) {
        showToast(res.msg);
        const badge = document.getElementById(`badge-rol-${id}`);
        if (badge) {
          badge.textContent = res.rol === 'ADMIN' ? 'Admin' : 'Usuario';
          badge.className   = `badge ${res.rol === 'ADMIN' ? 'badge--indigo' : 'badge--slate'}`;
        }
      } else {
        showToast(res.msg, 'error');
      }
    });
  });

  /* ── Búsqueda en tiempo real ─────────────────────────────── */
  document.getElementById('search-input')?.addEventListener('input', function() {
    const term = this.value.toLowerCase();
    document.querySelectorAll('#tabla-usuarios tbody tr').forEach(row => {
      const username = row.dataset.username || '';
      const email    = row.dataset.email    || '';
      row.style.display = (username.includes(term) || email.includes(term)) ? '' : 'none';
    });
  });

  /* ── Eliminar usuario ────────────────────────────────────── */
  document.getElementById('tabla-usuarios')?.addEventListener('click', async function(e) {
    const btn = e.target.closest('.js-eliminar-usuario');
    if (!btn) return;
    const id       = btn.dataset.id;
    const username = btn.dataset.username;
    if (!confirm(`¿Eliminar al usuario "${username}"? Esta acción no se puede deshacer.`)) return;
    const fd  = new FormData();
    const res = await postForm(`/admin-panel/usuarios/${id}/eliminar/`, fd);
    if (res.ok) {
      showToast(res.msg);
      btn.closest('tr')?.remove();
    } else {
      showToast(res.msg, 'error');
    }
  });

});
document.addEventListener('DOMContentLoaded', () => {

  lucide.createIcons();

  /* ── Toggle sidebar ─────────────────────────────────────── */
  const toggle  = document.getElementById('sidebar-toggle');
  const body    = document.body;
  const isMobile = () => window.innerWidth < 768;

  if (toggle) {
    toggle.addEventListener('click', () => {
      if (isMobile()) {
        body.classList.toggle('sidebar-open');
      } else {
        body.classList.toggle('sidebar-mini');
        localStorage.setItem('admin-sidebar-mini', body.classList.contains('sidebar-mini'));
      }
    });
  }

  // Restaurar estado guardado
  if (!isMobile() && localStorage.getItem('admin-sidebar-mini') === 'true') {
    body.classList.add('sidebar-mini');
  }

  /* ── Helper: CSRF token ──────────────────────────────────── */
  function getCsrf() {
    return document.cookie.split(';')
      .find(c => c.trim().startsWith('csrftoken='))
      ?.split('=')[1] || '';
  }

  function postJSON(url, data) {
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrf(),
      },
      body: JSON.stringify(data),
    }).then(r => r.json());
  }

  function postForm(url) {
    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', getCsrf());
    return fetch(url, { method: 'POST', body: fd }).then(r => r.json());
  }

  /* ── Toast ───────────────────────────────────────────────── */
  function showToast(msg, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `message message--${type}`;
    toast.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;min-width:260px;box-shadow:0 8px 24px rgba(0,0,0,0.12);';
    toast.innerHTML = `
      <i data-lucide="${type === 'success' ? 'check-circle' : 'alert-circle'}"></i>
      <span style="flex:1">${msg}</span>
    `;
    document.body.appendChild(toast);
    lucide.createIcons();
    setTimeout(() => toast.remove(), 3000);
  }

  /* ── Toggle usuario (activar/desactivar) ─────────────────── */
  document.querySelectorAll('.js-toggle-usuario').forEach(btn => {
    btn.addEventListener('change', async function () {
      const id  = this.dataset.id;
      const res = await postForm(`/admin-panel/usuarios/${id}/toggle/`);
      if (res.ok) {
        showToast(res.msg);
        const badge = document.getElementById(`badge-activo-${id}`);
        if (badge) {
          badge.textContent = res.activo ? 'Activo' : 'Inactivo';
          badge.className   = `badge ${res.activo ? 'badge--green' : 'badge--red'}`;
        }
      } else {
        showToast(res.msg || 'Error al cambiar estado.', 'error');
        this.checked = !this.checked; // revertir
      }
    });
  });

  /* ── Cambiar rol ─────────────────────────────────────────── */
  document.querySelectorAll('.js-cambiar-rol').forEach(btn => {
    btn.addEventListener('click', async function () {
      const id = this.dataset.id;
      if (!confirm('¿Cambiar el rol de este usuario?')) return;
      const res = await postForm(`/admin-panel/usuarios/${id}/rol/`);
      if (res.ok) {
        showToast(res.msg);
        const badge = document.getElementById(`badge-rol-${id}`);
        if (badge) {
          badge.textContent = res.rol === 'ADMIN' ? 'Admin' : 'Usuario';
          badge.className   = `badge ${res.rol === 'ADMIN' ? 'badge--indigo' : 'badge--slate'}`;
        }
        this.title = res.rol === 'ADMIN' ? 'Quitar admin' : 'Hacer admin';
      } else {
        showToast(res.msg || 'Error al cambiar rol.', 'error');
      }
    });
  });

  /* ── Toggle categoría ────────────────────────────────────── */
  document.querySelectorAll('.js-toggle-categoria').forEach(btn => {
    btn.addEventListener('change', async function () {
      const id  = this.dataset.id;
      const res = await postForm(`/admin-panel/categorias/${id}/toggle/`);
      if (res.ok) {
        showToast(res.msg);
        const badge = document.getElementById(`badge-cat-${id}`);
        if (badge) {
          badge.textContent = res.activo ? 'Activa' : 'Inactiva';
          badge.className   = `badge ${res.activo ? 'badge--green' : 'badge--red'}`;
        }
      } else {
        showToast(res.msg || 'Error.', 'error');
        this.checked = !this.checked;
      }
    });
  });

});
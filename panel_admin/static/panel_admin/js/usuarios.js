/* =============================================================
   usuarios.js  —  GastuApp
   Ruta: panel_admin/static/panel_admin/js/usuarios.js
   Lógica de modales, CRUD y filtros de la vista de usuarios
   ============================================================= */

document.addEventListener('DOMContentLoaded', () => {

  /* ── Helpers ─────────────────────────────────────────────── */
  function getCsrf() {
    // 1. Try cookie first
    const fromCookie = document.cookie
      .split(';')
      .map(c => c.trim())
      .find(c => c.startsWith('csrftoken='));
    if (fromCookie) return fromCookie.split('=')[1];
    // 2. Fallback to hidden input in any form on the page
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
  }

  async function postForm(url, fd) {
    // Evitar bodies multipart vacíos que pueden causar HTTP 400 en Daphne/Channels
    let isEmpty = true;
    for (let key of fd.keys()) { isEmpty = false; break; }
    if (isEmpty) fd.append('_dummy_field', '1');

    const resp = await fetch(url, {
      method:  'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': getCsrf(), 'X-Requested-With': 'XMLHttpRequest' },
      body:    fd,
    });
    if (!resp.ok) {
      const text = await resp.text();
      return { ok: false, msg: `Error ${resp.status}: ${resp.statusText}` };
    }
    return resp.json();
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
      const id       = this.dataset.id;
      const username = this.closest('tr')?.dataset.username || 'este usuario';
      const esAdmin  = this.querySelector('[data-lucide="shield-off"]') !== null;
      const accion   = esAdmin ? 'quitar permisos de administrador a' : 'hacer administrador a';

      const confirmado = await window.GastuAlerts.confirmar(
        'Cambiar rol de usuario',
        `¿Deseas ${accion} "${username}"?`,
        'Sí, cambiar rol'
      );
      if (!confirmado) return;

      const fd  = new FormData();
      const res = await postForm(`/admin-panel/usuarios/${id}/rol/`, fd);
      if (res.ok) {
        showToast(res.msg);
        const badge = document.getElementById(`badge-rol-${id}`);
        if (badge) {
          badge.textContent = res.rol === 'ADMIN' ? 'Admin' : 'Usuario';
          badge.className   = `badge ${res.rol === 'ADMIN' ? 'badge--indigo' : 'badge--slate'}`;
        }
        /* Actualizar icono del botón sin recargar la página */
        const nuevoIcono = res.rol === 'ADMIN' ? 'shield-off' : 'shield-check';
        const nuevoTitle = res.rol === 'ADMIN' ? 'Quitar admin' : 'Hacer admin';
        btn.title = nuevoTitle;
        btn.innerHTML = `<i data-lucide="${nuevoIcono}"></i>`;
        lucide.createIcons({ nodes: [btn] });
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

    const confirmado = await window.GastuAlerts.confirmar(
      'Eliminar usuario',
      `¿Estás seguro de que quieres eliminar a "${username}" y todos sus datos? Esta acción no se puede deshacer.`,
      'Sí, eliminar'
    );
    if (!confirmado) return;

    btn.disabled = true;
    try {
      const fd  = new FormData();
      const res = await postForm(`/admin-panel/usuarios/${id}/eliminar/`, fd);
      if (res.ok) {
        showToast(res.msg);
        btn.closest('tr')?.remove();
      } else {
        showToast(res.msg || 'No se pudo eliminar el usuario.', 'error');
        btn.disabled = false;
      }
    } catch(err) {
      console.error('Error al eliminar usuario:', err);
      showToast('Error de conexión al intentar eliminar.', 'error');
      btn.disabled = false;
    }
  });

  /* ── Toggle Contraseñas Crear Usuario ────────────────────── */
  document.getElementById('toggleCrearPass1')?.addEventListener('click', function() {
    const input = document.getElementById('crear-password1');
    if (!input) return;
    const isPass = input.type === 'password';
    input.type = isPass ? 'text' : 'password';
    this.innerHTML = isPass ? '<i data-lucide="eye-off" class="w-[15px] h-[15px]"></i>' : '<i data-lucide="eye" class="w-[15px] h-[15px]"></i>';
    lucide.createIcons({ nodes: [this] });
  });

  document.getElementById('toggleCrearPass2')?.addEventListener('click', function() {
    const input = document.getElementById('crear-password2');
    if (!input) return;
    const isPass = input.type === 'password';
    input.type = isPass ? 'text' : 'password';
    this.innerHTML = isPass ? '<i data-lucide="eye-off" class="w-[15px] h-[15px]"></i>' : '<i data-lucide="eye" class="w-[15px] h-[15px]"></i>';
    lucide.createIcons({ nodes: [this] });
  });

  /* ── Password Strength and Match (Admin Crear) ───────────── */
  const passInput = document.getElementById('crear-password1');
  const pass2Input = document.getElementById('crear-password2');
  const strengthBar = document.getElementById('strength-bar-crear');
  const strengthLbl = document.getElementById('strength-label-crear');
  const matchDiv = document.getElementById('match-indicator-crear');
  const matchIcon = document.getElementById('match-icon-crear');
  const matchText = document.getElementById('match-text-crear');

  const LEVELS = [
    { color: '#ef4444', label: 'Muy débil',  pct: '20%' },
    { color: '#f97316', label: 'Débil',      pct: '40%' },
    { color: '#eab308', label: 'Regular',    pct: '60%' },
    { color: '#10b981', label: 'Fuerte',     pct: '80%' },
    { color: '#059669', label: 'Muy fuerte', pct: '100%' },
  ];

  function toggleCriterionTailwind(id, met) {
    const el = document.getElementById(id);
    if (!el) return;
    const dot = el.querySelector('.criterion-dot');
    if (met) {
      el.classList.add('text-emerald-500');
      el.classList.remove('text-slate-400');
      if (dot) {
        dot.classList.add('bg-emerald-500');
        dot.classList.remove('bg-slate-300');
      }
    } else {
      el.classList.add('text-slate-400');
      el.classList.remove('text-emerald-500');
      if (dot) {
        dot.classList.add('bg-slate-300');
        dot.classList.remove('bg-emerald-500');
      }
    }
  }

  function evalPasswordTailwind(pw) {
    const c = {
      length:  pw.length >= 8,
      upper:   /[A-Z]/.test(pw),
      number:  /\d/.test(pw),
      special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pw),
    };
    toggleCriterionTailwind('c-length-crear',  c.length);
    toggleCriterionTailwind('c-upper-crear',   c.upper);
    toggleCriterionTailwind('c-number-crear',  c.number);
    toggleCriterionTailwind('c-special-crear', c.special);
    return Object.values(c).filter(Boolean).length;
  }

  function checkMatchAdmin() {
    const v1 = passInput?.value || '';
    const v2 = pass2Input?.value || '';
    if (!matchDiv) return;
    if (!v2) { matchDiv.style.color = 'transparent'; return; }

    if (v1 === v2) {
      matchDiv.style.color = '#10b981';
      if (matchIcon) matchIcon.textContent = '✓';
      if (matchText) matchText.textContent = 'Las contraseñas coinciden';
    } else {
      matchDiv.style.color = '#ef4444';
      if (matchIcon) matchIcon.textContent = '✗';
      if (matchText) matchText.textContent = 'Las contraseñas no coinciden';
    }
  }

  if (passInput) {
    passInput.addEventListener('input', () => {
      const pw = passInput.value;
      const score = pw.length ? evalPasswordTailwind(pw) : 0;

      if (!pw.length) {
        if (strengthBar) strengthBar.style.width = '0%';
        if (strengthLbl) { strengthLbl.textContent = 'Escribe una contraseña'; strengthLbl.style.color = '#94a3b8'; }
        return;
      }

      const level = LEVELS[score - 1] || LEVELS[0];
      if (strengthBar) {
        strengthBar.style.width = level.pct;
        strengthBar.style.backgroundColor = level.color;
      }
      if (strengthLbl) {
        strengthLbl.textContent = level.label;
        strengthLbl.style.color = level.color;
      }
      checkMatchAdmin();
    });
  }

  if (pass2Input) {
    pass2Input.addEventListener('input', checkMatchAdmin);
    pass2Input.addEventListener('blur', checkMatchAdmin);
  }

});
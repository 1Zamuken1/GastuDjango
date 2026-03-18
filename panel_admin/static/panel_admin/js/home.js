document.addEventListener('DOMContentLoaded', () => {

  /* ── Modal perfil ──────────────────────────────────────────── */
  const modalPerfil     = document.getElementById('modal-perfil');
  const btnOpenPerfil   = document.getElementById('btn-open-perfil');
  const btnClosePerfil  = document.getElementById('btn-close-perfil');
  const btnCancelPerfil = document.getElementById('btn-cancel-perfil');

  if (btnOpenPerfil)   btnOpenPerfil.addEventListener('click',   () => modalPerfil.classList.add('open'));
  if (btnClosePerfil)  btnClosePerfil.addEventListener('click',  () => modalPerfil.classList.remove('open'));
  if (btnCancelPerfil) btnCancelPerfil.addEventListener('click', () => modalPerfil.classList.remove('open'));
  if (modalPerfil)     modalPerfil.addEventListener('click', e => {
    if (e.target === modalPerfil) modalPerfil.classList.remove('open');
  });

  /* ── Guardar perfil ────────────────────────────────────────── */
  const formPerfil = document.getElementById('form-perfil');
  if (formPerfil) {
    formPerfil.addEventListener('submit', async function(e) {
      e.preventDefault();
      const fd  = new FormData(this);
      const msg = document.getElementById('perfil-msg');

      // PERFIL_URL se inyecta desde el template como variable global
      const res = await fetch(window.PERFIL_URL, {
        method:  'POST',
        headers: { 'X-CSRFToken': getCsrf() },
        body:    fd,
      }).then(r => r.json());

      if (res.ok) {
        msg.style.color = '#059669';
        msg.textContent = res.msg;
        const avatar = document.getElementById('perfil-avatar');
        const name   = document.getElementById('perfil-display-name');
        if (avatar) avatar.textContent = res.username[0].toUpperCase();
        if (name)   name.textContent   = res.username;
      } else {
        msg.style.color = '#ef4444';
        msg.textContent = res.msg;
      }
    });
  }

  function getCsrf() {
    return document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] || '';
  }

});
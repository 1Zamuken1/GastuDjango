/* =============================================================
   login.js  —  GastuApp
   Ruta: usuarios/static/usuarios/js/login.js
   Lógica de validación e interacción del formulario de login
   ============================================================= */

document.addEventListener('DOMContentLoaded', () => {

  lucide.createIcons();

  /* ── Animación GSAP ──────────────────────────────────────── */
  gsap.set(['#auth-header', '#auth-card'], { y: 22 });
  gsap.to('#auth-header', { opacity: 1, y: 0, duration: 0.6, ease: 'power3.out', delay: 0.15 });
  gsap.to('#auth-card',   { opacity: 1, y: 0, duration: 0.7, ease: 'power3.out', delay: 0.28 });

  /* ── Helpers ─────────────────────────────────────────────── */
  function setError(inputId, errId, msg) {
    document.getElementById(inputId).classList.add('input-error');
    const el = document.getElementById(errId);
    if (el) el.textContent = msg;
  }

  function clearError(inputId, errId) {
    document.getElementById(inputId).classList.remove('input-error');
    const el = document.getElementById(errId);
    if (el) el.textContent = '';
  }

  /* ── Toggle visibilidad contraseña ──────────────────────── */
  const passInput  = document.getElementById('id_password');
  const toggleBtn  = document.getElementById('togglePass');
  const eyeIcon    = document.getElementById('eyeIcon');

  if (toggleBtn && passInput) {
    toggleBtn.addEventListener('click', () => {
      const isPass = passInput.type === 'password';
      passInput.type = isPass ? 'text' : 'password';
      eyeIcon.setAttribute('data-lucide', isPass ? 'eye-off' : 'eye');
      lucide.createIcons();
    });
  }

  /* ── Validación en tiempo real ───────────────────────────── */
  const usernameInput = document.getElementById('id_username');

  if (usernameInput) {
    usernameInput.addEventListener('blur', () => {
      if (!usernameInput.value.trim()) {
        setError('id_username', 'err-username', 'El nombre de usuario es obligatorio.');
      } else {
        clearError('id_username', 'err-username');
      }
    });
    usernameInput.addEventListener('input', () => clearError('id_username', 'err-username'));
  }

  if (passInput) {
    passInput.addEventListener('blur', () => {
      if (!passInput.value) {
        setError('id_password', 'err-password', 'La contraseña es obligatoria.');
      } else {
        clearError('id_password', 'err-password');
      }
    });
    passInput.addEventListener('input', () => clearError('id_password', 'err-password'));
  }

  /* ── Validación al enviar ─────────────────────────────────── */
  const loginForm = document.getElementById('login-form');

  if (loginForm) {
    loginForm.addEventListener('submit', (e) => {
      let hasError = false;

      if (!usernameInput?.value.trim()) {
        setError('id_username', 'err-username', 'El nombre de usuario es obligatorio.');
        hasError = true;
      }

      if (!passInput?.value) {
        setError('id_password', 'err-password', 'La contraseña es obligatoria.');
        hasError = true;
      }

      if (hasError) e.preventDefault();
    });
  }

});
/* =============================================================
   register.js  —  GastuApp
   Ruta: usuarios/static/usuarios/js/register.js
   Lógica de validación e interacción del formulario de registro
   ============================================================= */

document.addEventListener('DOMContentLoaded', () => {

  lucide.createIcons();

  /* ── Animación GSAP ──────────────────────────────────────── */
  gsap.set(['#auth-header', '#auth-card'], { y: 22 });
  gsap.to('#auth-header', { opacity: 1, y: 0, duration: 0.6, ease: 'power3.out', delay: 0.15 });
  gsap.to('#auth-card',   { opacity: 1, y: 0, duration: 0.7, ease: 'power3.out', delay: 0.28 });

  /* ── Helpers ─────────────────────────────────────────────── */
  function setError(inputId, errId, msg) {
    const input = document.getElementById(inputId);
    const err   = document.getElementById(errId);
    if (input) { input.classList.remove('input-ok'); input.classList.add('input-error'); }
    if (err)   err.textContent = msg;
  }

  function setOk(inputId, errId) {
    const input = document.getElementById(inputId);
    const err   = document.getElementById(errId);
    if (input) { input.classList.remove('input-error'); input.classList.add('input-ok'); }
    if (err)   err.textContent = '';
  }

  function clearState(inputId, errId) {
    const input = document.getElementById(inputId);
    const err   = document.getElementById(errId);
    if (input) input.classList.remove('input-error', 'input-ok');
    if (err)   err.textContent = '';
  }

  /* ── Toggle visibilidad contraseña ──────────────────────── */
  function togglePassword(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon  = document.getElementById(iconId);
    if (!input || !icon) return;
    const isPass = input.type === 'password';
    input.type = isPass ? 'text' : 'password';
    icon.setAttribute('data-lucide', isPass ? 'eye-off' : 'eye');
    lucide.createIcons();
  }

  document.getElementById('togglePass1')
    ?.addEventListener('click', () => togglePassword('id_password1', 'eyeIcon1'));
  document.getElementById('togglePass2')
    ?.addEventListener('click', () => togglePassword('id_password2', 'eyeIcon2'));

  /* ── Validación username ──────────────────────────────────── */
  const usernameInput = document.getElementById('id_username');

  if (usernameInput) {
    usernameInput.addEventListener('blur', () => {
      const val = usernameInput.value.trim();
      if (!val) {
        setError('id_username', 'err-username', 'El nombre de usuario es obligatorio.');
      } else if (val.length < 3) {
        setError('id_username', 'err-username', 'Mínimo 3 caracteres.');
      } else if (val.length > 30) {
        setError('id_username', 'err-username', 'Máximo 30 caracteres.');
      } else if (!/^[a-zA-Z0-9_ .\-]+$/.test(val)) {
        setError('id_username', 'err-username', 'Solo letras, números, espacios, _, . y -');
      } else {
        setOk('id_username', 'err-username');
      }
    });
    usernameInput.addEventListener('input', () => clearState('id_username', 'err-username'));
  }

  /* ── Validación email ─────────────────────────────────────── */
  const emailInput = document.getElementById('id_email');

  if (emailInput) {
    emailInput.addEventListener('blur', () => {
      const val = emailInput.value.trim();
      const re  = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!val) {
        setError('id_email', 'err-email', 'El correo electrónico es obligatorio.');
      } else if (!re.test(val)) {
        setError('id_email', 'err-email', 'Ingresa un correo electrónico válido.');
      } else {
        setOk('id_email', 'err-email');
      }
    });
    emailInput.addEventListener('input', () => clearState('id_email', 'err-email'));
  }

  /* ── Validación teléfono ──────────────────────────────────── */
  const telefonoInput = document.getElementById('id_telefono');

  if (telefonoInput) {
    telefonoInput.addEventListener('blur', () => {
      const val = telefonoInput.value.trim();
      if (!val) { clearState('id_telefono', 'err-telefono'); return; }
      const digits = val.replace(/[\s\-\+]/g, '');
      if (!/^\d+$/.test(digits)) {
        setError('id_telefono', 'err-telefono', 'Solo números, espacios, + y -');
      } else if (digits.length < 7 || digits.length > 15) {
        setError('id_telefono', 'err-telefono', 'Debe tener entre 7 y 15 dígitos.');
      } else {
        setOk('id_telefono', 'err-telefono');
      }
    });
  }

  /* ── Barra de fortaleza de contraseña ─────────────────────── */
  const passInput   = document.getElementById('id_password1');
  const strengthBar = document.getElementById('strength-bar');
  const strengthLbl = document.getElementById('strength-label');

  const LEVELS = [
    { color: '#ef4444', label: 'Muy débil',  pct: '20%' },
    { color: '#f97316', label: 'Débil',      pct: '40%' },
    { color: '#eab308', label: 'Regular',    pct: '60%' },
    { color: '#10b981', label: 'Fuerte',     pct: '80%' },
    { color: '#059669', label: 'Muy fuerte', pct: '100%' },
  ];

  function toggleCriterion(id, met) {
    document.getElementById(id)?.classList.toggle('met', met);
  }

  function evalPassword(pw) {
    const c = {
      length:  pw.length >= 8,
      upper:   /[A-Z]/.test(pw),
      number:  /\d/.test(pw),
      special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pw),
    };
    toggleCriterion('c-length',  c.length);
    toggleCriterion('c-upper',   c.upper);
    toggleCriterion('c-number',  c.number);
    toggleCriterion('c-special', c.special);
    return Object.values(c).filter(Boolean).length;
  }

  if (passInput) {
    passInput.addEventListener('input', () => {
      const pw    = passInput.value;
      const score = pw.length ? evalPassword(pw) : 0;

      if (!pw.length) {
        if (strengthBar) strengthBar.style.width = '0%';
        if (strengthLbl) { strengthLbl.textContent = 'Escribe una contraseña'; strengthLbl.style.color = '#94a3b8'; }
        return;
      }

      const level = LEVELS[score - 1] || LEVELS[0];
      if (strengthBar) {
        strengthBar.style.width           = level.pct;
        strengthBar.style.backgroundColor = level.color;
      }
      if (strengthLbl) {
        strengthLbl.textContent = level.label;
        strengthLbl.style.color = level.color;
      }
    });

    passInput.addEventListener('blur', () => {
      const pw = passInput.value;
      if (!pw) {
        setError('id_password1', 'err-password1', 'La contraseña es obligatoria.');
      } else if (pw.length < 8) {
        setError('id_password1', 'err-password1', 'Mínimo 8 caracteres.');
      } else {
        setOk('id_password1', 'err-password1');
      }
      checkMatch();
    });
  }

  /* ── Coincidencia de contraseñas ──────────────────────────── */
  const pass2Input = document.getElementById('id_password2');
  const matchDiv   = document.getElementById('match-indicator');
  const matchIcon  = document.getElementById('match-icon');
  const matchText  = document.getElementById('match-text');

  function checkMatch() {
    const v1 = passInput?.value || '';
    const v2 = pass2Input?.value || '';
    if (!matchDiv) return;
    if (!v2) { matchDiv.style.color = 'transparent'; return; }

    if (v1 === v2) {
      matchDiv.style.color    = '#10b981';
      if (matchIcon) matchIcon.textContent = '✓';
      if (matchText) matchText.textContent = 'Las contraseñas coinciden';
      setOk('id_password2', 'err-password2');
    } else {
      matchDiv.style.color    = '#ef4444';
      if (matchIcon) matchIcon.textContent = '✗';
      if (matchText) matchText.textContent = 'Las contraseñas no coinciden';
      setError('id_password2', 'err-password2', 'Las contraseñas no coinciden.');
    }
  }

  pass2Input?.addEventListener('input', checkMatch);
  pass2Input?.addEventListener('blur',  checkMatch);

  /* ── Validación al enviar ─────────────────────────────────── */
  document.getElementById('register-form')?.addEventListener('submit', (e) => {
    let hasError = false;

    // Username
    const uname = usernameInput?.value.trim() || '';
    if (!uname) {
      setError('id_username', 'err-username', 'El nombre de usuario es obligatorio.');
      hasError = true;
    } else if (uname.length < 3) {
      setError('id_username', 'err-username', 'Mínimo 3 caracteres.');
      hasError = true;
    } else if (!/^[a-zA-Z0-9_ .\-]+$/.test(uname)) {
      setError('id_username', 'err-username', 'Solo letras, números, espacios, _, . y -');
      hasError = true;
    }

    // Email
    const email = emailInput?.value.trim() || '';
    if (!email) {
      setError('id_email', 'err-email', 'El correo electrónico es obligatorio.');
      hasError = true;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('id_email', 'err-email', 'Ingresa un correo electrónico válido.');
      hasError = true;
    }

    // Password1
    const pw = passInput?.value || '';
    if (!pw) {
      setError('id_password1', 'err-password1', 'La contraseña es obligatoria.');
      hasError = true;
    } else if (pw.length < 8) {
      setError('id_password1', 'err-password1', 'Mínimo 8 caracteres.');
      hasError = true;
    } else if (!/[A-Z]/.test(pw)) {
      setError('id_password1', 'err-password1', 'Incluye al menos una mayúscula.');
      hasError = true;
    } else if (!/\d/.test(pw)) {
      setError('id_password1', 'err-password1', 'Incluye al menos un número.');
      hasError = true;
    } else if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pw)) {
      setError('id_password1', 'err-password1', 'Incluye al menos un carácter especial.');
      hasError = true;
    }

    // Password2
    const pw2 = pass2Input?.value || '';
    if (!pw2) {
      setError('id_password2', 'err-password2', 'Confirma tu contraseña.');
      hasError = true;
    } else if (pw !== pw2) {
      setError('id_password2', 'err-password2', 'Las contraseñas no coinciden.');
      hasError = true;
    }

    if (hasError) e.preventDefault();
  });

});
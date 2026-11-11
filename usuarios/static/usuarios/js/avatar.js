/* =============================================================
   avatar.js — Selector del pool de avatares en Mi perfil.
   Los datos llegan en data- del modal y de cada opcion; al guardar
   se actualizan todos los [data-avatar-slot] (hero y barra superior)
   sin recargar la pagina.
   ============================================================= */
(function () {
  'use strict';

  var modal = document.getElementById('modal-avatar');
  var abrir = document.getElementById('btn-cambiar-avatar');
  if (!modal || !abrir) return;

  var opciones = Array.prototype.slice.call(modal.querySelectorAll('.avatar-opcion'));
  var preview = document.getElementById('avatar-preview');
  var previewNombre = document.getElementById('avatar-preview-nombre');
  var btnGuardar = document.getElementById('btn-guardar-avatar');
  var actual = modal.getAttribute('data-actual') || '';
  var foto = modal.getAttribute('data-foto') || '';
  var inicial = modal.getAttribute('data-inicial') || '';
  var elegido = actual;

  function iconos() {
    if (window.lucide) window.lucide.createIcons();
  }

  // Avatar a mostrar segun la clave elegida ("" = automatico)
  function avatarDe(clave) {
    var op = opciones.filter(function (o) { return o.getAttribute('data-avatar') === clave; })[0];
    if (clave && op) {
      return { tipo: 'pool', icono: op.getAttribute('data-icono'), color: op.getAttribute('data-color') };
    }
    if (foto) return { tipo: 'foto', url: foto };
    return { tipo: 'inicial', inicial: inicial };
  }

  // Pinta un avatar dentro de un elemento .avatar-ui sin usar innerHTML con datos
  function pintar(el, avatar) {
    el.classList.remove('avatar-ui--pool', 'avatar-ui--foto', 'avatar-ui--inicial');
    el.classList.add('avatar-ui--' + avatar.tipo);
    el.style.removeProperty('--avatar-color');
    while (el.firstChild) el.removeChild(el.firstChild);

    var hijo;
    if (avatar.tipo === 'pool') {
      el.style.setProperty('--avatar-color', avatar.color);
      hijo = document.createElement('i');
      hijo.setAttribute('data-lucide', avatar.icono);
    } else if (avatar.tipo === 'foto') {
      hijo = document.createElement('img');
      hijo.src = avatar.url;
      hijo.alt = '';
      hijo.referrerPolicy = 'no-referrer';
    } else {
      hijo = document.createElement('span');
      hijo.textContent = avatar.inicial;
    }
    hijo.setAttribute('aria-hidden', 'true');
    el.appendChild(hijo);
  }

  function seleccionar(clave) {
    elegido = clave;
    opciones.forEach(function (o) {
      o.setAttribute('aria-checked', o.getAttribute('data-avatar') === clave ? 'true' : 'false');
      o.tabIndex = o.getAttribute('data-avatar') === clave ? 0 : -1;
    });
    var op = opciones.filter(function (o) { return o.getAttribute('data-avatar') === clave; })[0];
    previewNombre.textContent = op ? op.getAttribute('data-nombre') : 'Automático';
    pintar(preview, avatarDe(clave));
    iconos();
  }

  function abrirModal() {
    seleccionar(actual);
    modal.classList.add('visible');
    modal.setAttribute('aria-hidden', 'false');
    var marcada = modal.querySelector('.avatar-opcion[aria-checked="true"]') || opciones[0];
    setTimeout(function () { marcada.focus(); }, 50);
  }

  function cerrarModal() {
    modal.classList.remove('visible');
    modal.setAttribute('aria-hidden', 'true');
    abrir.focus();
  }

  function csrf() {
    if (typeof CSRF_TOKEN !== 'undefined') return CSRF_TOKEN;
    var m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function guardar() {
    if (elegido === actual) { cerrarModal(); return; }
    btnGuardar.disabled = true;
    var cuerpo = new URLSearchParams();
    cuerpo.append('avatar', elegido);
    fetch(modal.getAttribute('data-url'), {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': csrf(), 'Content-Type': 'application/x-www-form-urlencoded' },
      body: cuerpo.toString()
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, datos: d }; }); })
      .then(function (res) {
        if (!res.ok || !res.datos.ok) throw new Error((res.datos && res.datos.error) || 'No se pudo guardar el avatar.');
        actual = res.datos.avatar.clave || '';
        modal.setAttribute('data-actual', actual);
        document.querySelectorAll('[data-avatar-slot]').forEach(function (el) { pintar(el, res.datos.avatar); });
        iconos();
        cerrarModal();
        if (window.GastuAlerts) window.GastuAlerts.toastSuccess('Avatar actualizado');
      })
      .catch(function (err) {
        var msg = err && err.message && err.message.indexOf('JSON') === -1 ? err.message : 'No se pudo guardar el avatar.';
        if (window.GastuAlerts && window.GastuAlerts.toastError) window.GastuAlerts.toastError(msg);
      })
      .then(function () { btnGuardar.disabled = false; });
  }

  abrir.addEventListener('click', abrirModal);
  document.getElementById('btn-cerrar-avatar').addEventListener('click', cerrarModal);
  document.getElementById('btn-cancelar-avatar').addEventListener('click', cerrarModal);
  btnGuardar.addEventListener('click', guardar);
  modal.addEventListener('click', function (e) { if (e.target === modal) cerrarModal(); });

  opciones.forEach(function (o, i) {
    o.addEventListener('click', function () { seleccionar(o.getAttribute('data-avatar')); });
    // Flechas para moverse por el grupo de opciones (patron radiogroup)
    o.addEventListener('keydown', function (e) {
      var paso = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
      if (!paso) return;
      e.preventDefault();
      var sig = opciones[(i + paso + opciones.length) % opciones.length];
      seleccionar(sig.getAttribute('data-avatar'));
      sig.focus();
    });
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && modal.classList.contains('visible')) cerrarModal();
  });
})();

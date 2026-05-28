/**
 * perfil.js — Controlador de tabs y notificaciones
 */

document.addEventListener('DOMContentLoaded', function () {

  // ── Tabs ────────────────────────────────────────────────
  var tabs = document.querySelectorAll('.perfil-tab');
  var panels = document.querySelectorAll('.perfil-panel');

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      var target = tab.getAttribute('data-tab');

      tabs.forEach(function (t) {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');

      panels.forEach(function (p) {
        p.classList.remove('active');
      });
      var panel = document.querySelector('.perfil-panel[data-panel="' + target + '"]');
      if (panel) panel.classList.add('active');

      var url = new URL(window.location);
      url.searchParams.set('tab', target);
      window.history.replaceState({}, '', url);

      if (target === 'notificaciones') {
        cargarNotificaciones();
      }
    });
  });

  // ── Toggle password visibility ──────────────────────────
  document.querySelectorAll('.toggle-pass').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var input = document.getElementById(btn.getAttribute('data-target'));
      var icon = btn.querySelector('i');
      if (input.type === 'password') {
        input.type = 'text';
        icon.setAttribute('data-lucide', 'eye-off');
      } else {
        input.type = 'password';
        icon.setAttribute('data-lucide', 'eye');
      }
      lucide.createIcons();
    });
  });

  // ── Password Strength and Match (Perfil) ────────────────
  var passInput = document.getElementById('id_new_password1');
  var pass2Input = document.getElementById('id_new_password2');
  var strengthBar = document.getElementById('strength-bar-perfil');
  var strengthLbl = document.getElementById('strength-label-perfil');
  var matchDiv = document.getElementById('match-indicator-perfil');
  var matchIcon = document.getElementById('match-icon-perfil');
  var matchText = document.getElementById('match-text-perfil');

  var LEVELS = [
    { color: '#ef4444', label: 'Muy débil',  pct: '20%' },
    { color: '#f97316', label: 'Débil',      pct: '40%' },
    { color: '#eab308', label: 'Regular',    pct: '60%' },
    { color: '#10b981', label: 'Fuerte',     pct: '80%' },
    { color: '#059669', label: 'Muy fuerte', pct: '100%' },
  ];

  function toggleCriterion(id, met) {
    var el = document.getElementById(id);
    if (el) el.classList.toggle('met', met);
  }

  function evalPassword(pw) {
    var c = {
      length:  pw.length >= 8,
      upper:   /[A-Z]/.test(pw),
      number:  /\d/.test(pw),
      special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pw),
    };
    toggleCriterion('c-length-perfil',  c.length);
    toggleCriterion('c-upper-perfil',   c.upper);
    toggleCriterion('c-number-perfil',  c.number);
    toggleCriterion('c-special-perfil', c.special);
    var metCount = 0;
    if(c.length) metCount++;
    if(c.upper) metCount++;
    if(c.number) metCount++;
    if(c.special) metCount++;
    return metCount;
  }

  function checkMatch() {
    var v1 = passInput ? passInput.value : '';
    var v2 = pass2Input ? pass2Input.value : '';
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
    passInput.addEventListener('input', function () {
      var pw = passInput.value;
      var score = pw.length ? evalPassword(pw) : 0;

      if (!pw.length) {
        if (strengthBar) strengthBar.style.width = '0%';
        if (strengthLbl) { strengthLbl.textContent = 'Escribe una contraseña'; strengthLbl.style.color = '#94a3b8'; }
        return;
      }

      var level = LEVELS[score - 1] || LEVELS[0];
      if (strengthBar) {
        strengthBar.style.width = level.pct;
        strengthBar.style.backgroundColor = level.color;
      }
      if (strengthLbl) {
        strengthLbl.textContent = level.label;
        strengthLbl.style.color = level.color;
      }
      checkMatch();
    });
  }

  if (pass2Input) {
    pass2Input.addEventListener('input', checkMatch);
    pass2Input.addEventListener('blur', checkMatch);
  }

  // ── Auto-hide toasts ───────────────────────────────────
  document.querySelectorAll('.perfil-toast').forEach(function (el) {
    setTimeout(function () {
      el.style.transition = 'opacity 0.4s ease';
      el.style.opacity = '0';
      setTimeout(function () { el.style.display = 'none'; }, 400);
    }, 4000);
  });

  // ── Notificaciones ─────────────────────────────────────

  var moduloActivo = 'TODOS';

  var notifFiltersEl = document.getElementById('notif-filters');
  var csrfToken = notifFiltersEl ? (notifFiltersEl.getAttribute('data-csrf') || '') : '';

  var notifPendingCtrl = null;

  /**
   * Map de iconos por tipo de notificación.
   * Colores semánticos por tipo (solo para el icono circular interno).
   */
  var ICON_MAP = {
    DEFICIT:                  { icon: 'trending-down',  color: '#2563eb', bg: '#eff6ff' },
    EGRESO_GRANDE:            { icon: 'arrow-up-right', color: '#e11d48', bg: '#fef2f2' },
    UMBRAL_MENSUAL:           { icon: 'alert-triangle', color: '#d97706', bg: '#fffbeb' },
    GASTO_INCREMENTAL:        { icon: 'trending-up',   color: '#e11d48', bg: '#fff1f2' },
    REDUCCION_INGRESOS:       { icon: 'trending-down',  color: '#6366f1', bg: '#eef2ff' },
    PATRON_INUSUAL:           { icon: 'eye',            color: '#2563eb', bg: '#eff6ff' },
    CONCENTRACION_GASTO:      { icon: 'bar-chart-3',    color: '#e11d48', bg: '#fff1f2' },
    CONCEPTO_SIN_USO:         { icon: 'circle-help',    color: '#d97706', bg: '#fffbeb' },
    VELOCIDAD_GASTO:          { icon: 'zap',            color: '#e11d48', bg: '#fff1f2' },
    INACTIVIDAD_INGRESOS:     { icon: 'pause',          color: '#6366f1', bg: '#eef2ff' },
    EGRESOS_AGRUPADOS:        { icon: 'layers',         color: '#e11d48', bg: '#fff1f2' },
    MICRO_GASTOS:             { icon: 'coins',          color: '#d97706', bg: '#fffbeb' },
    GASTOS_HORMIGA:           { icon: 'bug',            color: '#b45309', bg: '#fffbeb' },
    PROYECCION_SOBREGASTO:    { icon: 'activity',       color: '#2563eb', bg: '#eff6ff' },
    COMPARACION_PERIODO:      { icon: 'git-compare',    color: '#d97706', bg: '#fffbeb' },
    DIA_MES_CRITICO:          { icon: 'calendar-x',     color: '#e11d48', bg: '#fff1f2' },
    EGRESO_SIN_CONCEPTO:      { icon: 'tag-off',        color: '#64748b', bg: '#f1f5f9' },
    INGRESO_INUSUAL:          { icon: 'banknote',       color: '#10b981', bg: '#ecfdf5' },
  };

  function getPanel() {
    return document.querySelector('.perfil-panel[data-panel="notificaciones"]');
  }

  function getLista() {
    var panel = getPanel();
    return panel ? panel.querySelector('#perfil-notif-lista') : null;
  }

  function escapeHtml(text) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
  }

  /**
   * Renderiza una card HTML. Boton "marcar como leida" solo en no-leidas.
   */
  function buildCard(n) {
    var ic = ICON_MAP[n.tipo] || { icon: 'bell', color: '#10b981', bg: '#ecfdf5' };
    var mod = n.modulo || 'GENERAL';
    var cls = n.leida ? 'read' : 'unread';
    var btn = '';
    if (!n.leida) {
      btn = '<button class="notif-read-btn" data-notif-id="' + n.id + '" title="Marcar como leida">' +
              '<i data-lucide="check"></i></button>';
    }
    return '<div class="notif-item ' + cls + '" data-notif-id="' + n.id + '" data-modulo="' + mod + '">' +
      '<div class="notif-icon-wrap" style="background:' + ic.bg + ';color:' + ic.color + '">' +
        '<i data-lucide="' + ic.icon + '"></i>' +
      '</div>' +
      '<div class="notif-body">' +
        '<p class="notif-title">' + escapeHtml(n.titulo) + '</p>' +
        '<p class="notif-desc">' + escapeHtml(n.descripcion) + '</p>' +
        '<div class="notif-meta"><span class="notif-time">' + n.fecha + '</span></div>' +
      '</div>' +
      btn +
    '</div>';
  }

  /**
   * Fetch + render. Siempre ejecuta — sin guards que impidan la carga.
   */
  function cargarNotificaciones() {
    var lista = getLista();
    if (!lista) {
      console.error('perfils: #perfil-notif-lista no encontrado');
      return;
    }

    // Cancelar request previo
    if (notifPendingCtrl) {
      notifPendingCtrl.abort();
      notifPendingCtrl = null;
    }

    lista.innerHTML = '<div class="notif-loading">' +
      '<i data-lucide="loader"></i>' +
      '<span>Cargando notificaciones...</span>' +
    '</div>';
    lucide.createIcons();

    var url = '/notificaciones/json/';
    if (moduloActivo !== 'TODOS') {
      url += '?modulo=' + moduloActivo;
    }

    var ctrl = new AbortController();
    notifPendingCtrl = ctrl;

    fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      signal: ctrl.signal,
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        notifPendingCtrl = null;

        // Verificar respuesta
        if (!data || !data.ok) {
          lista.innerHTML = '<div class="notif-empty">' +
            '<i data-lucide="alert-triangle"></i>' +
            '<span>El servidor no devolvió datos</span>' +
          '</div>';
          lucide.createIcons();
          return;
        }

        // Actualizar contadores en los pills
        var pills = document.querySelectorAll('.notif-pill');
        pills.forEach(function (pill) {
          var pillMod = pill.getAttribute('data-modulo');
          var count = (pillMod === 'TODOS') ? data.total_no_leidas : ((data.recuentos_modulos && data.recuentos_modulos[pillMod]) || 0);
          var countBadge = pill.querySelector('.notif-pill-count');
          if (count > 0) {
            if (!countBadge) {
              countBadge = document.createElement('span');
              countBadge.className = 'notif-pill-count';
              pill.appendChild(countBadge);
            }
            countBadge.textContent = count;
          } else {
            if (countBadge) countBadge.remove();
          }
        });

        // Actualizar campana en la topbar
        var topbarBadge = document.querySelector('#notif-btn .notif-badge');
        if (data.total_no_leidas > 0) {
          if (!topbarBadge) {
            topbarBadge = document.createElement('span');
            topbarBadge.className = 'notif-badge';
            var notifBtn = document.getElementById('notif-btn');
            if (notifBtn) notifBtn.appendChild(topbarBadge);
          }
          if (topbarBadge) topbarBadge.textContent = data.total_no_leidas;
        } else {
          if (topbarBadge) topbarBadge.remove();
        }

        var notifs = data.notificaciones;
        if (!notifs || notifs.length === 0) {
          lista.innerHTML = '<div class="notif-empty">' +
            '<i data-lucide="bell-off"></i>' +
            '<span>Sin notificaciones en esta categoria</span>' +
          '</div>';
          lucide.createIcons();
          return;
        }

        // Renderizar cards
        lista.innerHTML = notifs.map(buildCard).join('');
        lucide.createIcons();

        // Ocultar pills de modulos vacios
        // ocultarPillsVacias(notifs);
      })
      .catch(function (err) {
        notifPendingCtrl = null;
        if (err.name === 'AbortError') return;
        console.error('perfils fetch error:', err.message, err);
        lista.innerHTML = '<div class="notif-empty">' +
          '<i data-lucide="alert-triangle"></i>' +
          '<span>Error al cargar notificaciones</span>' +
        '</div>';
        lucide.createIcons();
      });
  }

  /**
   * Oculta los pills de modulo cuando no hay notificaciones de ese tipo.
   * Siempre deja visible "Todos".
   */
  function ocultarPillsVacias(notifs) {
    var counts = {};
    for (var i = 0; i < notifs.length; i++) {
      var mod = notifs[i].modulo || 'GENERAL';
      counts[mod] = (counts[mod] || 0) + 1;
    }
    var pills = document.querySelectorAll('.notif-pill');
    for (var i = 0; i < pills.length; i++) {
      var pillMod = pills[i].getAttribute('data-modulo');
      if (pillMod === 'TODOS') continue;
      pills[i].style.display = (counts[pillMod] ? '' : 'none');
    }
  }

  // ── Individual mark-as-read (delegation) ───────────────
  var listaEl = getLista();
  if (listaEl) {
    listaEl.addEventListener('click', function (e) {
      var btn = e.target.closest('.notif-read-btn');
      if (!btn) return;

      var notifId = btn.getAttribute('data-notif-id');
      var card = btn.closest('.notif-item');
      if (!card) return;

      fetch('/notificaciones/marcar-leidas/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ ids: [notifId] }),
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.ok) {
            card.classList.remove('unread');
            card.classList.add('read');
            btn.remove();
          }
        });
    });
  }

  // ── Pill filter clicks (delegation) ────────────────────
  var filtersContainer = document.querySelector('.notif-filters');
  if (filtersContainer) {
    filtersContainer.addEventListener('click', function (e) {
      var pill = e.target.closest('.notif-pill');
      if (!pill) return;
      e.preventDefault();

      var active = document.querySelectorAll('.notif-pill.active');
      for (var i = 0; i < active.length; i++) {
        active[i].classList.remove('active');
      }
      pill.classList.add('active');
      moduloActivo = pill.getAttribute('data-modulo');
      cargarNotificaciones();
    });
  }

  // ── Mark all as read ───────────────────────────────────
  var notifPanel = getPanel();
  var btnMarcar = notifPanel ? notifPanel.querySelector('#btn-marcar-todas') : null;
  if (btnMarcar) {
    btnMarcar.addEventListener('click', function () {
      var body = {};
      if (moduloActivo !== 'TODOS') {
        body.modulo = moduloActivo;
      }
      fetch('/notificaciones/marcar-leidas/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(body),
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.ok) cargarNotificaciones();
        });
    });
  }

  // ── Auto-load si el tab de notificaciones esta activo al iniciar ──
  var panelActivo = document.querySelector('.perfil-panel.active');
  if (panelActivo && panelActivo.getAttribute('data-panel') === 'notificaciones') {
    cargarNotificaciones();
  }

  // ── Deep-link: ?notif=ID → scroll + highlight + marcar leída ──
  (function() {
    var urlParams = new URLSearchParams(window.location.search);
    var notifId = urlParams.get('notif');
    if (!notifId) return;

    // Esperar a que las notificaciones se rendericen y luego hacer scroll
    function scrollYHighlight() {
      var card = document.querySelector('.notif-item[data-notif-id="' + notifId + '"]');
      if (!card) return false;

      // Scroll suave al card
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });

      // Añadir highlight visual temporal
      card.style.transition = 'box-shadow 0.3s, background 0.3s';
      card.style.background = '#fef9c3';
      card.style.boxShadow = '0 0 0 2px #f59e0b';
      card.style.borderRadius = '10px';
      setTimeout(function() {
        card.style.background = '';
        card.style.boxShadow = '';
      }, 2500);

      // Si no está leída, marcarla como leída
      if (card.classList.contains('unread')) {
        var csrfForDeep = notifFiltersEl ? (notifFiltersEl.getAttribute('data-csrf') || '') : '';
        fetch('/notificaciones/marcar-leidas/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfForDeep,
          },
          body: JSON.stringify({ ids: [notifId] }),
        })
          .then(function(r) { return r.json(); })
          .then(function(d) {
            if (d.ok) {
              card.classList.remove('unread');
              card.classList.add('read');
              var btn = card.querySelector('.notif-read-btn');
              if (btn) btn.remove();
            }
          })
          .catch(function() {});
      }

      // Limpiar el param de la URL sin recargar
      var cleanUrl = new URL(window.location);
      cleanUrl.searchParams.delete('notif');
      window.history.replaceState({}, '', cleanUrl);
      return true;
    }

    // Intentar varias veces mientras el fetch de notificaciones termina
    var attempts = 0;
    var maxAttempts = 20;
    var interval = setInterval(function() {
      attempts++;
      if (scrollYHighlight() || attempts >= maxAttempts) {
        clearInterval(interval);
      }
    }, 150);
  })();

  // ══════════════════════════════════════════════════════════
  //  ELIMINAR CUENTA — Modal + Slide to Confirm
  // ══════════════════════════════════════════════════════════

  var modalOverlay   = document.getElementById('modal-eliminar');
  var btnAbrir       = document.getElementById('btn-abrir-eliminar');
  var btnCerrar      = document.getElementById('btn-cerrar-eliminar');
  var deletePassword = document.getElementById('delete-password');
  var deleteError    = document.getElementById('delete-error');
  var slideCont      = document.getElementById('slide-container');
  var slideTrack     = document.getElementById('slide-track');
  var slideThumb     = document.getElementById('slide-thumb');
  var slideProgress  = document.getElementById('slide-progress');
  var slideText      = document.getElementById('slide-text');
  var hiddenPw       = document.getElementById('delete-password-hidden');
  var formEliminar   = document.getElementById('form-eliminar-cuenta');

  function abrirModal() {
    if (!modalOverlay) return;
    modalOverlay.classList.add('visible');
    document.body.style.overflow = 'hidden';
    if (deletePassword) deletePassword.value = '';
    if (deleteError) deleteError.textContent = '';
    resetSlider();
    actualizarSlider();
    lucide.createIcons();
  }

  function cerrarModal() {
    if (!modalOverlay) return;
    modalOverlay.classList.remove('visible');
    document.body.style.overflow = '';
    resetSlider();
  }

  if (btnAbrir) btnAbrir.addEventListener('click', abrirModal);
  if (btnCerrar) btnCerrar.addEventListener('click', cerrarModal);

  if (modalOverlay) {
    modalOverlay.addEventListener('mousedown', function (e) {
      if (e.target === modalOverlay && !isDragging) cerrarModal();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modalOverlay.classList.contains('visible')) {
        cerrarModal();
      }
    });
  }

  // Toggle visibility del password del modal
  if (modalOverlay) {
    modalOverlay.querySelectorAll('.toggle-pass').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var input = document.getElementById(btn.getAttribute('data-target'));
        var icon = btn.querySelector('i');
        if (input.type === 'password') {
          input.type = 'text';
          icon.setAttribute('data-lucide', 'eye-off');
        } else {
          input.type = 'password';
          icon.setAttribute('data-lucide', 'eye');
        }
        lucide.createIcons();
      });
    });
  }

  // Habilitar/deshabilitar slider segun el password
  function actualizarSlider() {
    if (!slideCont || !deletePassword) return;
    var tiene = deletePassword.value.trim().length > 0;
    if (tiene) {
      slideCont.classList.add('enabled');
    } else {
      slideCont.classList.remove('enabled');
    }
  }

  if (deletePassword) {
    deletePassword.addEventListener('input', function () {
      actualizarSlider();
      if (deleteError) deleteError.textContent = '';
    });
  }

  // ── Slide to Confirm ──────────────────────────────────

  var isDragging  = false;
  var startX      = 0;
  var thumbStartX = 3; // initial left offset
  var maxTravel   = 0;
  var completed   = false;

  function resetSlider() {
    completed = false;
    isDragging = false;
    if (slideThumb) {
      slideThumb.style.left = '3px';
      slideThumb.classList.remove('returning');
    }
    if (slideProgress) slideProgress.style.width = '0';
    if (slideTrack) slideTrack.classList.remove('completed', 'shake');
    if (slideText) slideText.textContent = 'Desliza para confirmar';
  }

  function getMaxTravel() {
    if (!slideTrack || !slideThumb) return 0;
    return slideTrack.offsetWidth - slideThumb.offsetWidth - 6;
  }

  function onDragStart(clientX) {
    if (completed) return;
    isDragging = true;
    maxTravel = getMaxTravel();
    startX = clientX;
    thumbStartX = parseInt(slideThumb.style.left, 10) || 3;
    slideThumb.classList.remove('returning');
  }

  function onDragMove(clientX) {
    if (!isDragging || completed) return;
    var dx = clientX - startX;
    var newLeft = Math.max(3, Math.min(thumbStartX + dx, maxTravel));
    slideThumb.style.left = newLeft + 'px';
    slideProgress.style.width = newLeft + 'px';

    var pct = newLeft / maxTravel;
    slideText.style.opacity = String(1 - pct * 1.5);
  }

  function onDragEnd() {
    if (!isDragging || completed) return;
    isDragging = false;
    var currentLeft = parseInt(slideThumb.style.left, 10) || 3;
    maxTravel = getMaxTravel();

    if (currentLeft >= maxTravel * 0.92) {
      completed = true;
      slideThumb.style.left = maxTravel + 'px';
      slideTrack.classList.add('completed');
      slideText.textContent = 'Eliminando cuenta...';
      slideText.style.opacity = '1';
      enviarEliminacion();
    } else {
      slideThumb.classList.add('returning');
      slideThumb.style.left = '3px';
      slideProgress.style.width = '0';
      slideText.style.opacity = '1';
    }
  }

  if (slideThumb) {
    slideThumb.addEventListener('mousedown', function (e) {
      e.preventDefault();
      onDragStart(e.clientX);
    });
    slideThumb.addEventListener('touchstart', function (e) {
      onDragStart(e.touches[0].clientX);
    }, { passive: true });
  }

  document.addEventListener('mousemove', function (e) {
    if (isDragging) onDragMove(e.clientX);
  });
  document.addEventListener('touchmove', function (e) {
    if (isDragging) onDragMove(e.touches[0].clientX);
  }, { passive: true });
  document.addEventListener('mouseup', onDragEnd);
  document.addEventListener('touchend', onDragEnd);

  function enviarEliminacion() {
    var pw = deletePassword ? deletePassword.value.trim() : '';
    if (hiddenPw) hiddenPw.value = pw;

    var formData = new FormData(formEliminar);

    fetch('/perfil/', {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      body: formData,
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          slideText.textContent = 'Cuenta eliminada';
          setTimeout(function () {
            window.location.href = data.redirect || '/';
          }, 800);
        } else {
          if (deleteError) deleteError.textContent = data.msg || 'Error al eliminar.';
          resetSlider();
          slideTrack.classList.add('shake');
          setTimeout(function () {
            slideTrack.classList.remove('shake');
          }, 400);
        }
      })
      .catch(function () {
        if (deleteError) deleteError.textContent = 'Error de conexion.';
        resetSlider();
      });
  }

  // ══════════════════════════════════════════════════════════
  //  AJAX FORM SUBMISSIONS (Perfil, Password, Preferencias)
  // ══════════════════════════════════════════════════════════
  
  function handleFormSubmit(e, form) {
    e.preventDefault();
    var formData = new FormData(form);
    
    // Clear errors
    form.querySelectorAll('.form-error').forEach(function(el) { el.textContent = ''; });

    var btn = form.querySelector('button[type="submit"]');
    var originalBtnContent = '';
    if (btn) {
      originalBtnContent = btn.innerHTML;
      btn.innerHTML = '<i data-lucide="loader" style="width:14px;height:14px;animation:spin 1s linear infinite;"></i> Guardando...';
      btn.disabled = true;
      lucide.createIcons();
    }

    fetch('/perfil/', {
      method: 'POST',
      body: formData,
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (btn) {
        btn.innerHTML = originalBtnContent;
        btn.disabled = false;
        lucide.createIcons();
      }

      if (data.ok) {
        if (window.GastuAlerts) {
          window.GastuAlerts.toastSuccess(data.mensaje || 'Actualizado correctamente');
        }
        if (form.id === 'password-form') {
          form.reset();
        }
      } else {
        if (window.GastuAlerts) {
          window.GastuAlerts.toastError('Por favor corrige los errores');
        }
        if (data.errors) {
          for (var field in data.errors) {
            var errorEl = document.getElementById('error-' + field);
            if (errorEl) {
              errorEl.textContent = data.errors[field][0];
            }
          }
        }
      }
    })
    .catch(function(err) {
      if (btn) {
        btn.innerHTML = originalBtnContent;
        btn.disabled = false;
        lucide.createIcons();
      }
      if (window.GastuAlerts) {
        window.GastuAlerts.toastError('Error de conexion');
      }
    });
  }

  var formPerfil = document.getElementById('perfil-form');
  var formPassword = document.getElementById('password-form');
  var formPreferencias = document.getElementById('preferencias-form');

  if (formPerfil) {
    formPerfil.addEventListener('submit', function(e) { handleFormSubmit(e, formPerfil); });
  }
  if (formPassword) {
    formPassword.addEventListener('submit', function(e) { handleFormSubmit(e, formPassword); });
  }
  if (formPreferencias) {
    formPreferencias.addEventListener('submit', function(e) { handleFormSubmit(e, formPreferencias); });
  }

})
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
        ocultarPillsVacias(notifs);
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

})

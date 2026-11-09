/**
 * Pestana "Por revisar" del panel de notificaciones (base_app.html).
 * Muestra los movimientos bancarios detectados y permite confirmarlos con un toque.
 */
(function () {
  'use strict';

  var lista = document.getElementById('notif-pendientes');
  if (!lista) return;

  var URL_DETECTADOS = lista.dataset.urlDetectados;
  var URL_CAPTURA = lista.dataset.urlCaptura;
  var MAX_ITEMS = 5;
  var ICONO = { compra: 'shopping-bag', transferencia: 'arrow-left-right', retiro: 'banknote', pago: 'receipt', abono: 'wallet' };

  var listaNotif = document.getElementById('notif-lista');
  var contador = document.getElementById('notif-tab-pendientes');
  var footer = document.getElementById('notif-footer-link');
  var footerTextoOriginal = footer ? footer.querySelector('span').textContent : '';
  var footerHrefOriginal = footer ? footer.getAttribute('href') : '';
  var tabActiva = 'todas';

  function csrf() {
    var m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function el(tag, clase, texto) {
    var n = document.createElement(tag);
    if (clase) n.className = clase;
    if (texto !== undefined) n.textContent = texto;
    return n;
  }

  function icono(nombre) {
    var i = document.createElement('i');
    i.setAttribute('data-lucide', nombre);
    return i;
  }

  function actualizarContador(total) {
    if (!contador) return;
    contador.hidden = !total;
    contador.textContent = total > 99 ? '99+' : total;
  }

  function vacio(texto, iconoNombre) {
    var caja = el('div', 'notif-dropdown-empty');
    caja.appendChild(icono(iconoNombre));
    caja.appendChild(el('span', '', texto));
    return caja;
  }

  function crearItem(d) {
    var esIngreso = d.tipo === 'INGRESO';
    var item = el('div', 'notif-pend-item' + (esIngreso ? ' notif-pend-item--ingreso' : ''));

    var ic = el('div', 'notif-pend-icono');
    ic.appendChild(icono(ICONO[d.operacion] || 'circle-dollar-sign'));
    item.appendChild(ic);

    var cuerpo = el('div', 'notif-pend-cuerpo');
    var fila = el('div', 'notif-pend-fila');
    fila.appendChild(el('p', 'notif-pend-comercio', d.comercio));
    fila.appendChild(el('p', 'notif-pend-monto', (esIngreso ? '+' : '-') + d.monto_formateado));
    cuerpo.appendChild(fila);
    var cat = d.categoria_sugerida ? d.categoria_sugerida.nombre : 'Sin categoría';
    cuerpo.appendChild(el('p', 'notif-pend-meta', d.banco + ' · ' + cat));
    item.appendChild(cuerpo);

    var boton = el('button', 'notif-pend-confirmar');
    boton.type = 'button';
    boton.title = 'Confirmar con la categoría ' + cat;
    boton.appendChild(icono('check'));
    if (!d.categoria_sugerida) boton.disabled = true;
    boton.addEventListener('click', function (e) {
      e.stopPropagation();
      boton.disabled = true;
      fetch(URL_DETECTADOS + d.id + '/confirmar/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest' },
        body: '{}',
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!data.ok) throw new Error(data.error || 'No se pudo confirmar');
          if (window.GastuAlerts) {
            if (data.advertencia) window.GastuAlerts.toastInfo(data.advertencia);
            else window.GastuAlerts.toastSuccess('Registrado en ' + cat);
          }
          cargar();
          window.dispatchEvent(new CustomEvent('captura:cambio'));
        })
        .catch(function (err) {
          boton.disabled = false;
          if (window.GastuAlerts) window.GastuAlerts.toastError(err.message);
        });
    });
    item.appendChild(boton);

    item.addEventListener('click', function () { window.location.href = URL_CAPTURA; });
    return item;
  }

  function cargar() {
    return fetch(URL_DETECTADOS + '?limite=' + MAX_ITEMS, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) throw new Error();
        actualizarContador(data.total);
        lista.innerHTML = '';
        if (!data.detectados.length) {
          lista.appendChild(vacio('No tienes movimientos por revisar', 'inbox'));
        } else {
          data.detectados.forEach(function (d) { lista.appendChild(crearItem(d)); });
          if (data.total > MAX_ITEMS) {
            var mas = el('a', 'notif-pend-mas', 'Y ' + (data.total - MAX_ITEMS) + ' más por revisar');
            mas.href = URL_CAPTURA;
            lista.appendChild(mas);
          }
        }
        if (window.lucide) window.lucide.createIcons();
      })
      .catch(function () {
        lista.innerHTML = '';
        lista.appendChild(vacio('No se pudieron cargar los movimientos', 'alert-triangle'));
        if (window.lucide) window.lucide.createIcons();
      });
  }

  function mostrarTab(nombre) {
    tabActiva = nombre;
    document.querySelectorAll('.notif-tab').forEach(function (t) {
      t.classList.toggle('activo', t.dataset.notifTab === nombre);
    });
    var pendientes = nombre === 'pendientes';
    lista.hidden = !pendientes;
    if (listaNotif) listaNotif.hidden = pendientes;
    if (footer) {
      footer.querySelector('span').textContent = pendientes ? 'Revisar en Captura automática' : footerTextoOriginal;
      footer.setAttribute('href', pendientes ? URL_CAPTURA : footerHrefOriginal);
    }
    if (pendientes) cargar();
  }

  document.querySelectorAll('.notif-tab').forEach(function (t) {
    t.addEventListener('click', function () { mostrarTab(t.dataset.notifTab); });
  });

  // Al abrir el panel se refresca el contador; si estaba en pendientes, tambien la lista.
  var botonCampana = document.getElementById('notif-btn');
  if (botonCampana) {
    botonCampana.addEventListener('click', function () {
      if (tabActiva === 'pendientes') cargar();
      else refrescarContador();
    });
  }

  function refrescarContador() {
    fetch(URL_DETECTADOS + '?limite=1', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.json(); })
      .then(function (data) { if (data.ok) actualizarContador(data.total); })
      .catch(function () {});
  }

  refrescarContador();
})();

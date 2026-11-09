/**
 * Captura automatica: onboarding, bandeja de pendientes, historial y reglas.
 * Las URLs llegan por atributos data- del contenedor #captura-app.
 */
(function () {
  'use strict';

  var app = document.getElementById('captura-app');
  if (!app) return;

  var URL = {
    resumen: app.dataset.urlResumen,
    buzon: app.dataset.urlBuzon,
    regenerar: app.dataset.urlRegenerar,
    detectados: app.dataset.urlDetectados,
    lote: app.dataset.urlLote,
    reglas: app.dataset.urlReglas,
    baseDetectado: app.dataset.urlBaseDetectado,
    baseRegla: app.dataset.urlBaseRegla,
  };

  var ICONO_OPERACION = {
    compra: 'shopping-bag',
    transferencia: 'arrow-left-right',
    retiro: 'banknote',
    pago: 'receipt',
    abono: 'wallet',
  };

  var estado = {
    resumen: null,
    pendientes: [],
    categoriaElegida: {},   // id detectado -> {id, nombre}
    tabActiva: 'pendientes',
    cargado: { historial: false, reglas: false },
    sondeo: null,
  };

  var $ = function (id) { return document.getElementById(id); };

  // ── Utilidades ─────────────────────────────────────────────
  function csrf() {
    var m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function pedir(url, opciones) {
    opciones = opciones || {};
    var config = { method: opciones.method || 'GET', headers: { 'X-Requested-With': 'XMLHttpRequest' } };
    if (config.method !== 'GET') {
      config.headers['X-CSRFToken'] = csrf();
      config.headers['Content-Type'] = 'application/json';
      config.body = JSON.stringify(opciones.body || {});
    }
    return fetch(url, config).then(function (r) {
      var esJson = (r.headers.get('Content-Type') || '').indexOf('application/json') !== -1;
      if (!esJson) throw new Error('Error del servidor (' + r.status + '). Recarga la página e intenta de nuevo.');
      return r.json().then(function (data) {
        if (!r.ok || data.ok === false) throw new Error(data.error || 'Error del servidor');
        return data;
      });
    });
  }

  function aviso(tipo, mensaje) {
    var A = window.GastuAlerts;
    if (!A) return;
    if (tipo === 'ok') A.toastSuccess(mensaje);
    else if (tipo === 'info') A.toastInfo(mensaje);
    else A.toastError(mensaje);
  }

  function iconos() { if (window.lucide) window.lucide.createIcons(); }

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

  function hora(iso) {
    return new Date(iso).toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' });
  }

  function fechaCorta(iso) {
    return new Date(iso).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' });
  }

  function haceCuanto(iso) {
    var min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    if (min < 1) return 'hace un momento';
    if (min < 60) return 'hace ' + min + ' min';
    var h = Math.round(min / 60);
    if (h < 24) return 'hace ' + h + (h === 1 ? ' hora' : ' horas');
    return 'el ' + fechaCorta(iso);
  }

  function claveDia(iso) {
    var d = new Date(iso);
    var hoy = new Date();
    var ayer = new Date(); ayer.setDate(hoy.getDate() - 1);
    if (d.toDateString() === hoy.toDateString()) return 'Hoy';
    if (d.toDateString() === ayer.toDateString()) return 'Ayer';
    var texto = d.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' });
    return texto.charAt(0).toUpperCase() + texto.slice(1);
  }

  function capitalizar(texto) {
    return texto ? texto.charAt(0).toUpperCase() + texto.slice(1) : '';
  }

  // ── Resumen y vistas ───────────────────────────────────────
  function pintarResumen(r) {
    estado.resumen = r;
    var activo = r.buzon.activo;
    $('vista-onboarding').classList.toggle('cap-oculto', activo);
    $('vista-principal').classList.toggle('cap-oculto', !activo);
    $('cap-hero').classList.toggle('cap-oculto', !activo);

    var e = r.estadisticas;
    $('hero-pendientes').textContent = e.pendientes;
    $('hero-egresos').textContent = e.egresos_pendientes;
    $('hero-ingresos').textContent = e.ingresos_pendientes;
    $('hero-confirmados').textContent = e.confirmados_mes;
    $('hero-reglas').textContent = e.reglas;
    $('tab-contador').textContent = e.pendientes;

    var badge = 'Sin activar';
    if (activo) badge = r.pasos.primera_alerta ? 'Captura activa' : 'Esperando tu primera alerta';
    $('hero-estado').textContent = badge;

    if (!activo) return;

    $('buzon-direccion').textContent = r.buzon.direccion;
    var mostrarCodigo = !!r.buzon.codigo_reenvio_gmail && !r.pasos.primera_alerta;
    $('buzon-codigo').classList.toggle('cap-oculto', !mostrarCodigo);
    $('buzon-codigo-valor').textContent = r.buzon.codigo_reenvio_gmail || '';

    $('vista-principal').classList.toggle('cap-layout--configurando', !r.pasos.primera_alerta);
    $('paso-direccion').classList.toggle('hecho', r.pasos.direccion);
    $('paso-reenvio').classList.toggle('hecho', r.pasos.reenvio_gmail);
    $('paso-alerta').classList.toggle('hecho', r.pasos.primera_alerta);
    $('paso-alerta-detalle').textContent = r.buzon.ultimo_correo_en
      ? 'Último correo ' + haceCuanto(r.buzon.ultimo_correo_en) + '.'
      : 'Esperando un correo de tu banco.';

    var bancos = $('lista-bancos');
    bancos.innerHTML = '';
    r.bancos.forEach(function (nombre, i) {
      var chip = el('span', 'cap-banco' + (i === 0 ? ' cap-banco--destacado' : ''), nombre);
      chip.title = i === 0 ? 'Lectura exacta con reglas' : 'Lectura con IA; revisa los datos antes de confirmar';
      bancos.appendChild(chip);
    });

    // Mientras falte configuracion, revisar cada 10 s si llego el codigo o la primera alerta.
    var completo = r.pasos.primera_alerta;
    if (!completo && !estado.sondeo) {
      estado.sondeo = setInterval(cargarResumen, 10000);
    } else if (completo && estado.sondeo) {
      clearInterval(estado.sondeo);
      estado.sondeo = null;
    }
  }

  function cargarResumen() {
    return pedir(URL.resumen).then(pintarResumen);
  }

  // ── Pendientes ─────────────────────────────────────────────
  function categoriaDe(d) {
    return estado.categoriaElegida[d.id] || d.categoria_sugerida;
  }

  function crearItem(d, modo) {
    var nodo = $('tpl-detectado').content.firstElementChild.cloneNode(true);
    var esIngreso = d.tipo === 'INGRESO';
    nodo.dataset.id = d.id;
    if (esIngreso) nodo.classList.add('cap-item--ingreso');

    var ic = nodo.querySelector('.cap-item__icono');
    ic.innerHTML = '';
    ic.appendChild(icono(ICONO_OPERACION[d.operacion] || 'circle-dollar-sign'));

    nodo.querySelector('.cap-item__comercio').textContent = d.comercio;
    nodo.querySelector('.cap-item__monto').textContent = (esIngreso ? '+' : '-') + d.monto_formateado;

    var meta = [capitalizar(d.operacion), d.banco];
    if (d.producto) meta.push(d.producto);
    meta.push(modo === 'historial' ? fechaCorta(d.fecha_transaccion) + ', ' + hora(d.fecha_transaccion) : hora(d.fecha_transaccion));
    nodo.querySelector('.cap-item__meta').textContent = meta.join(' · ');

    var badges = nodo.querySelector('.cap-item__badges');
    if (modo === 'historial') {
      var conf = d.estado === 'CONFIRMADO';
      var b = el('span', 'cap-badge ' + (conf ? 'cap-badge--confirmado' : 'cap-badge--descartado'));
      b.appendChild(icono(conf ? 'check' : 'x'));
      b.appendChild(document.createTextNode(conf ? 'Registrado' : 'Descartado'));
      badges.appendChild(b);
    } else {
      if (d.dkim_valido) {
        var v = el('span', 'cap-badge cap-badge--verificado');
        v.appendChild(icono('shield-check'));
        v.appendChild(document.createTextNode('Verificado por el banco'));
        v.title = 'La firma digital del correo confirma que lo envió ' + d.banco;
        badges.appendChild(v);
      }
      if (d.leido_con_ia) {
        var ia = el('span', 'cap-badge cap-badge--ia');
        ia.appendChild(icono('sparkles'));
        ia.appendChild(document.createTextNode('Leído con IA, revisa los datos'));
        badges.appendChild(ia);
      }
    }

    var chip = nodo.querySelector('.cap-chip-categoria');
    var cat = categoriaDe(d);
    chip.querySelector('span').textContent = cat ? cat.nombre : 'Elegir categoría';

    if (modo === 'historial') {
      chip.classList.add('cap-chip-categoria--estatico');
      chip.disabled = true;
      chip.querySelectorAll('i')[1].remove();
      nodo.querySelector('.cap-item__botones').remove();
      nodo.querySelector('.cap-item__auto').remove();
      return nodo;
    }

    chip.addEventListener('click', function () { abrirSelector(d); });

    // Registrar solo los proximos: solo tiene efecto si el banco firma sus correos.
    if (d.dkim_valido) nodo.querySelector('.cap-item__auto').classList.remove('cap-oculto');

    nodo.querySelector('.cap-btn-confirmar').addEventListener('click', function () { confirmar(d, nodo); });
    nodo.querySelector('.cap-btn-descartar').addEventListener('click', function () { descartar(d, nodo); });
    return nodo;
  }

  function pintarAgrupado(contenedor, lista, modo) {
    contenedor.innerHTML = '';
    var grupos = [];
    var indice = {};
    lista.forEach(function (d) {
      var fecha = modo === 'historial' ? (d.resuelto_en || d.fecha_transaccion) : d.fecha_transaccion;
      var clave = claveDia(fecha);
      if (!(clave in indice)) {
        indice[clave] = grupos.length;
        grupos.push({ titulo: clave, items: [] });
      }
      grupos[indice[clave]].items.push(d);
    });

    grupos.forEach(function (g) {
      var grupo = el('section', 'cap-grupo');
      grupo.appendChild(el('h4', 'cap-grupo__titulo', g.titulo));
      var cont = el('div', 'cap-grupo__lista');
      g.items.forEach(function (d) { cont.appendChild(crearItem(d, modo)); });
      grupo.appendChild(cont);
      contenedor.appendChild(grupo);
    });
    iconos();
  }

  function pintarPendientes() {
    var hay = estado.pendientes.length > 0;
    pintarAgrupado($('lista-pendientes'), estado.pendientes, 'pendientes');
    $('vacio-pendientes').classList.toggle('cap-oculto', hay);
    $('barra-pendientes').classList.toggle('cap-oculto', !hay);
    var btnTodos = $('btn-confirmar-todos');
    btnTodos.classList.toggle('cap-oculto', estado.pendientes.length < 2);
    btnTodos.lastChild.textContent = ' Confirmar todos (' + estado.pendientes.length + ')';
  }

  function cargarPendientes() {
    return pedir(URL.detectados).then(function (data) {
      estado.pendientes = data.detectados;
      pintarPendientes();
    });
  }

  function quitarConAnimacion(nodo, id) {
    nodo.classList.add('saliendo');
    setTimeout(function () {
      estado.pendientes = estado.pendientes.filter(function (d) { return d.id !== id; });
      delete estado.categoriaElegida[id];
      pintarPendientes();
      estado.cargado.historial = false;
      estado.cargado.reglas = false;
      cargarResumen();
    }, 220);
  }

  function confirmar(d, nodo) {
    var cat = categoriaDe(d);
    if (!cat) { abrirSelector(d); return; }
    var boton = nodo.querySelector('.cap-btn-confirmar');
    boton.disabled = true;
    var auto = nodo.querySelector('.cap-item__auto input');
    pedir(URL.baseDetectado + d.id + '/confirmar/', {
      method: 'POST',
      body: { categoria_id: cat.id, auto_confirmar: auto && auto.checked ? true : null },
    }).then(function (r) {
      quitarConAnimacion(nodo, d.id);
      if (r.advertencia) aviso('info', r.advertencia);
      else aviso('ok', (d.tipo === 'INGRESO' ? 'Ingreso' : 'Egreso') + ' registrado en ' + cat.nombre);
    }).catch(function (e) {
      boton.disabled = false;
      aviso('error', e.message);
    });
  }

  function descartar(d, nodo) {
    pedir(URL.baseDetectado + d.id + '/descartar/', { method: 'POST' })
      .then(function () {
        quitarConAnimacion(nodo, d.id);
        aviso('ok', 'Movimiento descartado');
      })
      .catch(function (e) { aviso('error', e.message); });
  }

  $('btn-confirmar-todos').addEventListener('click', function () {
    var lista = estado.pendientes.slice();
    var sinCategoria = lista.filter(function (d) { return !categoriaDe(d); });
    if (sinCategoria.length) {
      aviso('error', 'Hay movimientos sin categoría. Elígela antes de confirmar todos.');
      return;
    }
    var pregunta = window.GastuAlerts
      ? window.GastuAlerts.confirmar('Confirmar ' + lista.length + ' movimientos',
          'Se registrarán con la categoría que ves en cada uno.', 'Sí, registrar')
      : Promise.resolve(true);
    pregunta.then(function (ok) {
      if (!ok) return;
      // Los que tienen categoria cambiada se confirman uno a uno con su eleccion.
      var cambiados = lista.filter(function (d) { return estado.categoriaElegida[d.id]; });
      var resto = lista.filter(function (d) { return !estado.categoriaElegida[d.id]; });
      var peticiones = cambiados.map(function (d) {
        return pedir(URL.baseDetectado + d.id + '/confirmar/', {
          method: 'POST', body: { categoria_id: estado.categoriaElegida[d.id].id },
        });
      });
      if (resto.length) {
        peticiones.push(pedir(URL.lote, { method: 'POST', body: { ids: resto.map(function (d) { return d.id; }) } }));
      }
      Promise.all(peticiones).then(function () {
        estado.categoriaElegida = {};
        estado.cargado.historial = false;
        estado.cargado.reglas = false;
        aviso('ok', lista.length + ' movimientos registrados');
        cargarPendientes();
        cargarResumen();
      }).catch(function (e) {
        aviso('error', e.message);
        cargarPendientes();
        cargarResumen();
      });
    });
  });

  // ── Selector de categoria ──────────────────────────────────
  var detectadoEnSelector = null;

  function abrirModal(id) {
    $(id).classList.remove('cap-oculto');
    document.body.style.overflow = 'hidden';
  }

  function cerrarModales() {
    document.querySelectorAll('.cap-modal').forEach(function (m) { m.classList.add('cap-oculto'); });
    document.body.style.overflow = '';
    detectadoEnSelector = null;
  }

  function abrirSelector(d) {
    if (!window.CategoryPicker) return;
    detectadoEnSelector = d;
    $('modal-categorias-titulo').textContent = d.tipo === 'INGRESO' ? 'Categoría del ingreso' : 'Categoría del egreso';
    $('buscador-categorias').value = '';
    window.CategoryPicker.init({
      containerId: 'picker-grid',
      context: 'captura',
      tipo: d.tipo,
      onSelect: function (cat) {
        if (!detectadoEnSelector) return;
        estado.categoriaElegida[detectadoEnSelector.id] = { id: cat.id, nombre: cat.nombre };
        cerrarModales();
        pintarPendientes();
      },
    });
    abrirModal('modal-categorias');
    setTimeout(function () { $('buscador-categorias').focus(); }, 50);
  }

  $('buscador-categorias').addEventListener('input', function (e) {
    if (window.CategoryPicker) window.CategoryPicker.filter(e.target.value);
  });

  document.querySelectorAll('.cap-modal').forEach(function (modal) {
    modal.addEventListener('click', function (e) {
      if (e.target === modal || e.target.closest('[data-cerrar-modal]')) cerrarModales();
    });
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') cerrarModales(); });

  // ── Historial ──────────────────────────────────────────────
  function cargarHistorial() {
    return pedir(URL.detectados + '?estado=HISTORIAL&limite=60').then(function (data) {
      estado.cargado.historial = true;
      pintarAgrupado($('lista-historial'), data.detectados, 'historial');
      $('vacio-historial').classList.toggle('cap-oculto', data.detectados.length > 0);
    });
  }

  // ── Reglas ─────────────────────────────────────────────────
  function crearRegla(r) {
    var fila = el('div', 'cap-regla');
    var ic = el('div', 'cap-item__icono');
    ic.style.width = '2.2rem';
    ic.style.height = '2.2rem';
    if (r.tipo === 'INGRESO') fila.classList.add('cap-item--ingreso');
    ic.appendChild(icono('store'));
    fila.appendChild(ic);

    var cuerpo = el('div', 'cap-regla__cuerpo');
    cuerpo.appendChild(el('p', 'cap-regla__comercio', r.comercio.replace(/ cta(\d{4})/, ' *$1')));
    var veces = r.veces_usada === 1 ? '1 vez' : r.veces_usada + ' veces';
    cuerpo.appendChild(el('p', 'cap-regla__meta', r.categoria.nombre + ' · confirmado ' + veces));
    fila.appendChild(cuerpo);

    var sw = el('label', 'cap-switch');
    var input = document.createElement('input');
    input.type = 'checkbox';
    input.checked = r.auto_confirmar;
    sw.appendChild(input);
    sw.appendChild(el('span', 'cap-switch__pista'));
    sw.appendChild(document.createTextNode('Automático'));
    sw.title = 'Registrar sin preguntar los próximos movimientos de este comercio (solo si el banco firma el correo)';
    input.addEventListener('change', function () {
      pedir(URL.baseRegla + r.id + '/actualizar/', { method: 'POST', body: { auto_confirmar: input.checked } })
        .then(function () {
          aviso('ok', input.checked ? 'Los próximos se registrarán solos' : 'Te preguntaremos antes de registrar');
        })
        .catch(function (e) { input.checked = !input.checked; aviso('error', e.message); });
    });
    fila.appendChild(sw);

    var borrar = el('button', 'cap-btn-icono cap-btn-descartar');
    borrar.type = 'button';
    borrar.title = 'Olvidar esta regla';
    borrar.appendChild(icono('trash-2'));
    borrar.addEventListener('click', function () {
      pedir(URL.baseRegla + r.id + '/eliminar/', { method: 'POST' })
        .then(function () { fila.remove(); aviso('ok', 'Regla olvidada'); cargarResumen(); revisarReglasVacias(); })
        .catch(function (e) { aviso('error', e.message); });
    });
    fila.appendChild(borrar);
    return fila;
  }

  function revisarReglasVacias() {
    var vacio = $('lista-reglas').children.length === 0;
    $('vacio-reglas').classList.toggle('cap-oculto', !vacio);
  }

  function cargarReglas() {
    return pedir(URL.reglas).then(function (data) {
      estado.cargado.reglas = true;
      var lista = $('lista-reglas');
      lista.innerHTML = '';
      data.reglas.forEach(function (r) { lista.appendChild(crearRegla(r)); });
      revisarReglasVacias();
      iconos();
    });
  }

  // ── Tabs ───────────────────────────────────────────────────
  document.querySelectorAll('.cap-tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      var nombre = tab.dataset.tab;
      estado.tabActiva = nombre;
      document.querySelectorAll('.cap-tab').forEach(function (t) { t.classList.toggle('activo', t === tab); });
      document.querySelectorAll('.cap-panel').forEach(function (p) {
        p.classList.toggle('cap-oculto', p.dataset.panel !== nombre);
      });
      if (nombre === 'historial' && !estado.cargado.historial) cargarHistorial().catch(function (e) { aviso('error', e.message); });
      if (nombre === 'reglas' && !estado.cargado.reglas) cargarReglas().catch(function (e) { aviso('error', e.message); });
    });
  });

  // ── Buzon ──────────────────────────────────────────────────
  $('btn-activar').addEventListener('click', function () {
    pedir(URL.buzon, { method: 'POST' })
      .then(function () { return cargarResumen(); })
      .then(function () { aviso('ok', 'Captura automática activada'); abrirModal('modal-guia'); })
      .catch(function (e) { aviso('error', e.message); });
  });

  $('btn-copiar').addEventListener('click', function () {
    navigator.clipboard.writeText($('buzon-direccion').textContent)
      .then(function () { aviso('ok', 'Dirección copiada'); })
      .catch(function () { aviso('error', 'No se pudo copiar la dirección'); });
  });

  $('btn-guia').addEventListener('click', function () { abrirModal('modal-guia'); });

  $('btn-regenerar').addEventListener('click', function () {
    var pregunta = window.GastuAlerts
      ? window.GastuAlerts.confirmar('¿Cambiar tu dirección?',
          'La dirección actual dejará de recibir correos y tendrás que actualizar el filtro de reenvío en Gmail.',
          'Sí, cambiarla')
      : Promise.resolve(true);
    pregunta.then(function (ok) {
      if (!ok) return;
      pedir(URL.regenerar, { method: 'POST' })
        .then(function () { aviso('ok', 'Dirección actualizada. Recuerda cambiarla en Gmail.'); return cargarResumen(); })
        .catch(function (e) { aviso('error', e.message); });
    });
  });

  // ── Inicio ─────────────────────────────────────────────────
  cargarResumen()
    .then(function () {
      if (estado.resumen.buzon.activo) return cargarPendientes();
    })
    .then(function () {
      var params = new URLSearchParams(window.location.search);
      var tab = params.get('tab');
      if (tab) {
        var boton = document.querySelector('.cap-tab[data-tab="' + tab + '"]');
        if (boton) boton.click();
      }
    })
    .catch(function (e) { aviso('error', e.message); });
  iconos();

  // Confirmaciones hechas desde el panel de notificaciones.
  window.addEventListener('captura:cambio', function () {
    estado.cargado.historial = false;
    estado.cargado.reglas = false;
    cargarPendientes().catch(function () {});
    cargarResumen().catch(function () {});
  });

  // Refrescar la bandeja cada 30 s mientras la pagina esta visible.
  setInterval(function () {
    if (document.hidden || !estado.resumen || !estado.resumen.buzon.activo) return;
    if (document.querySelector('.cap-modal:not(.cap-oculto)')) return;
    cargarPendientes().catch(function () {});
    cargarResumen().catch(function () {});
  }, 30000);
})();

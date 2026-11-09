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
    prueba: app.dataset.urlPrueba,
    buzon: app.dataset.urlBuzon,
    regenerar: app.dataset.urlRegenerar,
    detectados: app.dataset.urlDetectados,
    lote: app.dataset.urlLote,
    reglas: app.dataset.urlReglas,
    baseDetectado: app.dataset.urlBaseDetectado,
    baseRegla: app.dataset.urlBaseRegla,
    reglaCrear: app.dataset.urlReglaCrear,
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
    direccion: '',
    direccionVisible: false,
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

    estado.direccion = r.buzon.direccion;
    pintarDireccion();
    var mostrarCodigo = !!r.buzon.codigo_reenvio_gmail && !r.pasos.primera_alerta;
    $('buzon-codigo').classList.toggle('cap-oculto', !mostrarCodigo);
    $('buzon-codigo-valor').textContent = r.buzon.codigo_reenvio_gmail || '';

    $('vista-principal').classList.toggle('cap-layout--configurando', !r.pasos.primera_alerta);
    $('paso-direccion').classList.toggle('hecho', r.pasos.direccion);
    $('paso-reenvio').classList.toggle('hecho', r.pasos.reenvio_gmail);
    $('paso-alerta').classList.toggle('hecho', r.pasos.primera_alerta);
    var pruebaOk = r.prueba && r.prueba.estado === 'RECIBIDA';
    $('paso-prueba').classList.toggle('hecho', pruebaOk);
    $('paso-prueba-detalle').textContent = pruebaOk
      ? 'Recibimos tu correo de prueba ' + haceCuanto(r.prueba.recibida_en) + '.'
      : 'Envíate un correo de prueba.';
    $('paso-filtro').classList.toggle('hecho', r.pasos.reenvio_automatico);
    $('paso-filtro-detalle').textContent = r.pasos.reenvio_automatico
      ? 'Gmail está reenviando las alertas solo.'
      : 'Se confirma cuando Gmail reenvíe una alerta por su cuenta.';
    $('paso-alerta-detalle').textContent = r.buzon.ultimo_correo_en
      ? 'Último correo ' + haceCuanto(r.buzon.ultimo_correo_en) + '.'
      : 'Esperando un correo de tu banco.';

    pintarBancos(r.bancos);
    actualizarGuia();

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

  // ── Bancos compatibles ─────────────────────────────────────
  function iniciales(nombre) {
    var palabras = nombre.replace(/^Banco (de )?/i, '').split(/\s+/).filter(Boolean);
    var txt = palabras.length > 1 ? palabras[0][0] + palabras[1][0] : palabras[0].slice(0, 2);
    return txt.toUpperCase();
  }

  function tonoDe(nombre) {
    var h = 0;
    for (var i = 0; i < nombre.length; i++) h = (h * 31 + nombre.charCodeAt(i)) % 360;
    return h;
  }

  function avatarBanco(nombre, grande) {
    var a = el('span', 'cap-banco-avatar' + (grande ? ' cap-banco-avatar--grande' : ''), iniciales(nombre));
    if (!grande) a.style.setProperty('--tono', tonoDe(nombre));
    a.setAttribute('aria-hidden', 'true');
    return a;
  }

  function pintarBancos(bancos) {
    var exactos = $('bancos-exactos');
    var conIa = $('bancos-ia');
    exactos.innerHTML = '';
    conIa.innerHTML = '';
    bancos.forEach(function (b) {
      if (b.lectura === 'EXACTA') {
        var fila = el('div', 'cap-banco-destacado');
        fila.appendChild(avatarBanco(b.nombre, true));
        var info = el('div', 'cap-banco-destacado__info');
        info.appendChild(el('p', 'cap-banco-destacado__nombre', b.nombre));
        var det = el('p', 'cap-banco-destacado__detalle');
        det.appendChild(icono('shield-check'));
        det.appendChild(document.createTextNode('Lectura exacta y firma verificada'));
        info.appendChild(det);
        fila.appendChild(info);
        exactos.appendChild(fila);
      } else {
        var ficha = el('div', 'cap-banco-ficha');
        ficha.title = b.nombre + ': lectura con IA';
        ficha.appendChild(avatarBanco(b.nombre, false));
        ficha.appendChild(el('span', 'cap-banco-ficha__nombre', b.nombre));
        conIa.appendChild(ficha);
      }
    });
    iconos();
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

    nodo.querySelector('.cap-item__comercio').textContent = d.apodo || d.comercio;
    nodo.querySelector('.cap-item__monto').textContent = (esIngreso ? '+' : '-') + d.monto_formateado;

    var meta = d.apodo ? [d.comercio, d.banco] : [capitalizar(d.operacion), d.banco];
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
  var pilaModales = [];

  function abrirModal(id) {
    $(id).classList.remove('cap-oculto');
    if (pilaModales.indexOf(id) === -1) pilaModales.push(id);
    document.body.style.overflow = 'hidden';
  }

  function cerrarModal(id) {
    $(id).classList.add('cap-oculto');
    pilaModales = pilaModales.filter(function (m) { return m !== id; });
    if (!pilaModales.length) document.body.style.overflow = '';
    if (id === 'modal-guia') detenerSondeoGuia();
    if (id === 'modal-prueba') detenerPrueba();
  }

  function cerrarModales() {
    pilaModales.slice().forEach(cerrarModal);
  }

  /** Abre el selector visual de categorias del tipo dado y llama a alElegir({id, nombre}). */
  function elegirCategoria(tipo, alElegir) {
    if (!window.CategoryPicker) return;
    $('modal-categorias-titulo').textContent = tipo === 'INGRESO' ? 'Categoría del ingreso' : 'Categoría del egreso';
    $('buscador-categorias').value = '';
    window.CategoryPicker.init({
      containerId: 'picker-grid',
      context: 'captura',
      tipo: tipo,
      onSelect: function (cat) {
        cerrarModal('modal-categorias');
        alElegir({ id: cat.id, nombre: cat.nombre });
      },
    });
    abrirModal('modal-categorias');
    setTimeout(function () { $('buscador-categorias').focus(); }, 50);
  }

  function abrirSelector(d) {
    elegirCategoria(d.tipo, function (cat) {
      estado.categoriaElegida[d.id] = cat;
      pintarPendientes();
    });
  }

  $('buscador-categorias').addEventListener('input', function (e) {
    if (window.CategoryPicker) window.CategoryPicker.filter(e.target.value);
  });

  document.querySelectorAll('.cap-modal').forEach(function (modal) {
    modal.addEventListener('click', function (e) {
      if (e.target === modal || e.target.closest('[data-cerrar-modal]')) cerrarModal(modal.id);
    });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && pilaModales.length) cerrarModal(pilaModales[pilaModales.length - 1]);
  });

  // ── Historial ──────────────────────────────────────────────
  function cargarHistorial() {
    return pedir(URL.detectados + '?estado=HISTORIAL&limite=60').then(function (data) {
      estado.cargado.historial = true;
      pintarAgrupado($('lista-historial'), data.detectados, 'historial');
      $('vacio-historial').classList.toggle('cap-oculto', data.detectados.length > 0);
    });
  }

  // ── Reglas ─────────────────────────────────────────────────
  function inicialesRegla(r) {
    if (!r.apodo) return null;
    var p = r.apodo.trim().split(/\s+/);
    return (p.length > 1 ? p[0][0] + p[1][0] : p[0].slice(0, 2)).toUpperCase();
  }

  function actualizarRegla(r, cambios, mensaje) {
    return pedir(URL.baseRegla + r.id + '/actualizar/', { method: 'POST', body: cambios })
      .then(function (data) {
        if (mensaje) aviso('ok', mensaje);
        return data.regla;
      });
  }

  function crearRegla(r) {
    var fila = el('article', 'cap-regla' + (r.tipo === 'INGRESO' ? ' cap-regla--ingreso' : ''));

    var avatar = el('div', 'cap-regla__avatar');
    var ini = inicialesRegla(r);
    if (ini) avatar.textContent = ini;
    else avatar.appendChild(icono(/cuenta \*\d{4}/.test(r.comercio) ? 'arrow-left-right' : 'store'));
    fila.appendChild(avatar);

    var cuerpo = el('div', 'cap-regla__cuerpo');
    cuerpo.appendChild(el('p', 'cap-regla__nombre', r.nombre_visible));
    cuerpo.appendChild(el('p', 'cap-regla__origen', r.apodo ? r.comercio : (r.tipo === 'INGRESO' ? 'Ingreso' : 'Egreso') + ' · usa el lápiz para ponerle un nombre'));

    var linea = el('div', 'cap-regla__linea');
    var flecha = el('span', 'cap-regla__flecha');
    flecha.appendChild(icono('corner-down-right'));
    linea.appendChild(flecha);
    var chip = el('button', 'cap-chip-categoria');
    chip.type = 'button';
    chip.title = 'Cambiar categoría';
    chip.appendChild(icono('tag'));
    chip.appendChild(el('span', '', r.categoria.nombre));
    chip.appendChild(icono('chevron-down'));
    chip.addEventListener('click', function () {
      elegirCategoria(r.tipo, function (cat) {
        actualizarRegla(r, { categoria_id: cat.id }, 'Categoría actualizada')
          .then(function (nueva) { fila.replaceWith(crearRegla(nueva)); iconos(); })
          .catch(function (e) { aviso('error', e.message); });
      });
    });
    linea.appendChild(chip);
    var veces = r.veces_usada === 1 ? '1 vez' : r.veces_usada + ' veces';
    linea.appendChild(el('span', 'cap-regla__veces', r.veces_usada ? 'Confirmado ' + veces : 'Precargada'));
    cuerpo.appendChild(linea);
    fila.appendChild(cuerpo);

    var acciones = el('div', 'cap-regla__acciones');
    var sw = el('label', 'cap-switch');
    var input = document.createElement('input');
    input.type = 'checkbox';
    input.checked = r.auto_confirmar;
    sw.appendChild(input);
    sw.appendChild(el('span', 'cap-switch__pista'));
    sw.appendChild(document.createTextNode('Automático'));
    sw.title = 'Registrar sin preguntar los próximos (solo si el banco firma el correo)';
    input.addEventListener('change', function () {
      actualizarRegla(r, { auto_confirmar: input.checked },
        input.checked ? 'Los próximos se registrarán solos' : 'Te preguntaremos antes de registrar')
        .then(function (nueva) { r = nueva; })
        .catch(function (e) { input.checked = !input.checked; aviso('error', e.message); });
    });
    acciones.appendChild(sw);

    var editar = el('button', 'cap-btn-icono cap-btn-editar');
    editar.type = 'button';
    editar.title = 'Editar nombre';
    editar.appendChild(icono('pencil'));
    editar.addEventListener('click', function () { abrirFormRegla(r); });
    acciones.appendChild(editar);

    var borrar = el('button', 'cap-btn-icono cap-btn-descartar');
    borrar.type = 'button';
    borrar.title = 'Eliminar regla';
    borrar.appendChild(icono('trash-2'));
    borrar.addEventListener('click', function () {
      var pregunta = window.GastuAlerts
        ? window.GastuAlerts.confirmar('¿Eliminar esta regla?',
            'Gastu olvidará la categoría de ' + r.nombre_visible + '. Los movimientos ya registrados no cambian.', 'Sí, eliminar')
        : Promise.resolve(true);
      pregunta.then(function (ok) {
        if (!ok) return;
        pedir(URL.baseRegla + r.id + '/eliminar/', { method: 'POST' })
          .then(function () { fila.remove(); aviso('ok', 'Regla eliminada'); cargarResumen(); revisarReglasVacias(); })
          .catch(function (e) { aviso('error', e.message); });
      });
    });
    acciones.appendChild(borrar);
    fila.appendChild(acciones);
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

  // ── Formulario de regla (nueva o editar) ───────────────────
  var formRegla = { editando: null, tipo: 'EGRESO', categoria: null };

  function nombreDesdeEntrada(texto, tipo) {
    var limpio = (texto || '').trim();
    var m = limpio.match(/^\*?\s*(\d{4,})$/);
    if (m) {
      var ult = m[1].slice(-4);
      return (tipo === 'EGRESO' ? 'Transferencia a cuenta *' : 'Transferencia de cuenta *') + ult;
    }
    return limpio;
  }

  function pintarTipoRegla() {
    $('regla-tipo').querySelectorAll('button').forEach(function (b) {
      var activo = b.dataset.tipo === formRegla.tipo;
      b.classList.toggle('activo', activo);
      b.setAttribute('aria-checked', activo ? 'true' : 'false');
    });
  }

  function pintarCategoriaRegla() {
    $('regla-categoria').querySelector('span').textContent = formRegla.categoria ? formRegla.categoria.nombre : 'Elegir categoría';
  }

  function pintarVistaPrevia() {
    var caja = $('regla-vista-previa');
    caja.innerHTML = '';
    var nombre = formRegla.editando ? formRegla.editando.comercio : nombreDesdeEntrada($('regla-comercio').value, formRegla.tipo);
    if (!nombre || !formRegla.categoria) return;
    var apodo = $('regla-apodo').value.trim();
    caja.appendChild(icono('wand-2'));
    caja.appendChild(document.createTextNode('Cuando llegue '));
    caja.appendChild(el('strong', '', nombre));
    caja.appendChild(document.createTextNode(apodo ? ' (' + apodo + ')' : ''));
    caja.appendChild(document.createTextNode(' se registrará en '));
    caja.appendChild(el('strong', '', formRegla.categoria.nombre));
    caja.appendChild(document.createTextNode($('regla-auto').checked ? ', sin preguntarte.' : ', para que lo confirmes.'));
    iconos();
  }

  function abrirFormRegla(regla) {
    formRegla.editando = regla || null;
    formRegla.tipo = regla ? regla.tipo : 'EGRESO';
    formRegla.categoria = regla ? { id: regla.categoria.id, nombre: regla.categoria.nombre } : null;
    $('modal-regla-titulo').textContent = regla ? 'Editar regla' : 'Nueva regla';
    $('regla-intro').textContent = regla
      ? 'Ponle un nombre fácil de reconocer y elige cómo debe registrarse.'
      : 'Prepara cómo debe registrarse un comercio o una cuenta antes de que llegue su alerta.';
    $('regla-campo-comercio').classList.toggle('cap-oculto', !!regla);
    $('regla-tipo').classList.toggle('bloqueado', !!regla);
    $('regla-comercio').value = '';
    $('regla-apodo').value = regla ? regla.apodo : '';
    $('regla-auto').checked = regla ? regla.auto_confirmar : false;
    pintarTipoRegla();
    pintarCategoriaRegla();
    pintarVistaPrevia();
    abrirModal('modal-regla');
    setTimeout(function () { (regla ? $('regla-apodo') : $('regla-comercio')).focus(); }, 50);
  }

  $('btn-nueva-regla').addEventListener('click', function () { abrirFormRegla(null); });

  $('regla-tipo').querySelectorAll('button').forEach(function (b) {
    b.addEventListener('click', function () {
      if (formRegla.editando || formRegla.tipo === b.dataset.tipo) return;
      formRegla.tipo = b.dataset.tipo;
      formRegla.categoria = null;
      pintarTipoRegla();
      pintarCategoriaRegla();
      pintarVistaPrevia();
    });
  });

  $('regla-categoria').addEventListener('click', function () {
    elegirCategoria(formRegla.tipo, function (cat) {
      formRegla.categoria = cat;
      pintarCategoriaRegla();
      pintarVistaPrevia();
    });
  });

  ['regla-comercio', 'regla-apodo'].forEach(function (id) { $(id).addEventListener('input', pintarVistaPrevia); });
  $('regla-auto').addEventListener('change', pintarVistaPrevia);

  $('form-regla').addEventListener('submit', function (e) {
    e.preventDefault();
    if (!formRegla.categoria) { aviso('error', 'Elige una categoría.'); return; }
    var boton = $('regla-guardar');
    boton.disabled = true;
    var cuerpo = {
      apodo: $('regla-apodo').value.trim(),
      categoria_id: formRegla.categoria.id,
      auto_confirmar: $('regla-auto').checked,
    };
    var promesa;
    if (formRegla.editando) {
      promesa = actualizarRegla(formRegla.editando, cuerpo, 'Regla actualizada');
    } else {
      var comercio = $('regla-comercio').value.trim();
      if (!comercio) { boton.disabled = false; aviso('error', 'Escribe el comercio o la cuenta.'); return; }
      cuerpo.comercio = comercio;
      cuerpo.tipo = formRegla.tipo;
      promesa = pedir(URL.reglaCrear, { method: 'POST', body: cuerpo }).then(function (d) { aviso('ok', 'Regla guardada'); return d.regla; });
    }
    promesa.then(function () {
      cerrarModal('modal-regla');
      cargarReglas();
      cargarResumen();
      cargarPendientes().catch(function () {});
    }).catch(function (err) {
      aviso('error', err.message);
    }).then(function () { boton.disabled = false; });
  });

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
      .then(function () { aviso('ok', 'Captura automática activada'); abrirGuia(); })
      .catch(function (e) { aviso('error', e.message); });
  });

  // La direccion se muestra oculta (el alias es lo que la hace privada); el dominio si se ve.
  function pintarDireccion() {
    var partes = estado.direccion.split('@');
    var texto = estado.direccionVisible ? estado.direccion : '•'.repeat(10) + '@' + (partes[1] || '');
    var nodo = $('buzon-direccion');
    nodo.textContent = texto;
    nodo.classList.toggle('cap-direccion__texto--oculta', !estado.direccionVisible);
    var btn = $('btn-revelar');
    btn.setAttribute('aria-pressed', estado.direccionVisible ? 'true' : 'false');
    btn.title = estado.direccionVisible ? 'Ocultar dirección' : 'Mostrar dirección';
    btn.innerHTML = '';
    btn.appendChild(icono(estado.direccionVisible ? 'eye-off' : 'eye'));
    iconos();
  }

  var temporizadorOcultar = null;
  $('btn-revelar').addEventListener('click', function () {
    estado.direccionVisible = !estado.direccionVisible;
    pintarDireccion();
    // Se vuelve a ocultar sola despues de 20 s.
    clearTimeout(temporizadorOcultar);
    if (estado.direccionVisible) {
      temporizadorOcultar = setTimeout(function () { estado.direccionVisible = false; pintarDireccion(); }, 20000);
    }
  });

  $('btn-copiar').addEventListener('click', function () {
    navigator.clipboard.writeText(estado.direccion)
      .then(function () { aviso('ok', 'Dirección copiada'); })
      .catch(function () { aviso('error', 'No se pudo copiar la dirección'); });
  });

  $('btn-guia').addEventListener('click', function () { abrirGuia(); });

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

  // ── Asistente de configuracion ─────────────────────────────
  var guia = { paso: 0, total: 5, sondeo: null };

  function pasoSugerido() {
    var r = estado.resumen;
    if (!r || !r.buzon.activo) return 0;
    if (r.pasos.primera_alerta) return 4;
    if (r.buzon.codigo_reenvio_gmail) return 2;
    return 0;
  }

  function irPaso(n) {
    guia.paso = Math.max(0, Math.min(guia.total - 1, n));
    document.querySelectorAll('.cap-asistente__paso').forEach(function (p) {
      p.classList.toggle('cap-oculto', Number(p.dataset.paso) !== guia.paso);
    });
    document.querySelectorAll('.cap-asistente__puntos button').forEach(function (b) {
      var i = Number(b.dataset.irPaso);
      b.classList.toggle('activo', i === guia.paso);
      b.classList.toggle('hecho', i < guia.paso);
    });
    $('guia-paso-texto').textContent = 'Paso ' + (guia.paso + 1) + ' de ' + guia.total;
    $('guia-progreso').style.width = ((guia.paso + 1) / guia.total * 100) + '%';
    $('guia-atras').style.visibility = guia.paso === 0 ? 'hidden' : 'visible';
    $('guia-siguiente').querySelector('span').textContent = guia.paso === guia.total - 1 ? 'Ir a Por revisar' : 'Siguiente';
    actualizarGuia();
  }

  function actualizarGuia() {
    var r = estado.resumen;
    if (!r || !r.buzon.activo) return;
    var partes = r.buzon.direccion.split('@');
    $('guia-direccion-mock').textContent = '•'.repeat(8) + '@' + (partes[1] || '');

    var codigo = r.buzon.codigo_reenvio_gmail;
    $('guia-codigo-espera').classList.toggle('cap-oculto', !!codigo);
    $('guia-codigo-listo').classList.toggle('cap-oculto', !codigo);
    $('guia-codigo-valor').textContent = codigo || '';
    $('guia-copiar-codigo').classList.toggle('cap-oculto', !codigo);

    var conectado = r.pasos.primera_alerta;
    $('guia-final-espera').classList.toggle('cap-oculto', conectado);
    $('guia-final-listo').classList.toggle('cap-oculto', !conectado);
  }

  function detenerSondeoGuia() {
    if (guia.sondeo) { clearInterval(guia.sondeo); guia.sondeo = null; }
  }

  function abrirGuia() {
    irPaso(pasoSugerido());
    abrirModal('modal-guia');
    // Con la guia abierta se revisa cada 5 s si llego el codigo de Gmail o la primera alerta.
    detenerSondeoGuia();
    guia.sondeo = setInterval(function () { cargarResumen().catch(function () {}); }, 5000);
  }

  function copiar(texto, mensaje) {
    navigator.clipboard.writeText(texto)
      .then(function () { aviso('ok', mensaje); })
      .catch(function () { aviso('error', 'No se pudo copiar'); });
  }

  $('guia-atras').addEventListener('click', function () { irPaso(guia.paso - 1); });
  $('guia-siguiente').addEventListener('click', function () {
    if (guia.paso === guia.total - 1) {
      cerrarModal('modal-guia');
      var tab = document.querySelector('.cap-tab[data-tab="pendientes"]');
      if (tab) tab.click();
      return;
    }
    irPaso(guia.paso + 1);
  });
  document.querySelectorAll('.cap-asistente__puntos button').forEach(function (b) {
    b.addEventListener('click', function () { irPaso(Number(b.dataset.irPaso)); });
  });
  document.querySelectorAll('[data-copiar-direccion]').forEach(function (b) {
    b.addEventListener('click', function () { copiar(estado.direccion, 'Dirección copiada'); });
  });
  document.querySelectorAll('[data-copiar]').forEach(function (b) {
    b.addEventListener('click', function () { copiar(b.dataset.copiar, 'Remitente copiado'); });
  });
  $('guia-copiar-codigo').addEventListener('click', function () {
    copiar(estado.resumen.buzon.codigo_reenvio_gmail, 'Código copiado');
  });

  // ── Prueba de conexion ─────────────────────────────────────
  var prueba = { sondeo: null, reloj: null, inicio: null, datos: null };

  function detenerPrueba() {
    clearInterval(prueba.sondeo);
    clearInterval(prueba.reloj);
    prueba.sondeo = null;
    prueba.reloj = null;
  }

  function mostrarVistaPrueba(nombre) {
    ['esperando', 'recibida', 'vencida'].forEach(function (v) {
      $('prueba-' + v).classList.toggle('cap-oculto', v !== nombre);
    });
  }

  function pintarPrueba(p, direccion) {
    prueba.datos = p;
    if (p.estado === 'RECIBIDA') {
      detenerPrueba();
      mostrarVistaPrueba('recibida');
      var seg = p.segundos;
      var tardo = seg < 60 ? seg + ' s' : Math.round(seg / 60) + ' min';
      $('prueba-detalle').textContent = 'Llegó en ' + tardo + ' desde ' + (p.remitente || 'tu correo') + '. Tu dirección de captura recibe correos.';
      var filtroOk = estado.resumen && estado.resumen.pasos.reenvio_automatico;
      var caja = $('prueba-filtro');
      caja.innerHTML = '';
      caja.className = 'cap-prueba__filtro' + (filtroOk ? ' cap-prueba__filtro--ok' : '');
      caja.appendChild(icono(filtroOk ? 'check-circle-2' : 'info'));
      caja.appendChild(el('span', '', filtroOk
        ? 'El filtro de Gmail también está funcionando: ya recibimos alertas reenviadas automáticamente.'
        : 'Falta comprobar el filtro del banco. Se confirmará solo con la primera alerta que Gmail reenvíe por su cuenta.'));
      iconos();
      cargarResumen().catch(function () {});
      return;
    }
    if (p.estado === 'VENCIDA') {
      detenerPrueba();
      mostrarVistaPrueba('vencida');
      return;
    }
    mostrarVistaPrueba('esperando');
    $('prueba-codigo').textContent = p.codigo;
    var partes = (direccion || estado.direccion).split('@');
    $('prueba-direccion').textContent = '•'.repeat(8) + '@' + (partes[1] || '');
    // mailto: lo abre la app de correo del propio equipo; no pasa por ningun servidor.
    $('prueba-mailto').href = 'mailto:' + (direccion || estado.direccion)
      + '?subject=' + encodeURIComponent(p.codigo)
      + '&body=' + encodeURIComponent('Prueba de conexión de Gastu.');
  }

  function consultarPrueba() {
    return pedir(URL.prueba).then(function (d) { pintarPrueba(d.prueba, d.direccion); });
  }

  function iniciarPrueba() {
    detenerPrueba();
    $('prueba-ayuda').classList.add('cap-oculto');
    mostrarVistaPrueba('esperando');
    $('prueba-codigo').textContent = '...';
    return pedir(URL.prueba, { method: 'POST' }).then(function (d) {
      pintarPrueba(d.prueba, d.direccion);
      prueba.inicio = Date.now();
      prueba.reloj = setInterval(function () {
        var s = Math.floor((Date.now() - prueba.inicio) / 1000);
        $('prueba-tiempo').textContent = Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
        if (s === 120) $('prueba-ayuda').classList.remove('cap-oculto');
      }, 1000);
      prueba.sondeo = setInterval(function () { consultarPrueba().catch(function () {}); }, 3000);
    });
  }

  function abrirPrueba() {
    cerrarModal('modal-guia');
    abrirModal('modal-prueba');
    iniciarPrueba().catch(function (e) { aviso('error', e.message); });
  }

  $('btn-probar').addEventListener('click', abrirPrueba);
  document.querySelectorAll('[data-abrir-prueba]').forEach(function (b) { b.addEventListener('click', abrirPrueba); });
  $('prueba-reintentar').addEventListener('click', function () {
    iniciarPrueba().catch(function (e) { aviso('error', e.message); });
  });
  $('prueba-copiar-codigo').addEventListener('click', function () {
    if (prueba.datos && prueba.datos.codigo) copiar(prueba.datos.codigo, 'Código copiado');
  });

  // Aviso en vivo: si llega la prueba por WebSocket, se consulta de inmediato.
  window.addEventListener('gastu:notificacion', function (e) {
    if (e.detail && e.detail.tipo === 'PRUEBA_CONEXION' && prueba.sondeo) consultarPrueba().catch(function () {});
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

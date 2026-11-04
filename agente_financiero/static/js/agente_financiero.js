/**
 * agente_financiero.js
 */

(function () {
  "use strict";

  const chatContainer     = document.getElementById("agenteChat");
  const form              = document.getElementById("agenteForm");
  const input             = document.getElementById("agenteInput");
  const btnEnviar         = document.getElementById("agenteBtnEnviar");
  const typingIndicator   = document.getElementById("agenteTyping");
  const btnLimpiar        = document.getElementById("btnLimpiarChat");
  const mensajeBienvenida = document.getElementById("mensajeBienvenida");

  const INICIAL = window.GASTU_USER_INICIAL || "U";
  let esperandoRespuesta = false;

  function getCsrfToken() {
    const cookie = document.cookie.split("; ").find(r => r.startsWith("csrftoken="));
    return cookie ? cookie.split("=")[1] : "";
  }

  function escaparHTML(texto) {
    return texto
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
  }

  function formatearBot(texto) {
    var seguro = escaparHTML(texto || "");
    return seguro
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br>");
  }

  function horaActual() {
    return new Date().toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" });
  }

  function logoSrc() {
    return document.querySelector(".agente-avatar__img")?.src || "";
  }

  
  // ── Renderizado de Tarjeta Interactiva de Confirmacion (Firewall) ───
  function renderizarTarjetaConfirmacion(datos) {
    var cardId = 'card_confirm_' + Date.now();
    var div = document.createElement('div');
    div.id = cardId;
    div.className = 'agente-card-confirmacion mt-3 p-3 bg-red-50/80 dark:bg-rose-950/30 border border-red-200 dark:border-rose-900 rounded-xl text-sm shadow-sm';
    
    var endpoint = (datos.endpoint || "").trim();
    // Validacion de seguridad: whitelist de rutas internas permitidas
    if (!endpoint.startsWith('/movimientos/api/') && !endpoint.startsWith('/api/presupuestos/')) {
      console.warn("[GASTU Firewall] Endpoint de confirmacion denegado por seguridad:", endpoint);
      return div;
    }

    var metodo = (datos.metodo || "POST").toUpperCase();
    if (metodo !== "POST" && metodo !== "DELETE") {
      metodo = "POST";
    }

    var resumen = escaparHTML(datos.resumen_accion || 'Se requiere tu autorizacion para proceder.');
    var payloadStr = escaparHTML(JSON.stringify(datos.detalles_modificacion || {}));

    div.innerHTML = '<div class="flex items-start gap-2.5">' +
      '<div class="w-7 h-7 rounded-lg bg-red-100 dark:bg-red-900/60 flex items-center justify-center shrink-0 text-red-600 dark:text-red-400 font-bold">&#9888;</div>' +
      '<div class="flex-1">' +
        '<p class="font-semibold text-slate-900 dark:text-slate-100 mb-1">Confirmacion de Seguridad Requerida</p>' +
        '<p class="text-slate-600 dark:text-slate-300 text-xs mb-3">' + resumen + '</p>' +
        '<div class="flex items-center gap-2">' +
          '<button type="button" class="btn-confirmar-accion px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow transition-colors flex items-center gap-1.5" data-endpoint="' + escaparHTML(endpoint) + '" data-metodo="' + metodo + '" data-payload="' + payloadStr + '">Confirmar Accion</button>' +
          '<button type="button" class="btn-cancelar-accion px-3 py-1.5 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 text-slate-700 dark:text-slate-300 rounded-lg text-xs font-medium transition-colors">Cancelar</button>' +
        '</div>' +
      '</div>' +
    '</div>';

    var btnConfirmar = div.querySelector('.btn-confirmar-accion');
    var btnCancelar = div.querySelector('.btn-cancelar-accion');

    btnConfirmar.addEventListener('click', async function() {
      btnConfirmar.disabled = true;
      btnCancelar.disabled = true;
      btnConfirmar.innerText = 'Procesando...';

      try {
        var metodoHTTP = btnConfirmar.dataset.metodo || 'POST';
        var reqOptions = {
          method: metodoHTTP,
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          }
        };
        if (metodoHTTP !== 'DELETE') {
          var payloadData = {};
          try { payloadData = JSON.parse(btnConfirmar.dataset.payload || '{}'); } catch(e){}
          reqOptions.body = JSON.stringify(payloadData);
        }

        var res = await fetch(btnConfirmar.dataset.endpoint, reqOptions);

        if (res.ok) {
          div.innerHTML = '<div class="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-medium text-xs"><span>&#10003;</span> Accion confirmada y ejecutada exitosamente.</div>';
          if (window.GastuAlerts && window.GastuAlerts.success) {
            window.GastuAlerts.success('Operacion ejecutada exitosamente');
          }
        } else {
          div.innerHTML = '<p class="text-xs text-red-600 font-medium">No se pudo completar la operacion (Error en el servidor).</p>';
        }
      } catch (err) {
        div.innerHTML = '<p class="text-xs text-red-600 font-medium">Error de conexion al procesar la confirmacion.</p>';
      }
    });

    btnCancelar.addEventListener('click', function() {
      div.innerHTML = '<div class="text-slate-500 dark:text-slate-400 text-xs italic">Operacion cancelada por el usuario. No se modifico ningun dato.</div>';
    });

    return div;
  }


  
  // ── Renderizado de Tarjeta de Descarga Documental ──────────────────
  function renderizarTarjetaDescarga(datos) {
    var div = document.createElement('div');
    div.className = 'agente-card-descarga mt-3 p-3 bg-emerald-50/90 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-xl text-sm shadow-sm';

    var formato = (datos.formato || 'EXCEL').toUpperCase();
    var colorBadge = 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300';
    var iconEmoji = '📊';

    if (formato === 'PDF') {
      colorBadge = 'bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-300';
      iconEmoji = '📄';
    } else if (formato === 'CSV') {
      colorBadge = 'bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300';
      iconEmoji = '📁';
    }

    var urlDescarga = (datos.url_descarga || "").trim();
    if (!urlDescarga.startsWith('/exportar/')) {
      urlDescarga = '#';
    }

    div.innerHTML = '<div class="flex items-center justify-between gap-3">' +
      '<div class="flex items-center gap-2.5">' +
        '<span class="text-xl">' + iconEmoji + '</span>' +
        '<div>' +
          '<p class="font-semibold text-slate-900 dark:text-slate-100 text-xs">' + escaparHTML(datos.nombre_archivo || 'Reporte_Financiero') + '</p>' +
          '<span class="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ' + colorBadge + '">' + formato + '</span>' +
        '</div>' +
      '</div>' +
      '<a href="' + escaparHTML(urlDescarga) + '" download class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow transition-colors flex items-center gap-1.5 shrink-0">' +
        'Descargar' +
      '</a>' +
    '</div>';

    return div;
  }


  function agregarMensaje(tipo, html, hora) {
    const h = hora || horaActual();
    const art = document.createElement("article");
    art.classList.add("agente-mensaje", `agente-mensaje--${tipo}`);

    const avatarHTML = tipo === "bot"
      ? `<div class="agente-mensaje__avatar"><img src="${logoSrc()}" alt="Gastu IA"></div>`
      : `<div class="agente-mensaje__avatar">${INICIAL}</div>`;

    art.innerHTML = `
      ${avatarHTML}
      <div class="agente-mensaje__burbuja">
        ${html}
        <span class="agente-mensaje__hora">${h}</span>
      </div>`;

    chatContainer.appendChild(art);
    scrollAlFinal();
    return art;
  }

  function setTyping(activo) {
    typingIndicator.style.display = activo ? "flex" : "none";
    typingIndicator.setAttribute("aria-hidden", activo ? "false" : "true");
    if (activo) scrollAlFinal();
  }

  function scrollAlFinal() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  // ── Cargar historial ──────────────────────────────────────

  async function cargarHistorial() {
    try {
      const res = await fetch("/api/agente/chat/", { method: "GET" });
      if (!res.ok) return;
      const data = await res.json();
      if (!data.ok || !data.mensajes.length) return;

      mensajeBienvenida.style.display = "none";
      data.mensajes.forEach(m => {
        agregarMensaje(
          m.rol === "user" ? "user" : "bot",
          m.rol === "user" ? escaparHTML(m.contenido) : formatearBot(m.contenido),
          m.hora
        );
      });
    } catch (e) {
      console.warn("[GASTU] Historial no disponible:", e);
    }
  }

  // ── Envío ─────────────────────────────────────────────────

  async function enviarMensaje(texto) {
    if (!texto || esperandoRespuesta) return;
    texto = texto.trim();
    if (!texto) return;

    mensajeBienvenida.style.display = "none";
    esperandoRespuesta = true;
    btnEnviar.disabled = true;
    input.value = "";
    ajustarAltura();

    agregarMensaje("user", escaparHTML(texto));
    setTyping(true);

    try {
      const res = await fetch("/api/agente/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
        body: JSON.stringify({ mensaje: texto }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setTyping(false);

      var respuestaTexto = data.respuesta || "Sin respuesta del agente.";
      var confirmacionData = null;

      var jsonMatch = respuestaTexto.match(/\{[\s\S]*"requiere_confirmacion"\s*:\s*true[\s\S]*\}/);
      if (jsonMatch) {
        try {
          confirmacionData = JSON.parse(jsonMatch[0]);
          respuestaTexto = respuestaTexto.replace(jsonMatch[0], "").trim();
          if (!respuestaTexto) {
            respuestaTexto = confirmacionData.mensaje_al_usuario || "Se requiere confirmacion para proceder:";
          }
        } catch (e) {
          console.warn("[GASTU] Error parseando confirmacion JSON:", e);
        }
      }

      var descargaData = null;
      var jsonDescargaMatch = respuestaTexto.match(/\{[\s\S]*"es_archivo_descarga"\s*:\s*true[\s\S]*\}/);
      if (jsonDescargaMatch) {
        try {
          descargaData = JSON.parse(jsonDescargaMatch[0]);
          respuestaTexto = respuestaTexto.replace(jsonDescargaMatch[0], "").trim();
          if (!respuestaTexto) {
            respuestaTexto = descargaData.mensaje_al_usuario || "Tu reporte esta listo para descargar:";
          }
        } catch (e) {
          console.warn("[GASTU] Error parseando JSON de descarga:", e);
        }
      }

      var msgEl = agregarMensaje("bot", formatearBot(respuestaTexto));

      if (descargaData && msgEl) {
        var burbujaDescarga = msgEl.querySelector(".agente-mensaje__burbuja");
        if (burbujaDescarga) {
          burbujaDescarga.appendChild(renderizarTarjetaDescarga(descargaData));
          scrollAlFinal();
        }
      }

      if (confirmacionData && msgEl) {
        var burbuja = msgEl.querySelector(".agente-mensaje__burbuja");
        if (burbuja) {
          burbuja.appendChild(renderizarTarjetaConfirmacion(confirmacionData));
          scrollAlFinal();
        }
      }
    } catch (err) {
      setTyping(false);
      agregarMensaje("bot", `<span class="agente-error">Error al procesar tu consulta. Intenta de nuevo.</span>`);
    } finally {
      esperandoRespuesta = false;
      btnEnviar.disabled = input.value.trim() === "";
    }
  }

  // ── Formulario ────────────────────────────────────────────

  form.addEventListener("submit", e => { e.preventDefault(); enviarMensaje(input.value); });

  input.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!btnEnviar.disabled) enviarMensaje(input.value);
    }
  });

  input.addEventListener("input", () => {
    btnEnviar.disabled = input.value.trim() === "" || esperandoRespuesta;
    ajustarAltura();
  });

  function ajustarAltura() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
  }

  // ── Sugerencias ───────────────────────────────────────────

  document.addEventListener("click", e => {
    const s = e.target.closest(".agente-sugerencia");
    if (!s) return;
    const p = s.dataset.pregunta;
    if (!p) return;
    s.closest(".agente-sugerencias")?.remove();
    enviarMensaje(p);
  });

  // ── Limpiar ───────────────────────────────────────────────

  btnLimpiar.addEventListener("click", async () => {
    try {
      await fetch("/api/agente/limpiar/", {
        method: "POST",
        headers: { "X-CSRFToken": getCsrfToken() },
      });
    } catch (e) { console.warn("[GASTU] Error limpiando:", e); }

    chatContainer.querySelectorAll(".agente-mensaje:not(#mensajeBienvenida)").forEach(m => m.remove());
    mensajeBienvenida.style.display = "";

    if (!mensajeBienvenida.querySelector(".agente-sugerencias")) {
      const div = document.createElement("div");
      div.className = "agente-sugerencias";
      div.innerHTML = `
        <button class="agente-sugerencia" data-pregunta="¿Cuál es mi resumen financiero de este mes?">Resumen del mes</button>
        <button class="agente-sugerencia" data-pregunta="¿Cómo van mis metas de ahorro?">Metas de ahorro</button>
        <button class="agente-sugerencia" data-pregunta="¿Qué movimientos recientes tengo?">Últimos movimientos</button>
        <button class="agente-sugerencia" data-pregunta="¿En qué categorías gasto más?">Gastos por categoría</button>
      `;
      mensajeBienvenida.querySelector(".agente-mensaje__burbuja").appendChild(div);
    }

    esperandoRespuesta = false;
    setTyping(false);
    btnEnviar.disabled = true;
    input.value = "";
    ajustarAltura();
    scrollAlFinal();
  });

  // ── Init ──────────────────────────────────────────────────

  setTyping(false);
  cargarHistorial();

})();
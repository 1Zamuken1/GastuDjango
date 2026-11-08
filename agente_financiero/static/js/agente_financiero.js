/**
 * agente_financiero.js — Rediseño Premium GastuApp
 * Manejo conversacional, formateo visual, artifacts y componentes
 */

(function () {
  "use strict";

  const chatContainer     = document.getElementById("agenteChat");
  const scrollArea        = document.getElementById("agenteScroll");
  const form              = document.getElementById("agenteForm");
  const input             = document.getElementById("agenteInput");
  const btnEnviar         = document.getElementById("agenteBtnEnviar");
  const typingIndicator   = document.getElementById("agenteTyping");
  const typingFrase       = document.getElementById("agenteTypingFrase");
  const btnLimpiar        = document.getElementById("btnLimpiarChat");
  const mensajeBienvenida = document.getElementById("mensajeBienvenida");
  const heroSaludo        = document.getElementById("heroSaludo");

  const INICIAL = window.GASTU_USER_INICIAL || "U";
  let esperandoRespuesta = false;

  function getCsrfToken() {
    const inputCsrf = document.querySelector('[name=csrfmiddlewaretoken]');
    if (inputCsrf && inputCsrf.value) return inputCsrf.value;
    const cookie = document.cookie.split("; ").find(r => r.startsWith("csrftoken="));
    return cookie ? cookie.split("=")[1] : "";
  }

  function escaparHTML(texto) {
    if (!texto) return "";
    return texto
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
  }

  // ── Saludo Dinámico según Hora Local ─────────────────────────────
  function actualizarSaludoHero() {
    if (!heroSaludo) return;
    const hora = new Date().getHours();
    let saludo = "Buenos días";
    if (hora >= 12 && hora < 19) {
      saludo = "Buenas tardes";
    } else if (hora >= 19 || hora < 5) {
      saludo = "Buenas noches";
    }
    const nombre = window.GASTU_USER_NAME || "Demo";
    heroSaludo.textContent = `${saludo}, ${nombre}`;
  }

  // ── Formateo Enriquecido de Contenidos Inline ─────────────────────
  function formatearContenidoInline(str) {
    if (!str) return "";
    return str
      // Badges de color: [badge:verde Texto], [badge:rojo Texto], etc.
      .replace(/\[badge:(verde|rojo|azul|naranja)\s+(.*?)\]/gi, function(match, color, cont) {
        return '<span class="agente-badge agente-badge--' + color.toLowerCase() + '">' + cont + '</span>';
      })
      // Colores de texto inline: [color:verde Texto], etc.
      .replace(/\[color:(verde|rojo|azul|naranja)\s+(.*?)\]/gi, function(match, color, cont) {
        return '<span class="agente-color--' + color.toLowerCase() + '">' + cont + '</span>';
      })
      // Código en línea: `codigo`
      .replace(/`([^`]+)`/g, '<code class="agente-codigo-inline">$1</code>')
      // Negrita: **texto**
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // Cursiva: *texto*
      .replace(/(^|[^\*])\*([^\*]+)\*([^\*]|$)/g, '$1<em>$2</em>$3');
  }

  // ── Procesador de Tablas Markdown como Artifacts ───────────────────
  function procesarTablasMarkdown(texto) {
    var lineas = texto.split(/\r?\n/);
    var resultado = [];
    var i = 0;

    while (i < lineas.length) {
      var linea = lineas[i];
      if (linea.includes('|') && i + 1 < lineas.length && /^\s*\|?\s*:?-+:?\s*(\|?\s*:?-+:?\s*)+\|?\s*$/.test(lineas[i + 1])) {
        var headerLinea = linea;
        var separatorLinea = lineas[i + 1];
        i += 2;

        var parseFila = function(str) {
          var trimmed = str.trim();
          if (trimmed.startsWith('|')) trimmed = trimmed.substring(1);
          if (trimmed.endsWith('|')) trimmed = trimmed.substring(0, trimmed.length - 1);
          return trimmed.split('|').map(function(c) { return c.trim(); });
        };

        var headers = parseFila(headerLinea);
        var filas = [];

        while (i < lineas.length && lineas[i].trim().includes('|') && lineas[i].trim() !== '') {
          filas.push(parseFila(lineas[i]));
          i++;
        }

        var tsvRows = [];
        tsvRows.push(headers.join('\t'));
        filas.forEach(function(f) {
          tsvRows.push(f.join('\t'));
        });
        var tsvData = encodeURIComponent(tsvRows.join('\n'));

        var htmlTabla = '<div class="agente-artifact-card" data-tipo="tabla">';
        htmlTabla += '  <div class="agente-artifact-header">';
        htmlTabla += '    <span class="agente-artifact-tag"><i data-lucide="table"></i> TABLA DE DATOS</span>';
        htmlTabla += '    <button type="button" class="agente-btn-copiar-tabla" data-tsv="' + tsvData + '" title="Copiar datos para Excel o Hojas de Cálculo">';
        htmlTabla += '      <i data-lucide="copy"></i> <span>Copiar tabla</span>';
        htmlTabla += '    </button>';
        htmlTabla += '  </div>';
        htmlTabla += '  <div class="agente-tabla-wrap">';
        htmlTabla += '    <table class="agente-tabla">';
        htmlTabla += '      <thead><tr>';
        headers.forEach(function(h) {
          htmlTabla += '        <th>' + formatearContenidoInline(h) + '</th>';
        });
        htmlTabla += '      </tr></thead><tbody>';
        filas.forEach(function(f) {
          htmlTabla += '      <tr>';
          f.forEach(function(c) {
            htmlTabla += '        <td>' + formatearContenidoInline(c) + '</td>';
          });
          htmlTabla += '      </tr>';
        });
        htmlTabla += '    </tbody></table>';
        htmlTabla += '  </div>';
        htmlTabla += '</div>';

        resultado.push(htmlTabla);
      } else {
        resultado.push(linea);
        i++;
      }
    }

    return resultado.join('\n');
  }

  // ── Procesador de Callouts ─────────────────────────────────────────
  function procesarCallouts(texto) {
    var lineas = texto.split(/\r?\n/);
    var resultado = [];
    var i = 0;

    var tipoCalloutMap = {
      'TIP':     { clase: 'agente-callout--tip',     icono: 'lightbulb' },
      'WARNING': { clase: 'agente-callout--warning', icono: 'alert-triangle' },
      'NOTE':    { clase: 'agente-callout--note',    icono: 'info' },
      'DANGER':  { clase: 'agente-callout--danger',  icono: 'alert-octagon' }
    };

    while (i < lineas.length) {
      var linea = lineas[i];
      var match = linea.match(/^\s*&gt;\s*\[!(TIP|WARNING|NOTE|DANGER)\]\s*(.*)$/i) ||
                  linea.match(/^\s*>\s*\[!(TIP|WARNING|NOTE|DANGER)\]\s*(.*)$/i);

      if (match) {
        var tipo = match[1].toUpperCase();
        var primerContenido = match[2];
        var info = tipoCalloutMap[tipo] || tipoCalloutMap['NOTE'];
        var bloqueLineas = [];
        if (primerContenido && primerContenido.trim()) {
          bloqueLineas.push(primerContenido.trim());
        }
        i++;

        while (i < lineas.length) {
          var sig = lineas[i];
          var contMatch = sig.match(/^\s*&gt;\s?(.*)$/) || sig.match(/^\s*>\s?(.*)$/);
          if (contMatch) {
            if (/^\s*\[!(TIP|WARNING|NOTE|DANGER)\]/i.test(contMatch[1])) {
              break;
            }
            bloqueLineas.push(contMatch[1]);
            i++;
          } else {
            break;
          }
        }

        var cuerpoCallout = bloqueLineas.join('<br>');
        var htmlCallout = '<div class="agente-callout ' + info.clase + '">' +
                          '  <i data-lucide="' + info.icono + '"></i>' +
                          '  <div class="agente-callout__texto">' + formatearContenidoInline(cuerpoCallout) + '</div>' +
                          '</div>';
        resultado.push(htmlCallout);
      } else {
        resultado.push(linea);
        i++;
      }
    }

    return resultado.join('\n');
  }

  // ── Pipeline Principal de Formateo Markdown ───────────────────────
  function formatearBot(texto) {
    if (!texto) return "";
    var t = escaparHTML(texto);

    // Titular destacado si empieza con ## o similar
    t = t.replace(/^##\s+(.*?)$/gm, '<h3 class="agente-lead">$1</h3>');
    t = t.replace(/^###\s+(.*?)$/gm, '<h4 class="agente-sublead" style="font-family:\'Plus Jakarta Sans\',sans-serif;font-weight:700;margin:8px 0 4px;">$1</h4>');

    // Tablas y Callouts
    t = procesarTablasMarkdown(t);
    t = procesarCallouts(t);

    // Líneas restantes
    var partes = t.split(/\n{2,}/);
    var htmlPartes = partes.map(function(p) {
      var pTrim = p.trim();
      if (!pTrim) return "";
      if (pTrim.startsWith('<div class="agente-artifact-card"') ||
          pTrim.startsWith('<div class="agente-callout"') ||
          pTrim.startsWith('<h3 class="agente-lead"') ||
          pTrim.startsWith('<h4 class="agente-sublead"')) {
        return pTrim;
      }
      return '<p>' + formatearContenidoInline(pTrim.replace(/\n/g, '<br>')) + '</p>';
    });

    return htmlPartes.join("");
  }

  // ── Renderizado de Mensajes en el Chat ────────────────────────────
  function agregarMensaje(rol, htmlContenido, hora, opciones) {
    opciones = opciones || {};
    var animo = opciones.animo || "normal";
    var procedencia = opciones.procedencia || "";

    var h = hora || new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    var item = document.createElement("article");

    if (rol === "user") {
      item.className = "agente-me";
      item.innerHTML = `
        <div class="agente-me__burbuja">${htmlContenido}</div>
        <span class="agente-me__hora">${h}</span>
      `;
    } else {
      // Mensaje de la IA — Directo en el lienzo sin burbuja contenedora
      item.className = "agente-ai";
      item.setAttribute("data-animo", animo);

      var staticUrl = window.GASTU_STATIC_URL || "/static/";
      var avatarClase = "agente-avatar agente-avatar--msg";
      if (animo === "alerta") avatarClase += " agente-avatar--alerta";
      else if (animo === "critico") avatarClase += " agente-avatar--critico";

      var procedenciaHtml = procedencia ? `<span class="agente-procedencia">${escaparHTML(procedencia)}</span>` : "";

      item.innerHTML = `
        <div class="${avatarClase}">
          <img src="${staticUrl}img/gastu_logo_rostro.png" alt="Gastu IA" class="agente-avatar__img">
        </div>
        <div class="agente-tx">
          <div class="agente-mensaje__cuerpo">${htmlContenido}</div>
          <div class="agente-meta-bar">
            <div class="agente-meta-bar__left">
              <button type="button" class="agente-btn-action agente-btn-copiar-msg" title="Copiar respuesta" aria-label="Copiar respuesta completa">
                <i data-lucide="copy"></i>
              </button>
            </div>
            ${procedenciaHtml}
          </div>
        </div>
      `;
    }

    chatContainer.appendChild(item);

    if (window.lucide) {
      window.lucide.createIcons({ root: item });
    }

    scrollAlFinal();
    return item;
  }

  function setTyping(activo, frase) {
    if (!typingIndicator) return;
    typingIndicator.style.display = activo ? "block" : "none";
    typingIndicator.setAttribute("aria-hidden", activo ? "false" : "true");
    if (typingFrase && frase) {
      typingFrase.textContent = frase;
    } else if (typingFrase) {
      typingFrase.textContent = "Revisando tus datos financieros";
    }
    if (activo) scrollAlFinal();
  }

  function scrollAlFinal() {
    if (scrollArea) {
      scrollArea.scrollTop = scrollArea.scrollHeight;
    }
  }

  // ── Cargar Historial ──────────────────────────────────────────────
  async function cargarHistorial() {
    try {
      const res = await fetch("/api/agente/chat/", { method: "GET" });
      if (!res.ok) return;
      const data = await res.json();
      if (!data.ok || !data.mensajes.length) {
        if (mensajeBienvenida) mensajeBienvenida.style.display = "";
        return;
      }

      if (mensajeBienvenida) mensajeBienvenida.style.display = "none";
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

  // ── Envío de Mensajes ─────────────────────────────────────────────
  async function enviarMensaje(texto) {
    if (!texto || esperandoRespuesta) return;
    texto = texto.trim();
    if (!texto) return;

    if (mensajeBienvenida) mensajeBienvenida.style.display = "none";
    esperandoRespuesta = true;
    btnEnviar.disabled = true;
    input.value = "";
    ajustarAltura();

    agregarMensaje("user", escaparHTML(texto));
    setTyping(true, "Consultando tus finanzas");

    try {
      const res = await fetch("/api/agente/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
        body: JSON.stringify({ mensaje: texto }),
      });
      if (!res.ok) {
        let msg = "Error al procesar tu consulta. Intenta de nuevo.";
        try {
          const errData = await res.json();
          if (errData && errData.error) msg = errData.error;
        } catch (_) {}
        throw new Error(msg);
      }
      const data = await res.json();
      setTyping(false);

      var respuestaTexto = data.respuesta || "Sin respuesta del agente.";
      agregarMensaje("bot", formatearBot(respuestaTexto));

    } catch (err) {
      setTyping(false);
      var textoError = (err && err.message) ? err.message : "Error al procesar tu consulta. Intenta de nuevo.";
      agregarMensaje("bot", `<span class="agente-error" style="color:var(--agente-danger);font-weight:500;">${escaparHTML(textoError)}</span>`);
    } finally {
      esperandoRespuesta = false;
      btnEnviar.disabled = input.value.trim() === "";
    }
  }

  // ── Formulario y Ajuste de Altura ─────────────────────────────────
  form.addEventListener("submit", e => {
    e.preventDefault();
    enviarMensaje(input.value);
  });

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
    input.style.height = Math.min(input.scrollHeight, 132) + "px";
  }

  // ── Botones del Hero de Estado Vacío ──────────────────────────────
  document.addEventListener("click", e => {
    const askBtn = e.target.closest(".agente-ask-btn");
    if (!askBtn) return;
    const pregunta = askBtn.dataset.pregunta;
    if (pregunta) {
      enviarMensaje(pregunta);
    }
  });

  // ── Botón Limpiar con GastuAlerts (SweetAlert2) ────────────────────
  btnLimpiar.addEventListener("click", async () => {
    let confirmado = true;

    if (window.GastuAlerts && window.GastuAlerts.confirm) {
      confirmado = await window.GastuAlerts.confirm(
        "¿Vaciar conversación?",
        "Se borrará todo el historial del chat de forma permanente.",
        "Sí, vaciar",
        "Cancelar"
      );
    } else {
      confirmado = confirm("¿Estás seguro de que deseas vaciar toda la conversación?");
    }

    if (!confirmado) return;

    try {
      await fetch("/api/agente/limpiar/", {
        method: "POST",
        headers: { "X-CSRFToken": getCsrfToken() },
      });
      if (window.GastuAlerts && window.GastuAlerts.toastSuccess) {
        window.GastuAlerts.toastSuccess("Conversación vaciada correctamente.");
      }
    } catch (e) {
      console.warn("[GASTU] Error limpiando:", e);
    }

    // Limpiar mensajes y mostrar el Hero
    chatContainer.querySelectorAll(".agente-me, .agente-ai").forEach(m => m.remove());
    if (mensajeBienvenida) {
      mensajeBienvenida.style.display = "";
      actualizarSaludoHero();
    }

    esperandoRespuesta = false;
    setTyping(false);
    btnEnviar.disabled = true;
    input.value = "";
    ajustarAltura();
    scrollAlFinal();
  });

  // ── Delegación de Eventos para Copiar Mensajes y Tablas ───────────
  chatContainer.addEventListener("click", function(e) {
    // 1. Copiar mensaje completo del bot
    var btnCopiarMsg = e.target.closest(".agente-btn-copiar-msg");
    if (btnCopiarMsg) {
      var cuerpo = btnCopiarMsg.closest(".agente-tx")?.querySelector(".agente-mensaje__cuerpo");
      if (cuerpo) {
        var textoACopiar = (cuerpo.innerText || cuerpo.textContent || "").trim();
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(textoACopiar).then(function() {
            if (window.GastuAlerts && window.GastuAlerts.toastSuccess) {
              window.GastuAlerts.toastSuccess("Respuesta copiada al portapapeles.");
            }
          }).catch(function(err) {
            console.warn("[GASTU] Error al copiar:", err);
          });
        }
      }
      return;
    }

    // 2. Copiar solo el Artifact (Tabla de datos en TSV)
    var btnCopiarTabla = e.target.closest(".agente-btn-copiar-tabla");
    if (btnCopiarTabla) {
      var tsvEncoded = btnCopiarTabla.getAttribute("data-tsv") || "";
      var tsvData = decodeURIComponent(tsvEncoded);
      if (tsvData && navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(tsvData).then(function() {
          var span = btnCopiarTabla.querySelector("span");
          var textoOrig = span ? span.textContent : "Copiar tabla";
          btnCopiarTabla.classList.add("copiado");
          if (span) span.textContent = "✓ ¡Copiado!";
          if (window.GastuAlerts && window.GastuAlerts.toastSuccess) {
            window.GastuAlerts.toastSuccess("Tabla copiada (formato TSV para Excel).");
          }
          setTimeout(function() {
            btnCopiarTabla.classList.remove("copiado");
            if (span) span.textContent = textoOrig;
          }, 2000);
        }).catch(function(err) {
          console.warn("[GASTU] Error al copiar tabla:", err);
        });
      }
      return;
    }
  });

  // ── Init ──────────────────────────────────────────────────────────
  actualizarSaludoHero();
  setTyping(false);
  cargarHistorial();

})();

/**
 * agente_financiero.js — Rediseño Premium GastuApp
 * Manejo conversacional, formateo visual, artifacts y componentes especializados (Medidor, Cifras, Libreta, etc.)
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
  const wrapper           = document.getElementById("agenteWrapper");
  const NOMBRE_USUARIO    = (wrapper && wrapper.dataset.usuarioNombre) || "";
  const MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

  let esperandoRespuesta = false;

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]')?.content;
    if (meta) return meta;
    const inputCsrf = document.querySelector('[name=csrfmiddlewaretoken]');
    if (inputCsrf && inputCsrf.value) return inputCsrf.value;
    const cookie = document.cookie.split("; ").find(r => r.startsWith("csrftoken="));
    return cookie ? cookie.split("=")[1] : "";
  }

  function escaparHTML(texto) {
    if (!texto) return "";
    return String(texto)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
  }

  function fechaCorta(texto) {
    return String(texto || "").replace(/\b(\d{4})-(\d{2})-(\d{2})\b/g, function (m, a, mes, dia) {
      var i = parseInt(mes, 10) - 1;
      return (i >= 0 && i < 12) ? dia + " " + MESES_CORTOS[i] : m;
    });
  }

  function formatearCOP(monto) {
    var n = Math.round(Number(monto) || 0);
    return "$" + n.toLocaleString("es-CO");
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
    heroSaludo.innerHTML = escaparHTML(NOMBRE_USUARIO ? saludo + ", " + NOMBRE_USUARIO + "." : saludo + ".") +
      '<span class="agente-hero__pregunta">¿Qué revisamos hoy?</span>';
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
        htmlTabla += '    <button type="button" class="agente-btn-copiar-tabla" data-tsv="' + tsvData + '" title="Copiar datos para Excel">';
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
      // "> [!TIP] texto" o una cita simple "> texto" (se muestra como nota).
      var match = linea.match(/^\s*&gt;\s*(?:\[!(TIP|WARNING|NOTE|DANGER)\])?\s*(.*)$/i);

      if (match) {
        var tipo = (match[1] || "NOTE").toUpperCase();
        var primerContenido = match[2];
        var info = tipoCalloutMap[tipo] || tipoCalloutMap['NOTE'];
        var bloqueLineas = [];
        if (primerContenido && primerContenido.trim()) {
          bloqueLineas.push(primerContenido.trim());
        }
        i++;

        while (i < lineas.length) {
          var sig = lineas[i];
          var contMatch = sig.match(/^\s*&gt;\s?(.*)$/);
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

  // ── Renderizadores Especializados (Fase 3) ─────────────────────────

  // 1. Medidor de 24 Segmentos (Indicador de Combustible Financiero)
  function renderMedidor(datos) {
    if (!datos) return "";
    var consumoPct = Math.round(datos.consumo_pct || 0);
    var umbralPct = Math.round(datos.umbral_pct || 80);
    var limite = datos.limite || 0;
    var gastado = datos.gastado || 0;

    var numLlenos = Math.min(Math.round((consumoPct / 100) * 24), 24);
    var numUmbral = Math.min(Math.round((umbralPct / 100) * 24), 24);

    var banderaTexto = formatearCOP(gastado) + " de " + formatearCOP(limite);
    var banderaPos = Math.round(Math.min(Math.max(((numLlenos - 0.5) / 24) * 100, 0), 100) * 10) / 10;

    var ariaLabel = consumoPct + "% consumido, " + formatearCOP(gastado) + " de " + formatearCOP(limite);

    var html = '<div class="agente-medidor" role="region" aria-label="Indicador de consumo presupuestal">';
    // --pos mueve la bandera y la desplaza en la misma proporcion: al 0% queda alineada a la
    // izquierda, al 100% a la derecha, y la flecha siempre apunta al ultimo segmento lleno.
    html += '  <div class="agente-medidor__bandera" style="--pos: ' + banderaPos + '%;">' + escaparHTML(banderaTexto) + '</div>';
    html += '  <div class="agente-medidor__track" role="img" aria-label="' + escaparHTML(ariaLabel) + '">';

    for (var s = 1; s <= 24; s++) {
      var claseSeg = "agente-medidor__seg";
      if (s <= numLlenos) {
        if (s <= numUmbral) {
          claseSeg += " is-ok";
        } else if (consumoPct >= 100) {
          claseSeg += " is-danger";
        } else {
          claseSeg += " is-warn";
        }
      }
      html += '<i class="' + claseSeg + '" aria-hidden="true"></i>';
    }

    html += '    <u class="agente-medidor__umbral-linea" style="left: ' + umbralPct + '%;" aria-hidden="true"></u>';
    html += '  </div>';
    html += '  <div class="agente-medidor__escala" aria-hidden="true">';
    html += '    <span style="left: ' + umbralPct + '%; font-weight: 500;">Alerta al ' + umbralPct + '%</span>';
    html += '  </div>';
    html += '</div>';

    return html;
  }

  // 2. Cifras Destacadas (2 Columnas)
  function renderCifras(datos) {
    if (!datos || !datos.items || !datos.items.length) return "";
    var html = '<div class="agente-cifras">';
    datos.items.forEach(function(item) {
      var claseCol = "agente-cifras__col" + (item.tono === "ok" ? " is-ok" : (item.tono === "danger" ? " is-danger" : ""));
      var valorFormateado = typeof item.valor === "number" ? formatearCOP(item.valor) : escaparHTML(item.valor);
      html += '  <div class="' + claseCol + '">';
      html += '    ' + escaparHTML(item.etiqueta);
      html += '    <b class="agente-cifras__valor">' + valorFormateado + '</b>';
      html += '  </div>';
    });
    html += '</div>';
    return html;
  }

  // 3. Libreta Contable de Movimientos
  function renderLibreta(datos) {
    if (!datos || !datos.filas) return "";
    var titulo = datos.titulo || "Movimientos";
    // Siempre enteros: estos valores se insertan como HTML y el JSON puede venir del modelo.
    var mostradas = parseInt(datos.mostradas, 10) || datos.filas.length;
    var totalFilas = parseInt(datos.total_filas, 10) || mostradas;
    var total = datos.total || null;

    var tsvRows = ["Fecha\tConcepto\tMonto\tTipo"];
    datos.filas.forEach(function(f) {
      tsvRows.push((f.fecha || "") + "\t" + (f.concepto || "") + "\t" + (f.monto || 0) + "\t" + (f.movimiento || "EGRESO"));
    });
    var tsvData = encodeURIComponent(tsvRows.join("\n"));

    var html = '<div class="agente-libreta" role="table" aria-label="' + escaparHTML(titulo) + '">';
    html += '  <div class="agente-libreta__header">';
    html += '    <span>' + escaparHTML(titulo) + '</span>';
    html += '    <div style="display:flex;align-items:center;gap:10px;">';
    html += '      <small>' + mostradas + ' de ' + totalFilas + '</small>';
    html += '      <button type="button" class="agente-btn-copiar-tabla" data-tsv="' + tsvData + '" title="Copiar movimientos para Excel" style="padding:2px 8px;font-size:11.5px;">';
    html += '        <i data-lucide="copy"></i> <span>Copiar</span>';
    html += '      </button>';
    html += '    </div>';
    html += '  </div>';

    datos.filas.forEach(function(fila) {
      var esIngreso = fila.movimiento === "INGRESO";
      var montoClase = "agente-libreta__monto" + (esIngreso ? " agente-libreta__monto--ingreso" : "");
      var signo = esIngreso ? "+" : "-";
      var montoStr = signo + formatearCOP(fila.monto);

      html += '  <div class="agente-libreta__row" role="row">';
      html += '    <em class="agente-libreta__fecha" role="cell">' + escaparHTML(fechaCorta(fila.fecha)) + '</em>';
      html += '    <span class="agente-libreta__concepto" role="cell" title="' + escaparHTML(fila.concepto || "") + '">' + escaparHTML(fila.concepto || "Sin detalle") + '</span>';
      html += '    <u class="agente-libreta__puntos" aria-hidden="true"></u>';
      html += '    <b class="' + montoClase + '" role="cell">' + montoStr + '</b>';
      html += '  </div>';
    });

    if (totalFilas > mostradas) {
      var restantes = totalFilas - mostradas;
      html += '  <div class="agente-libreta__mas">y ' + restantes + ' movimientos más</div>';
    }

    if (total) {
      html += '  <div class="agente-libreta__total">';
      html += '    <span>' + escaparHTML(total.etiqueta || "Total") + '</span>';
      html += '    <b>' + formatearCOP(total.valor) + '</b>';
      html += '  </div>';
    }

    html += '</div>';
    return html;
  }

  // 4. Atajos de Seguimiento ("Para seguir")
  function renderSiguientes(items) {
    if (!items || !items.length) return "";
    var html = '<div class="agente-next">';
    items.slice(0, 2).forEach(function(item) {
      html += '  <button type="button" class="agente-next-btn" data-pregunta="' + escaparHTML(item.pregunta || item.etiqueta) + '">';
      html += '    <span>' + escaparHTML(item.etiqueta) + '</span>';
      html += '    <i data-lucide="message-square"></i>';
      html += '  </button>';
    });
    html += '</div>';
    return html;
  }

  // 5. Tarjeta de confirmacion: el agente prepara el cambio y el usuario decide.
  var ESTADOS_CONFIRMACION = {
    CONFIRMADA: "Confirmado",
    CANCELADA: "Cancelado, no se hizo ningún cambio",
    FALLIDA: "No se pudo aplicar",
    VENCIDA: "Venció sin confirmarse",
  };

  function renderConfirmacion(b) {
    var token = String(b.token || "");
    var estado = b.estado || "PENDIENTE";
    var html = '<div class="agente-confirmacion" data-token="' + escaparHTML(token) + '" role="group" aria-label="Acción por confirmar">';
    html += '  <div class="agente-confirmacion__cabecera"><i data-lucide="shield-check" aria-hidden="true"></i><span>Revisa antes de guardar</span></div>';
    html += '  <p class="agente-confirmacion__resumen">' + escaparHTML(b.resumen || "") + '</p>';
    if (estado === "PENDIENTE" && token) {
      html += '  <div class="agente-confirmacion__acciones">';
      html += '    <button type="button" class="agente-confirmacion__btn agente-confirmacion__btn--ok" data-decision="confirmar">Confirmar</button>';
      html += '    <button type="button" class="agente-confirmacion__btn" data-decision="cancelar">Cancelar</button>';
      html += '  </div>';
      html += '  <p class="agente-confirmacion__estado" aria-live="polite"></p>';
    } else {
      html += '  <p class="agente-confirmacion__estado is-' + escaparHTML(estado.toLowerCase()) + '">' + escaparHTML(ESTADOS_CONFIRMACION[estado] || "") + '</p>';
    }
    html += '</div>';
    return html;
  }

  // 6. Boton de descarga: solo rutas internas de exportacion.
  function renderDescarga(b) {
    var url = String(b.url || "");
    if (!/^\/exportar\/(excel|pdf|csv)\/\?[\w=&%.\-]*$/.test(url)) return "";
    return '<a class="agente-descarga" href="' + escaparHTML(url) + '" download>' +
      '<i data-lucide="download" aria-hidden="true"></i><span>' + escaparHTML(b.etiqueta || "Descargar reporte") + '</span></a>';
  }

  async function resolverConfirmacion(tarjeta, decision, boton) {
    var token = tarjeta.dataset.token;
    var estadoEl = tarjeta.querySelector(".agente-confirmacion__estado");
    var botones = tarjeta.querySelectorAll(".agente-confirmacion__btn");
    botones.forEach(function(btn) { btn.disabled = true; });
    try {
      var res = await fetch("/api/agente/acciones/" + encodeURIComponent(token) + "/" + decision + "/", {
        method: "POST",
        headers: { "X-CSRFToken": getCsrfToken() },
      });
      var data = {};
      try { data = await res.json(); } catch (_) {}
      if (!res.ok || !data.ok) throw new Error(data.error || "No se pudo completar la acción.");
      var acciones = tarjeta.querySelector(".agente-confirmacion__acciones");
      if (acciones) acciones.remove();
      if (estadoEl) {
        estadoEl.textContent = data.mensaje || ESTADOS_CONFIRMACION[data.estado] || "";
        estadoEl.className = "agente-confirmacion__estado is-" + String(data.estado || "").toLowerCase();
      }
    } catch (err) {
      botones.forEach(function(btn) { btn.disabled = false; });
      if (estadoEl) {
        estadoEl.textContent = err.message;
        estadoEl.className = "agente-confirmacion__estado is-fallida";
      }
    }
  }

  // ── Ensamblador de Bloques Estructurados (Contrato Fase 4) ────────
  function renderBloques(bloques) {
    if (!bloques || !bloques.length) return "";
    var htmlPartes = [];

    bloques.forEach(function(b) {
      switch (b.tipo) {
        case "titular":
          htmlPartes.push('<h2 class="agente-lead">' + escaparHTML(b.texto) + '</h2>');
          break;
        case "medidor":
          htmlPartes.push(renderMedidor(b));
          break;
        case "cifras":
          htmlPartes.push(renderCifras(b));
          break;
        case "consejo":
          var txt = b.texto || "";
          htmlPartes.push('<p class="agente-consejo"><strong>Mi consejo.</strong> ' + formatearContenidoInline(escaparHTML(txt)) + '</p>');
          break;
        case "libreta":
          htmlPartes.push(renderLibreta(b));
          break;
        case "siguientes":
          htmlPartes.push(renderSiguientes(b.items));
          break;
        case "procedencia":
          if (b.texto) {
            htmlPartes.push('<p class="agente-procedencia">' + escaparHTML(b.texto) + '</p>');
          }
          break;
        case "texto":
          htmlPartes.push(formatearBot(b.texto));
          break;
        case "confirmacion":
          htmlPartes.push(renderConfirmacion(b));
          break;
        case "descarga":
          htmlPartes.push(renderDescarga(b));
          break;
        default:
          if (b.texto) htmlPartes.push('<p>' + escaparHTML(b.texto) + '</p>');
          break;
      }
    });

    return htmlPartes.join("");
  }

  // ── Pipeline Principal de Formateo de Respuestas ─────────────────
  function formatearBot(texto) {
    if (!texto) return "";

    // El texto del modelo siempre se trata como texto: los bloques estructurados
    // (tarjetas, medidores, botones) solo los genera el servidor. Asi una prompt
    // injection no puede pintar botones o tarjetas falsas en el chat.

    // Formateo Markdown enriquecido
    var t = escaparHTML(fechaCorta(texto));

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
          pTrim.startsWith('<div class="agente-medidor"') ||
          pTrim.startsWith('<div class="agente-cifras"') ||
          pTrim.startsWith('<div class="agente-libreta"') ||
          pTrim.startsWith('<h3 class="agente-lead"') ||
          pTrim.startsWith('<h4 class="agente-sublead"')) {
        return pTrim;
      }
      return '<p>' + formatearContenidoInline(pTrim.replace(/\n/g, '<br>')) + '</p>';
    });

    return htmlPartes.join("");
  }

  // Error dentro del flujo: el mensaje y un boton para reintentar la misma pregunta.
  function renderError(mensaje, pregunta) {
    var html = '<div class="agente-error" role="alert">';
    html += '  <p class="agente-error__texto">' + escaparHTML(mensaje) + '</p>';
    if (pregunta) {
      html += '  <button type="button" class="agente-error__reintentar" data-pregunta="' + escaparHTML(pregunta) + '">';
      html += '    <i data-lucide="rotate-ccw" aria-hidden="true"></i><span>Reintentar</span>';
      html += '  </button>';
    }
    html += '</div>';
    return html;
  }

  // ── Renderizado de Mensajes en el Chat ────────────────────────────
  function agregarMensaje(rol, htmlContenido, hora, opciones) {
    opciones = opciones || {};
    var animo = opciones.animo || "normal";
    var procedencia = opciones.procedencia || "";
    var pregunta = opciones.pregunta || "";

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
              ${pregunta ? `<button type="button" class="agente-btn-action agente-btn-regenerar" title="Regenerar respuesta" aria-label="Regenerar respuesta" data-pregunta="${escaparHTML(pregunta)}">
                <i data-lucide="refresh-cw"></i>
              </button>` : ""}
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
    typingIndicator.hidden = !activo;
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
      var ultimaPregunta = "";
      data.mensajes.forEach(m => {
        if (m.rol === "user") ultimaPregunta = m.contenido;
        var contenidoHtml = "";
        if (m.bloques && Array.isArray(m.bloques)) {
          contenidoHtml = renderBloques(m.bloques);
        } else {
          contenidoHtml = m.rol === "user" ? escaparHTML(m.contenido) : formatearBot(m.contenido);
        }
        agregarMensaje(
          m.rol === "user" ? "user" : "bot",
          contenidoHtml,
          m.hora,
          { animo: m.animo, procedencia: m.procedencia, pregunta: m.rol === "user" ? "" : ultimaPregunta }
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

      var respuestaHtml = "";
      if (data.bloques && Array.isArray(data.bloques)) {
        respuestaHtml = renderBloques(data.bloques);
      } else {
        respuestaHtml = formatearBot(data.respuesta || "Sin respuesta del agente.");
      }

      agregarMensaje("bot", respuestaHtml, null, { animo: data.animo, procedencia: data.procedencia, pregunta: texto });

    } catch (err) {
      setTyping(false);
      var textoError = (err && err.message) ? err.message : "Error al procesar tu consulta. Intenta de nuevo.";
      agregarMensaje("bot", renderError(textoError, texto), null, { animo: "critico" });
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

  // ── Botones del Hero y Atajos "Para Seguir" ───────────────────────
  document.addEventListener("click", e => {
    // 1. Botones del Hero inicial
    const askBtn = e.target.closest(".agente-ask-btn");
    if (askBtn) {
      const pregunta = askBtn.dataset.pregunta;
      if (pregunta) enviarMensaje(pregunta);
      return;
    }

    // 2. Reintentar tras un error o regenerar una respuesta
    const reenviar = e.target.closest(".agente-error__reintentar, .agente-btn-regenerar");
    if (reenviar) {
      const pregunta = reenviar.dataset.pregunta;
      if (pregunta && !esperandoRespuesta) {
        const error = reenviar.closest(".agente-ai");
        if (reenviar.classList.contains("agente-error__reintentar") && error) {
          // La pregunta fallida se vuelve a enviar: se quita su burbuja para no duplicarla.
          const previa = error.previousElementSibling;
          if (previa && previa.classList.contains("agente-me")) previa.remove();
          error.remove();
        }
        enviarMensaje(pregunta);
      }
      return;
    }

    // 3. Atajos de seguimiento (.agente-next-btn)
    const nextBtn = e.target.closest(".agente-next-btn");
    if (nextBtn) {
      const pregunta = nextBtn.dataset.pregunta;
      if (pregunta) enviarMensaje(pregunta);
      return;
    }
  });

  // ── Botón Limpiar con GastuAlerts (SweetAlert2) ────────────────────
  btnLimpiar.addEventListener("click", async () => {
    let confirmado = true;

    if (window.GastuAlerts && window.GastuAlerts.confirmar) {
      confirmado = await window.GastuAlerts.confirmar(
        "¿Vaciar la conversación?",
        "Se borrará todo el historial del chat de forma permanente. Tus movimientos no cambian.",
        "Sí, vaciar"
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
    // 0. Confirmar o cancelar una accion preparada por el agente
    var btnDecision = e.target.closest(".agente-confirmacion__btn");
    if (btnDecision) {
      var tarjeta = btnDecision.closest(".agente-confirmacion");
      if (tarjeta) resolverConfirmacion(tarjeta, btnDecision.dataset.decision === "confirmar" ? "confirmar" : "cancelar", btnDecision);
      return;
    }

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

    // 2. Copiar Artifact (Tabla de datos o Libreta en TSV)
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
            window.GastuAlerts.toastSuccess("Datos copiados (formato TSV para Excel).");
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

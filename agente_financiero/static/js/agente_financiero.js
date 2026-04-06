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
    return texto
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br>");
  }

  function horaActual() {
    return new Date().toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" });
  }

  function logoSrc() {
    return document.querySelector(".agente-avatar__img")?.src || "";
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
      agregarMensaje("bot", formatearBot(data.respuesta || "Sin respuesta del agente."));
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
/* ═══════════════════════════════════════════════════════════════
   gastuapp_layout.js  —  Lógica global del layout de GastuApp
   Sidebar toggle · User dropdown · Notificaciones
   ═══════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();

  const body = document.body;
  const toggleDesktop = document.getElementById("sidebar-toggle");
  const toggleMobile = document.getElementById("sidebar-toggle-mobile");
  const overlay = document.getElementById("sidebar-overlay");
  const isMobile = () => window.innerWidth < 768;
  const isTablet = () =>
    window.innerWidth >= 768 && window.innerWidth < 1024;

  // ── Restaurar estado guardado (solo desktop) ──────────────
  if (!isMobile() && !isTablet()) {
    if (localStorage.getItem("sidebar-mini") === "true") {
      body.classList.add("sidebar-mini");
    }
  }

  // ── Toggle desktop (dentro del sidebar) ──────────────────
  toggleDesktop?.addEventListener("click", () => {
    if (isTablet()) {
      // En tablet: alternar overlay (no empuja contenido)
      const open = body.classList.toggle("sidebar-forced-open");
      overlay.classList.toggle("show", open);
    } else {
      // En desktop: alternar mini/full y guardar en localStorage
      body.classList.toggle("sidebar-mini");
      localStorage.setItem(
        "sidebar-mini",
        body.classList.contains("sidebar-mini"),
      );
    }
  });

  // ── Toggle mobile (hamburguesa en topbar) ─────────────────
  toggleMobile?.addEventListener("click", () => {
    const open = body.classList.toggle("sidebar-open");
    overlay.classList.toggle("show", open);
  });

  // Cerrar sidebar al click en overlay
  overlay.addEventListener("click", () => {
    body.classList.remove("sidebar-open");
    body.classList.remove("sidebar-forced-open");
    overlay.classList.remove("show");
  });

  // Cerrar sidebar al navegar (mobile y tablet)
  document.querySelectorAll("#sidebar .nav-item").forEach((item) => {
    item.addEventListener("click", () => {
      if (isMobile()) {
        body.classList.remove("sidebar-open");
        overlay.classList.remove("show");
      }
      if (isTablet()) {
        body.classList.remove("sidebar-forced-open");
        overlay.classList.remove("show");
      }
    });
  });

  // Ajustar en resize
  window.addEventListener("resize", () => {
    if (!isMobile()) {
      body.classList.remove("sidebar-open");
      overlay.classList.remove("show");
    }
    // Limpiar sidebar-forced-open fuera de tablet
    if (!isTablet()) {
      body.classList.remove("sidebar-forced-open");
    }
  });

  // ── Dropdown de usuario ───────────────────────────────────
  const userBtn = document.getElementById("user-btn");
  const userDropdown = document.getElementById("user-dropdown");
  const userChevron = document.getElementById("user-chevron");

  userBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = userDropdown.classList.toggle("open");
    userChevron.style.transform = open ? "rotate(180deg)" : "rotate(0deg)";
  });

  // ── Notificaciones ────────────────────────────────────
  const notifBtn = document.getElementById("notif-btn");
  notifBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleNotifDropdown();
  });

  document.addEventListener("click", () => {
    userDropdown.classList.remove("open");
    userChevron.style.transform = "rotate(0deg)";
    // Cerrar panel notificaciones al click fuera
    const panel = document.getElementById("notif-panel");
    if (panel) panel.style.display = "none";
  });

  /* ── Notificaciones ──────────────────────────────────── */
  const COLORES_NOTIF = {
    DEFICIT: {
      bg: "#fef2f2",
      border: "#fecaca",
      dot: "#e11d48",
      icon: "trending-down",
    },
    EGRESO_GRANDE: {
      bg: "#fff7ed",
      border: "#fed7aa",
      dot: "#f97316",
      icon: "arrow-up-right",
    },
    UMBRAL_MENSUAL: {
      bg: "#fefce8",
      border: "#fde68a",
      dot: "#d97706",
      icon: "alert-triangle",
    },
    DEFAULT: {
      bg: "#f0fdf4",
      border: "#bbf7d0",
      dot: "#10b981",
      icon: "bell",
    },
  };

  let notifCargadas = false;

  window.toggleNotifDropdown = function () {
    const panel = document.getElementById("notif-panel");
    if (!panel) return;
    const visible = panel.style.display === "flex";
    panel.style.display = visible ? "none" : "flex";
    if (!visible && !notifCargadas) cargarNotificaciones();
  };

  async function cargarNotificaciones() {
    const lista = document.getElementById("notif-lista");
    if (!lista) return;

    try {
      const res = await fetch("/notificaciones/json/", {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await res.json();
      notifCargadas = true;

      if (!data.ok || data.notificaciones.length === 0) {
        lista.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;
                  justify-content:center;padding:40px 20px;gap:8px;color:#94a3b8;">
        <i data-lucide="bell-off" style="width:32px;height:32px;"></i>
        <span style="font-size:.82rem;font-weight:500;">Sin notificaciones</span>
      </div>`;
        lucide.createIcons();
        return;
      }

      lista.innerHTML = data.notificaciones
        .map((n) => {
          const c = COLORES_NOTIF[n.tipo] || COLORES_NOTIF.DEFAULT;
          return `
      <div style="display:flex;gap:10px;padding:10px 10px;border-radius:10px;
                  background:${c.bg};border:1px solid ${c.border};
                  margin-bottom:6px;">
        <div style="width:30px;height:30px;border-radius:8px;
                    background:${c.dot}20;color:${c.dot};
                    display:grid;place-items:center;flex-shrink:0;margin-top:1px;">
          <i data-lucide="${c.icon}" style="width:14px;height:14px;"></i>
        </div>
        <div style="min-width:0;">
          <p style="font-size:.8rem;font-weight:700;color:#0f172a;
                    margin:0 0 2px;">${n.titulo}</p>
          <p style="font-size:.75rem;color:#475569;margin:0;
                    line-height:1.4;">${n.descripcion}</p>
          <p style="font-size:.68rem;color:#94a3b8;margin:4px 0 0;">
            ${n.fecha}</p>
        </div>
        ${
          !n.leida
            ? `<span style="width:7px;height:7px;border-radius:50%;
                                   background:${c.dot};flex-shrink:0;
                                   margin-top:4px;"></span>`
            : ""
        }
      </div>`;
        })
        .join("");

      lucide.createIcons();
    } catch (e) {
      lista.innerHTML = `
    <div style="padding:20px;text-align:center;font-size:.8rem;color:#94a3b8;">
      Error al cargar notificaciones
    </div>`;
    }
  }
});

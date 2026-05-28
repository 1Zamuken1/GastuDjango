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

  // Remover la clase de preload para restaurar las transiciones CSS normales
  requestAnimationFrame(() => {
    document.documentElement.classList.remove('sidebar-mini-preload');
  });

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
  document.addEventListener("click", () => {
    userDropdown.classList.remove("open");
    userChevron.style.transform = "rotate(0deg)";
  });

});

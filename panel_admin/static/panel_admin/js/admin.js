/* =============================================================
   admin.js  —  GastuApp Panel Admin
   Ruta: panel_admin/static/panel_admin/js/admin.js
   Responsabilidades:
   - Inicializar Lucide icons
   - Toggle del sidebar (desktop mini / mobile overlay)
   - Restaurar estado del sidebar desde localStorage
   Los handlers de dominio (usuarios, categorias) viven en sus
   propios archivos JS para evitar doble registro de listeners.
   ============================================================= */

document.addEventListener('DOMContentLoaded', () => {

  /* ── Lucide icons ────────────────────────────────────────── */
  lucide.createIcons();

  /* ── Toggle sidebar ──────────────────────────────────────── */
  const toggle   = document.getElementById('sidebar-toggle');
  const body     = document.body;
  const isMobile = () => window.innerWidth < 768;

  if (toggle) {
    toggle.addEventListener('click', () => {
      if (isMobile()) {
        body.classList.toggle('sidebar-open');
      } else {
        body.classList.toggle('sidebar-mini');
        localStorage.setItem(
          'admin-sidebar-mini',
          body.classList.contains('sidebar-mini')
        );
      }
    });
  }

  /* Restaurar estado del sidebar al cargar */
  if (!isMobile() && localStorage.getItem('admin-sidebar-mini') === 'true') {
    body.classList.add('sidebar-mini');
  }

  /* Cerrar sidebar en mobile al hacer click en el overlay */
  document.addEventListener('click', (e) => {
    if (isMobile() && body.classList.contains('sidebar-open')) {
      const sidebar = document.getElementById('admin-sidebar');
      if (sidebar && !sidebar.contains(e.target) && e.target !== toggle) {
        body.classList.remove('sidebar-open');
      }
    }
  });

});
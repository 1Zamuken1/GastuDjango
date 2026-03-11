/* =============================================================
   dashboard.js  —  GastuApp
   Ruta: static/dashboard/js/dashboard.js
   ============================================================= */

document.addEventListener('DOMContentLoaded', () => {

  lucide.createIcons();

  /* ─────────────────────────────────────────────────────────────
     CARRUSEL
     ─────────────────────────────────────────────────────────── */

  const AUTO_DELAY    = 5000;
  const PROGRESS_DUR  = AUTO_DELAY - 150;

  const track   = document.getElementById('carousel-track');
  const progBar = document.getElementById('carousel-progress-bar');
  const btnPrev = document.getElementById('carousel-prev');
  const btnNext = document.getElementById('carousel-next');
  const dots    = Array.from(document.querySelectorAll('.carousel-dot'));

  if (!track) return;

  const slides = Array.from(track.querySelectorAll('.carousel-slide'));

  let current   = 0;
  let autoTimer = null;
  let isPaused  = false;

  /** Cuántas slides son visibles según el ancho actual */
  function visibleCount() {
    const w = window.innerWidth;
    if (w < 768) return 1;
    if (w < 1024) return 2;
    return 3;
  }

  function maxIndex() {
    return Math.max(0, slides.length - visibleCount());
  }

  /** Ancho de un slide + gap */
  function slideWidth() {
    if (!slides[0]) return 0;
    const gap = parseFloat(getComputedStyle(track).gap) || 14;
    return slides[0].getBoundingClientRect().width + gap;
  }

  function goTo(index) {
    current = Math.max(0, Math.min(index, maxIndex()));
    track.style.transform = `translateX(-${current * slideWidth()}px)`;

    // Sincronizar dots
    dots.forEach((d, i) => d.classList.toggle('active', i === current));

    // Reiniciar barra de progreso
    if (progBar) {
      progBar.style.transition = 'none';
      progBar.style.width = '0%';
      // Doble rAF para asegurar que el browser procesa el reset antes de animar
      requestAnimationFrame(() => requestAnimationFrame(() => {
        progBar.style.transition = `width ${PROGRESS_DUR}ms linear`;
        progBar.style.width = '100%';
      }));
    }
  }

  function next() {
    goTo(current >= maxIndex() ? 0 : current + 1);
  }

  function startAuto() {
    stopAuto();
    autoTimer = setInterval(() => { if (!isPaused) next(); }, AUTO_DELAY);
  }

  function stopAuto() {
    clearInterval(autoTimer);
    autoTimer = null;
  }

  // Botones
  btnPrev?.addEventListener('click', () => { goTo(current <= 0 ? maxIndex() : current - 1); startAuto(); });
  btnNext?.addEventListener('click', () => { next(); startAuto(); });

  // Dots
  dots.forEach((dot, i) => {
    dot.addEventListener('click', () => { goTo(i); startAuto(); });
  });

  // Pausa al hover
  const section = track.closest('.carousel-section');
  section?.addEventListener('mouseenter', () => { isPaused = true; });
  section?.addEventListener('mouseleave', () => { isPaused = false; });

  // Teclado
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft')  { goTo(current - 1); startAuto(); }
    if (e.key === 'ArrowRight') { next(); startAuto(); }
  });

  // Drag / swipe (mouse)
  let dragX = 0, dragging = false;
  track.addEventListener('mousedown',  (e) => { dragging = true; dragX = e.clientX; stopAuto(); });
  document.addEventListener('mouseup', (e) => {
    if (!dragging) return;
    dragging = false;
    const delta = e.clientX - dragX;
    if (Math.abs(delta) > 40) delta < 0 ? next() : goTo(current - 1);
    startAuto();
  });

  // Touch / swipe (móvil)
  let touchX = 0;
  track.addEventListener('touchstart', (e) => { touchX = e.touches[0].clientX; stopAuto(); }, { passive: true });
  track.addEventListener('touchend',   (e) => {
    const delta = e.changedTouches[0].clientX - touchX;
    if (Math.abs(delta) > 40) delta < 0 ? next() : goTo(current - 1);
    startAuto();
  }, { passive: true });

  // Recalcular posición en resize
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (current > maxIndex()) current = maxIndex();
      goTo(current);
    }, 100);
  });

  // Inicializar — esperamos un frame para que el DOM esté pintado
  requestAnimationFrame(() => {
    goTo(0);
    startAuto();
  });


  /* ─────────────────────────────────────────────────────────────
     GRÁFICOS APEXCHARTS
     ─────────────────────────────────────────────────────────── */

  const historico = JSON.parse(document.getElementById('data-historico')?.textContent || 'null');
  const pie       = JSON.parse(document.getElementById('data-pie')?.textContent || 'null');

  if (!historico || !pie) return;

  const fontFamily = "'DM Sans', system-ui, sans-serif";
  const formatCOP  = (val) => '$' + new Intl.NumberFormat('es-CO').format(val);

  const axisStyle = { fontSize: '11px', colors: '#94a3b8', fontFamily };

  /* ── Stacked bar — tendencia 6 meses ── */
  const elBar = document.getElementById('chart-tendencia');
  if (elBar) {
    new ApexCharts(elBar, {
      chart: {
        type: 'bar',
        stacked: true,
        height: 260,
        toolbar: { show: false },
        fontFamily,
        animations: { enabled: true, speed: 700, easing: 'easeinout' },
        background: 'transparent',
      },
      series: [
        { name: 'Ingresos', data: historico.ingresos },
        { name: 'Egresos',  data: historico.egresos  },
        { name: 'Ahorros',  data: historico.ahorros  },
      ],
      colors: ['#10b981', '#f97316', '#d97706'],
      xaxis: {
        categories: historico.labels,
        labels: { style: axisStyle },
        axisBorder: { show: false },
        axisTicks:  { show: false },
      },
      yaxis: {
        labels: { style: axisStyle, formatter: formatCOP },
      },
      grid:        { borderColor: '#f1f5f9', strokeDashArray: 4, padding: { left: 4, right: 4 } },
      dataLabels:  { enabled: false },
      plotOptions: { bar: { borderRadius: 5, columnWidth: '50%' } },
      legend: {
        position: 'top',
        horizontalAlign: 'right',
        fontSize: '12px',
        fontFamily,
        markers: { width: 10, height: 10, radius: 3 },
        itemMargin: { horizontal: 8 },
      },
      tooltip: {
        theme: 'light',
        y: { formatter: formatCOP },
      },
    }).render();
  }

  /* ── Pie — distribución de egresos ── */
  const elPie = document.getElementById('chart-pie');
  if (elPie) {
    if (pie.labels.length > 0) {
      new ApexCharts(elPie, {
        chart: {
          type: 'donut',          // donut queda mejor que pie en dashboards
          height: 260,
          toolbar: { show: false },
          fontFamily,
          animations: { enabled: true, speed: 600 },
          background: 'transparent',
        },
        series: pie.valores,
        labels: pie.labels,
        colors: pie.colores,
        plotOptions: {
          pie: {
            donut: {
              size: '60%',
              labels: {
                show: true,
                total: {
                  show: true,
                  label: 'Total egresos',
                  fontSize: '11px',
                  fontFamily,
                  color: '#94a3b8',
                  formatter: (w) => formatCOP(
                    w.globals.seriesTotals.reduce((a, b) => a + b, 0)
                  ),
                },
              },
            },
          },
        },
        legend: {
          position: 'bottom',
          fontSize: '11px',
          fontFamily,
          markers: { width: 10, height: 10, radius: 3 },
          itemMargin: { horizontal: 6, vertical: 3 },
        },
        dataLabels: {
          enabled: true,
          style: { fontSize: '10px', fontFamily },
          formatter: (val) => val.toFixed(0) + '%',
          dropShadow: { enabled: false },
        },
        tooltip: {
          theme: 'light',
          y: { formatter: formatCOP },
        },
        stroke: { width: 2, colors: ['#fff'] },
      }).render();
    } else {
      elPie.innerHTML = `
        <div class="chart-empty">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none"
               stroke="#e2e8f0" stroke-width="1.5" stroke-linecap="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 8v4l3 3"/>
          </svg>
          Sin egresos registrados este mes
        </div>`;
    }
  }

});
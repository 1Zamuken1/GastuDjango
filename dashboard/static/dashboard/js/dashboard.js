/* =============================================================
   dashboard.js  —  GastuApp
   ============================================================= */

document.addEventListener('DOMContentLoaded', () => {

  lucide.createIcons();

  /* ─────────────────────────────────────────────────────────────
     CARRUSEL
     ─────────────────────────────────────────────────────────── */
  const AUTO_DELAY   = 5000;
  const PROGRESS_DUR = AUTO_DELAY - 150;

  const track   = document.getElementById('carousel-track');
  const progBar = document.getElementById('carousel-progress-bar');
  const btnPrev = document.getElementById('carousel-prev');
  const btnNext = document.getElementById('carousel-next');
  const dots    = Array.from(document.querySelectorAll('.carousel-dot'));

  if (!track) return;

  const slides = Array.from(track.querySelectorAll('.carousel-slide'));
  let current = 0, autoTimer = null, isPaused = false;

  function visibleCount() {
    const w = window.innerWidth;
    if (w < 768)  return 1;
    if (w < 1024) return 2;
    return 3;
  }
  function maxIndex()   { return Math.max(0, slides.length - visibleCount()); }
  function slideWidth() {
    if (!slides[0]) return 0;
    const gap = parseFloat(getComputedStyle(track).gap) || 14;
    return slides[0].getBoundingClientRect().width + gap;
  }

  function goTo(index) {
    current = Math.max(0, Math.min(index, maxIndex()));
    track.style.transform = `translateX(-${current * slideWidth()}px)`;
    dots.forEach((d, i) => d.classList.toggle('active', i === current));
    if (progBar) {
      progBar.style.transition = 'none';
      progBar.style.width = '0%';
      requestAnimationFrame(() => requestAnimationFrame(() => {
        progBar.style.transition = `width ${PROGRESS_DUR}ms linear`;
        progBar.style.width = '100%';
      }));
    }
  }

  function next() { goTo(current >= maxIndex() ? 0 : current + 1); }
  function startAuto() { stopAuto(); autoTimer = setInterval(() => { if (!isPaused) next(); }, AUTO_DELAY); }
  function stopAuto()  { clearInterval(autoTimer); autoTimer = null; }

  btnPrev?.addEventListener('click', () => { goTo(current <= 0 ? maxIndex() : current - 1); startAuto(); });
  btnNext?.addEventListener('click', () => { next(); startAuto(); });
  dots.forEach((dot, i) => dot.addEventListener('click', () => { goTo(i); startAuto(); }));

  const section = track.closest('.carousel-section');
  section?.addEventListener('mouseenter', () => { isPaused = true; });
  section?.addEventListener('mouseleave', () => { isPaused = false; });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft')  { goTo(current - 1); startAuto(); }
    if (e.key === 'ArrowRight') { next(); startAuto(); }
  });

  let dragX = 0, dragging = false;
  track.addEventListener('mousedown', (e) => { dragging = true; dragX = e.clientX; stopAuto(); });
  document.addEventListener('mouseup', (e) => {
    if (!dragging) return;
    dragging = false;
    const delta = e.clientX - dragX;
    if (Math.abs(delta) > 40) delta < 0 ? next() : goTo(current - 1);
    startAuto();
  });

  let touchX = 0;
  track.addEventListener('touchstart', (e) => { touchX = e.touches[0].clientX; stopAuto(); }, { passive: true });
  track.addEventListener('touchend',   (e) => {
    const delta = e.changedTouches[0].clientX - touchX;
    if (Math.abs(delta) > 40) delta < 0 ? next() : goTo(current - 1);
    startAuto();
  }, { passive: true });

  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { if (current > maxIndex()) current = maxIndex(); goTo(current); }, 100);
  });

  requestAnimationFrame(() => { goTo(0); startAuto(); });


  /* ─────────────────────────────────────────────────────────────
     CONSTANTES
     ─────────────────────────────────────────────────────────── */
  const fontFamily = "'DM Sans', system-ui, sans-serif";
  const formatCOP  = (val) => '$' + new Intl.NumberFormat('es-CO').format(val);
  const axisStyle  = { fontSize: '11px', colors: '#94a3b8', fontFamily };
  const URL_TENDENCIA = document.getElementById('url-tendencia')?.dataset.url || '/dashboard/tendencia/';


  /* ─────────────────────────────────────────────────────────────
     PIE CHART — distribución de gastos
     ─────────────────────────────────────────────────────────── */
  const pieData = JSON.parse(document.getElementById('data-pie')?.textContent || 'null');
  const elPie   = document.getElementById('chart-pie');

  if (elPie && pieData) {
    if (pieData.labels.length > 0) {
      new ApexCharts(elPie, {
        chart: {
          type: 'pie',
          height: 280,
          toolbar: { show: false },
          fontFamily,
          animations: { enabled: true, speed: 600 },
          background: 'transparent',
        },
        series: pieData.valores,
        labels: pieData.labels,
        colors: pieData.colores,
        legend: {
          position: 'bottom',
          fontSize: '11px',
          fontFamily,
          markers: { width: 10, height: 10, radius: 3 },
          itemMargin: { horizontal: 6, vertical: 3 },
        },
        dataLabels: {
          enabled: true,
          style: { fontSize: '11px', fontFamily, fontWeight: '600' },
          formatter: (val) => val.toFixed(1) + '%',
          dropShadow: { enabled: false },
        },
        tooltip: {
          theme: 'light',
          y: { formatter: formatCOP },
        },
        stroke: { width: 2, colors: ['#fff'] },
        plotOptions: {
          pie: { expandOnClick: true },
        },
      }).render();
    } else {
      elPie.innerHTML = `
        <div class="chart-empty">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none"
               stroke="#e2e8f0" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
          Sin egresos registrados este mes
        </div>`;
    }
  }


  /* ─────────────────────────────────────────────────────────────
     GRÁFICO TENDENCIA — día / semana / mes con fetch dinámico
     ─────────────────────────────────────────────────────────── */
  const elTendencia  = document.getElementById('chart-tendencia');
  const toggleBtns   = document.querySelectorAll('.tendencia-toggle');
  let tendenciaChart = null;
  let cargando       = false;

  function buildTendenciaOptions(labels, ingresos, egresos, granularidad) {
    const isLine = granularidad === 'dia';
    return {
      chart: {
        type: isLine ? 'area' : 'bar',
        height: 270,
        toolbar: { show: false },
        fontFamily,
        animations: { enabled: true, speed: 500, easing: 'easeinout' },
        background: 'transparent',
      },
      series: [
        { name: 'Ingresos', data: ingresos },
        { name: 'Egresos',  data: egresos  },
      ],
      colors: ['#10b981', '#f97316'],
      xaxis: {
        categories: labels,
        labels: { style: axisStyle, rotate: granularidad === 'dia' ? -35 : 0 },
        axisBorder: { show: false },
        axisTicks:  { show: false },
      },
      yaxis: {
        labels: { style: axisStyle, formatter: formatCOP },
      },
      grid: { borderColor: '#f1f5f9', strokeDashArray: 4, padding: { left: 4, right: 4 } },
      dataLabels: { enabled: false },
      ...(isLine ? {
        stroke: { curve: 'smooth', width: 2 },
        fill: {
          type: 'gradient',
          gradient: { shadeIntensity: 1, opacityFrom: 0.25, opacityTo: 0.02, stops: [0, 90] },
        },
        markers: { size: granularidad === 'dia' && labels.length <= 15 ? 4 : 0 },
      } : {
        plotOptions: { bar: { borderRadius: 5, columnWidth: '55%' } },
      }),
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
        shared: true,
        intersect: false,
        y: { formatter: formatCOP },
      },
    };
  }

  async function cargarTendencia(granularidad) {
    if (cargando || !elTendencia) return;
    cargando = true;

    // Estado de carga visual
    toggleBtns.forEach(b => b.disabled = true);

    try {
      const res  = await fetch(`${URL_TENDENCIA}?granularidad=${granularidad}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      const data = await res.json();
      if (!data.ok) return;

      const opts = buildTendenciaOptions(data.labels, data.ingresos, data.egresos, granularidad);

      if (tendenciaChart) {
        tendenciaChart.updateOptions(opts, true, true);
      } else {
        tendenciaChart = new ApexCharts(elTendencia, opts);
        tendenciaChart.render();
      }
    } catch (e) {
      console.error('tendencia error:', e);
    } finally {
      cargando = false;
      toggleBtns.forEach(b => b.disabled = false);
    }
  }

  // Conectar botones de toggle
  toggleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      toggleBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      cargarTendencia(btn.dataset.gran);
    });
  });

  // Carga inicial: vista de día
  cargarTendencia('dia');


  /* ─────────────────────────────────────────────────────────────
     ÚLTIMOS MOVIMIENTOS — filtro por tipo
     ─────────────────────────────────────────────────────────── */
  const filterBtns = document.querySelectorAll('.mov-filter-btn');
  const movRows    = document.querySelectorAll('.mov-row[data-tipo]');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filtro = btn.dataset.filtro; // 'todos' | 'INGRESO' | 'EGRESO'
      movRows.forEach(row => {
        row.style.display =
          filtro === 'todos' || row.dataset.tipo === filtro ? '' : 'none';
      });
    });
  });

});
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
     GRÁFICO TENDENCIA — mes actual, barras apiladas con zoom/pan
     El usuario navega con los controles nativos de ApexCharts.
     Zoom máximo: 7 días. Zoom mínimo: mes completo.
     ─────────────────────────────────────────────────────────── */
  const elTendencia = document.getElementById('chart-tendencia');
  const subtitulo   = document.getElementById('tendencia-subtitulo');
  const mesNombreEl = document.getElementById('mes-nombre-actual');
  const MES_NOMBRE  = mesNombreEl?.dataset.mes || '';
  const ANIO        = mesNombreEl?.dataset.anio || '';

  /* Controles de zoom custom encima del gráfico */
  const zoomControls = document.getElementById('tendencia-zoom-controls');

  async function iniciarTendencia() {
    if (!elTendencia) return;

    let data;
    try {
      const res = await fetch(URL_TENDENCIA, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      data = await res.json();
      if (!data.ok) return;
    } catch (e) {
      console.error('tendencia error:', e);
      return;
    }

    /* Todos los datos del mes — nunca se modifican */
    const labelsTotal   = data.labels;
    const ingresosTotal = data.ingresos;
    const egresosTotal  = data.egresos;
    const totalDias     = data.total_dias;
    const PASO          = 7;   /* salto de zoom = 1 semana */

    /* Ventana actual: índices 0-based sobre labelsTotal */
    let desde = 0;
    let hasta = totalDias - 1;

    let chart = null;

    function buildOpts(labels, ingresos, egresos) {
      return {
        chart: {
          type: 'bar',
          stacked: true,
          height: 270,
          fontFamily,
          animations: { enabled: true, speed: 300, easing: 'easeinout' },
          background: 'transparent',
          toolbar:   { show: false },
          selection:  { enabled: false },
          zoom:       { enabled: false },
        },
        series: [
          { name: 'Ingresos', data: ingresos },
          { name: 'Egresos',  data: egresos  },
        ],
        colors: ['#10b981', '#f97316'],
        xaxis: {
          categories: labels,
          title: {
            text: `${MES_NOMBRE} ${ANIO}`,
            style: { fontSize: '11px', fontWeight: 600, color: '#64748b', fontFamily },
          },
          labels: { style: axisStyle },
          axisBorder: { show: false },
          axisTicks:  { show: false },
        },
        yaxis: {
          labels: { style: axisStyle, formatter: formatCOP },
        },
        grid: { borderColor: '#f1f5f9', strokeDashArray: 4, padding: { left: 4, right: 4 } },
        dataLabels: { enabled: false },
        plotOptions: {
          bar: {
            borderRadius: labels.length <= 10 ? 4 : 2,
            columnWidth:  labels.length <= 7  ? '45%' : labels.length <= 14 ? '60%' : '75%',
          },
        },
        legend: {
          position: 'top', horizontalAlign: 'right',
          fontSize: '12px', fontFamily,
          markers: { width: 10, height: 10, radius: 3 },
          itemMargin: { horizontal: 8 },
        },
        tooltip: {
          theme: 'light', shared: true, intersect: false,
          x: { formatter: (val) => `Día ${val} — ${MES_NOMBRE} ${ANIO}` },
          y: { formatter: formatCOP },
        },
      };
    }

    function renderVista() {
      const labels   = labelsTotal.slice(desde, hasta + 1);
      const ingresos = ingresosTotal.slice(desde, hasta + 1);
      const egresos  = egresosTotal.slice(desde, hasta + 1);

      if (chart) {
        /* Actualizar series y categorías sin destruir el chart */
        chart.updateOptions({ xaxis: { categories: labels } }, false, false);
        chart.updateSeries([
          { name: 'Ingresos', data: ingresos },
          { name: 'Egresos',  data: egresos  },
        ]);
      } else {
        chart = new ApexCharts(elTendencia, buildOpts(labels, ingresos, egresos));
        chart.render();
      }

      sincronizarBotones();
    }

    function sincronizarBotones() {
      const visible = hasta - desde + 1;
      const btnIn    = document.getElementById('btn-zoom-in');
      const btnOut   = document.getElementById('btn-zoom-out');
      const btnReset = document.getElementById('btn-zoom-reset');
      if (btnIn)    btnIn.disabled    = visible <= PASO;
      if (btnOut)   btnOut.disabled   = visible >= totalDias;
      if (btnReset) btnReset.disabled = visible >= totalDias;
    }

    /* Zoom + : reducir ventana 1 semana, centrado */
    function zoomIn() {
      const visible = hasta - desde + 1;
      if (visible <= PASO) return;
      const nuevos = Math.max(PASO, visible - PASO);
      const centro = Math.round((desde + hasta) / 2);
      desde = Math.max(0, centro - Math.floor(nuevos / 2));
      hasta = Math.min(totalDias - 1, desde + nuevos - 1);
      desde = Math.max(0, hasta - nuevos + 1);
      renderVista();
    }

    /* Zoom - : ampliar ventana 1 semana */
    function zoomOut() {
      const visible = hasta - desde + 1;
      if (visible >= totalDias) return;
      const nuevos = Math.min(totalDias, visible + PASO);
      const centro = Math.round((desde + hasta) / 2);
      desde = Math.max(0, centro - Math.floor(nuevos / 2));
      hasta = Math.min(totalDias - 1, desde + nuevos - 1);
      desde = Math.max(0, hasta - nuevos + 1);
      renderVista();
    }

    /* Reset: mes completo */
    function zoomReset() {
      desde = 0;
      hasta = totalDias - 1;
      renderVista();
    }

    /* Pan con arrastre */
    let panDragging = false;
    let panStartX   = 0;
    let panDesde    = 0;

    elTendencia.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      panDragging = true;
      panStartX   = e.clientX;
      panDesde    = desde;
      elTendencia.style.cursor = 'grabbing';
      e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
      if (!panDragging) return;
      const chartW   = elTendencia.getBoundingClientRect().width || 600;
      const visible  = hasta - desde + 1;
      const pxPorDia = chartW / Math.max(visible, 1);
      const delta    = Math.round((panStartX - e.clientX) / pxPorDia);
      if (delta === 0) return;
      const newDesde = Math.max(0, Math.min(totalDias - visible, panDesde + delta));
      if (newDesde === desde) return;
      desde = newDesde;
      hasta = desde + visible - 1;
      renderVista();
    });

    document.addEventListener('mouseup', () => {
      if (!panDragging) return;
      panDragging = false;
      elTendencia.style.cursor = '';
    });

    /* Wheel */
    elTendencia.addEventListener('wheel', (e) => {
      e.preventDefault();
      e.deltaY < 0 ? zoomIn() : zoomOut();
    }, { passive: false });

    /* Conectar botones */
    document.getElementById('btn-zoom-in')?.addEventListener('click', zoomIn);
    document.getElementById('btn-zoom-out')?.addEventListener('click', zoomOut);
    document.getElementById('btn-zoom-reset')?.addEventListener('click', zoomReset);

    /* Render inicial */
    renderVista();

    if (subtitulo) {
      subtitulo.textContent = `${MES_NOMBRE} ${ANIO} · arrastra para navegar`;
    }
  }

  iniciarTendencia();



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
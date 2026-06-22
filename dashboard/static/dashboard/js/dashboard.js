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

  // Excluir slides ocultos (display:none) para que no afecten la navegación ni el conteo
  const slides = Array.from(track.querySelectorAll('.carousel-slide'))
                      .filter(s => s.style.display !== 'none');
  let current = 0, autoTimer = null, isPaused = false;

  function visibleCount() {
    // Mapea exactamente los mismos breakpoints del CSS:
    // ≥1536px → 5 slides, ≥1280px → 4, ≥1024px → 3, ≥768px → 2, <768px → 1
    const w = window.innerWidth;
    if (w < 768)  return 1;
    if (w < 1024) return 2;
    if (w < 1280) return 3;
    if (w < 1536) return 4;
    return 5;
  }
  function maxIndex()   { return Math.max(0, slides.length - visibleCount()); }
  function slideWidth() {
    if (!slides[0]) return 0;
    const gap = parseFloat(getComputedStyle(track).gap) || 14;
    return slides[0].getBoundingClientRect().width + gap;
  }

  // Actualiza qué dots son visibles: solo los que corresponden a posiciones reales
  function updateDots() {
    const max = maxIndex();
    dots.forEach((d, i) => {
      d.style.display = i <= max ? '' : 'none';
      d.classList.toggle('active', i === current);
    });
  }

  function goTo(index) {
    current = Math.max(0, Math.min(index, maxIndex()));
    track.style.transform = `translateX(-${current * slideWidth()}px)`;
    updateDots();
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
  function startAuto() { 
    stopAuto(); 
    autoTimer = setInterval(() => { 
      if (!isPaused && !document.body.classList.contains('tour-active')) next(); 
    }, AUTO_DELAY); 
  }
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

  // Recalcular carrusel y gráficos cuando termina la animación del sidebar
  const appContent = document.getElementById('app-content');
  if (appContent) {
    appContent.addEventListener('transitionend', (e) => {
      if (e.propertyName === 'margin-left') {
        // Reposicionar carrusel al nuevo ancho
        if (current > maxIndex()) current = maxIndex();
        goTo(current);
        // Disparar resize para que ApexCharts redimensione todos los gráficos
        // (pie chart incluido). ApexCharts escucha window 'resize' nativo.
        setTimeout(() => window.dispatchEvent(new Event('resize')), 50);
      }
    });
  }

  requestAnimationFrame(() => { goTo(0); startAuto(); });


  /* ─────────────────────────────────────────────────────────────
     CONSTANTES Y URLS
     ─────────────────────────────────────────────────────────── */
  const fontFamily        = "'DM Sans', system-ui, sans-serif";
  const formatCOP         = (val) => '$' + new Intl.NumberFormat('es-CO').format(val);
  const axisStyle         = { fontSize: '11px', colors: '#94a3b8', fontFamily };
  const URL_TENDENCIA     = document.getElementById('url-tendencia')?.dataset.url    || '/dashboard/tendencia/';
  const URL_DASHBOARD     = document.getElementById('url-dashboard')?.dataset.url    || '/dashboard/';
  const URL_MESES_DISP    = document.getElementById('url-meses-disp')?.dataset.url   || '/dashboard/meses-disponibles/';


  /* ─────────────────────────────────────────────────────────────
     ESTADO DE NAVEGACION
     ─────────────────────────────────────────────────────────── */
  const navEl    = document.getElementById('nav-meses');
  let mesVisto   = parseInt(navEl?.dataset.mes  || new Date().getMonth() + 1);
  let anioVisto  = parseInt(navEl?.dataset.anio || new Date().getFullYear());
  let primerMes  = mesVisto;
  let primerAnio = anioVisto;
  
  // Estado de filtros avanzados
  let currentFiltros = {
    min_monto: document.getElementById('filtro-min-monto')?.value || '',
    max_monto: document.getElementById('filtro-max-monto')?.value || '',
    categoria_id: document.getElementById('filtro-categoria')?.value || '',
    tipo: ''
  };

  const hoy       = new Date();
  const MES_HOY   = hoy.getMonth() + 1;
  const ANIO_HOY  = hoy.getFullYear();

  function esMesActual(mes, anio) {
    return mes === MES_HOY && anio === ANIO_HOY;
  }

  function mesSiguiente(mes, anio) {
    return mes === 12 ? { mes: 1, anio: anio + 1 } : { mes: mes + 1, anio };
  }

  function mesAnterior(mes, anio) {
    return mes === 1 ? { mes: 12, anio: anio - 1 } : { mes: mes - 1, anio };
  }

  function antesDelPrimero(mes, anio) {
    return (anio < primerAnio) || (anio === primerAnio && mes < primerMes);
  }


  /* ─────────────────────────────────────────────────────────────
     PIE CHART — distribución de gastos
     ─────────────────────────────────────────────────────────── */
  const elPie = document.getElementById('chart-pie');
  let pieChartInst = null;

  let pieRendering = false;
  function renderPie(pieData) {
    if (!elPie || pieRendering) return;
    pieRendering = true;

    if (pieChartInst) {
      pieChartInst.destroy();
      pieChartInst = null;
      window.pieChartInst = null;
    }
    elPie.innerHTML = '';

    if (!pieData || pieData.labels.length === 0) {
      elPie.innerHTML = `
        <div class="chart-empty">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none"
               stroke="#e2e8f0" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
          Sin egresos registrados este mes
        </div>`;
      pieRendering = false;
      return;
    }

    pieChartInst = new ApexCharts(elPie, {
      chart: {
        type: 'pie',
        height: window.innerWidth <= 479 ? 220 : window.innerWidth <= 767 ? 240 : 280,
        toolbar:    { show: false },
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
        markers:     { width: 10, height: 10, radius: 3 },
        itemMargin:  { horizontal: 6, vertical: 3 },
      },
      dataLabels: {
        enabled: true,
        style:   { fontSize: '11px', fontFamily, fontWeight: '600' },
        formatter: (val) => val.toFixed(1) + '%',
        dropShadow: { enabled: false },
      },
      tooltip: { theme: 'light', y: { formatter: formatCOP } },
      stroke:  { width: 2, colors: ['#fff'] },
      plotOptions: { pie: { expandOnClick: true } },
    });
    pieChartInst.render();
    window.pieChartInst = pieChartInst;
    pieRendering = false;
  }

  const pieData = JSON.parse(document.getElementById('data-pie')?.textContent || 'null');
  renderPie(pieData);


  /* ─────────────────────────────────────────────────────────────
     GRÁFICO TENDENCIA
     ─────────────────────────────────────────────────────────── */
  const elTendencia = document.getElementById('chart-tendencia');
  const subtitulo   = document.getElementById('tendencia-subtitulo');

  let tendenciaChart  = null;
  let tendenciaAbort  = null;

  async function iniciarTendencia(mes, anio) {
    if (!elTendencia) return;

    if (tendenciaAbort) tendenciaAbort.abort();
    tendenciaAbort = new AbortController();
    const sig = tendenciaAbort.signal;

    if (tendenciaChart) {
      tendenciaChart.destroy();
      tendenciaChart = null;
      window.tendenciaChartInst = null;
      elTendencia.innerHTML = '';
    }

    const MES_NOMBRE = document.getElementById('mes-nombre-actual')?.dataset.mes  || '';
    const ANIO_LABEL = document.getElementById('mes-nombre-actual')?.dataset.anio || '';

    let q = `?mes=${mes}&anio=${anio}`;
    if (currentFiltros.min_monto) q += `&min_monto=${currentFiltros.min_monto}`;
    if (currentFiltros.max_monto) q += `&max_monto=${currentFiltros.max_monto}`;
    if (currentFiltros.categoria_id) q += `&categoria_id=${currentFiltros.categoria_id}`;
    if (currentFiltros.tipo) q += `&tipo=${currentFiltros.tipo}`;

    let data;
    try {
      const res = await fetch(`${URL_TENDENCIA}${q}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      data = await res.json();
      if (!data.ok) return;
    } catch (e) {
      console.error('tendencia error:', e);
      return;
    }

    if (sig.aborted) return;

    if (data.total_dias === 0) {
      elTendencia.innerHTML = `
        <div class="chart-empty">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none"
               stroke="#e2e8f0" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
          Sin movimientos en este período
        </div>`;
      return;
    }

    const labelsTotal   = data.labels;
    const ingresosTotal = data.ingresos;
    const egresosTotal  = data.egresos;
    const ahorrosTotal  = data.ahorros  || [];
    const detalleIng    = data.detalle_ing  || {};
    const detalleEgr    = data.detalle_egr  || {};
    const detalleAhor   = data.detalle_ahor || {};
    const totalDias     = data.total_dias;
    const PASO          = 7;

    let desde = 0;
    let hasta = totalDias - 1;

    // En pantallas de móvil, hacer "zoom" inicial centrado en el último día con datos
    if (window.innerWidth <= 768 && totalDias > 10) {
      // Buscar el último día con datos reales
      let ultimoDiaConDatos = 0;
      for (let i = totalDias - 1; i >= 0; i--) {
        if (ingresosTotal[i] > 0 || egresosTotal[i] > 0 || (ahorrosTotal && ahorrosTotal[i] > 0)) {
          ultimoDiaConDatos = i;
          break;
        }
      }
      // Ventana de 10 días que TERMINA en el último día con datos
      hasta  = Math.min(totalDias - 1, ultimoDiaConDatos + 2); // +2 días de margen visual
      desde  = Math.max(0, hasta - 9);
    }
    let chart = null;

    function buildOpts(labels, ingresos, egresos, ahorros) {
      return {
        chart: {
          type: 'bar', stacked: true,
          height: window.innerWidth <= 479 ? 200 : window.innerWidth <= 767 ? 220 : 270,
          fontFamily,
          animations: { enabled: true, speed: 300, easing: 'easeinout' },
          background: 'transparent',
          toolbar:    { show: false },
          selection:  { enabled: false },
          zoom:       { enabled: false },
        },
        series: [
          { name: 'Ingresos', data: ingresos },
          { name: 'Egresos',  data: egresos  },
          { name: 'Ahorros',  data: ahorros   },
        ],
        colors: ['#10b981', '#e11d48', '#d97706'],
        xaxis: {
          categories: labels,
          title: {
            text:  `${MES_NOMBRE} ${ANIO_LABEL}`,
            style: { fontSize: '11px', fontWeight: 600, color: '#64748b', fontFamily },
          },
          labels:     { style: axisStyle },
          axisBorder: { show: false },
          axisTicks:  { show: false },
        },
        yaxis: { labels: { style: axisStyle, formatter: formatCOP } },
        grid:  { borderColor: '#f1f5f9', strokeDashArray: 4, padding: { left: 4, right: 4 } },
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
          markers:    { width: 10, height: 10, radius: 3 },
          itemMargin: { horizontal: 8 },
        },
        tooltip: {
          theme: 'light',
          shared: true,
          intersect: false,
          x: { formatter: (val) => `Día ${val} — ${MES_NOMBRE} ${ANIO_LABEL}` },
          custom: ({ series, seriesIndex, dataPointIndex, w }) => {
            const dia      = w.globals.labels[dataPointIndex];
            const totalIng  = series[0][dataPointIndex] || 0;
            const totalEgr  = series[1][dataPointIndex] || 0;
            const totalAhor = series[2] ? (series[2][dataPointIndex] || 0) : 0;
            const catIng   = detalleIng[dia]  || [];
            const catEgr   = detalleEgr[dia]  || [];
            const catAhor  = detalleAhor[dia]  || [];

            const fmtNum = (v) => '$' + new Intl.NumberFormat('es-CO').format(Math.round(v));

            const filas = (cats, color) => cats.length === 0 ? '' :
              cats.map(c => `
                <div style="display:flex;justify-content:space-between;gap:1.5rem;
                            padding:.15rem 0;font-size:.72rem;color:#64748b;">
                  <span style="display:flex;align-items:center;gap:.35rem;">
                    <span style="width:6px;height:6px;border-radius:50%;
                                 background:${color};flex-shrink:0;"></span>
                    ${c.nombre}
                  </span>
                  <span style="font-weight:600;color:#334155;">${fmtNum(c.monto)}</span>
                </div>`).join('');

            const seccion = (label, total, color, cats) => `
              <div style="margin-bottom:.5rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;
                            margin-bottom:.3rem;">
                  <span style="display:flex;align-items:center;gap:.4rem;
                               font-size:.75rem;font-weight:700;color:#0f172a;">
                    <span style="width:8px;height:8px;border-radius:2px;
                                 background:${color};flex-shrink:0;"></span>
                    ${label}
                  </span>
                  <span style="font-size:.8rem;font-weight:800;color:#0f172a;">
                    ${fmtNum(total)}
                  </span>
                </div>
                ${filas(cats, color)}
              </div>`;

            const header = `
              <div style="font-size:.72rem;font-weight:700;color:#94a3b8;
                          text-transform:uppercase;letter-spacing:.06em;
                          margin-bottom:.5rem;padding-bottom:.4rem;
                          border-bottom:1px solid #f1f5f9;">
                Día ${dia} &mdash; ${MES_NOMBRE} ${ANIO_LABEL}
              </div>`;

            const body = (totalIng  > 0 ? seccion('Ingresos', totalIng,  '#10b981', catIng)  : '')
                       + (totalEgr  > 0 ? seccion('Egresos',  totalEgr,  '#e11d48', catEgr)  : '')
                       + (totalAhor > 0 ? seccion('Ahorros',  totalAhor, '#d97706', catAhor) : '');

            return `<div style="background:#fff;border:1px solid #e2e8f0;border-radius:.75rem;
                                padding:.75rem 1rem;min-width:200px;max-width:260px;
                                box-shadow:0 8px 24px rgba(0,0,0,.1);
                                font-family:'DM Sans',sans-serif;">
                      ${header}${body}
                    </div>`;
          },
        },
      };
    }

    function renderVista() {
      const labels   = labelsTotal.slice(desde, hasta + 1);
      const ingresos = ingresosTotal.slice(desde, hasta + 1);
      const egresos  = egresosTotal.slice(desde, hasta + 1);
      const ahorros  = ahorrosTotal.slice(desde, hasta + 1);

      if (chart) {
        chart.updateOptions({ xaxis: { categories: labels } }, false, false);
        chart.updateSeries([
          { name: 'Ingresos', data: ingresos },
          { name: 'Egresos',  data: egresos  },
          { name: 'Ahorros',  data: ahorros   },
        ]);
      } else {
        chart = new ApexCharts(elTendencia, buildOpts(labels, ingresos, egresos, ahorros));
        chart.render();
        tendenciaChart = chart;
        window.tendenciaChartInst = chart;
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

    function zoomReset() {
      desde = 0;
      hasta = totalDias - 1;
      renderVista();
    }

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
    }, { signal: sig });

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
    }, { signal: sig });

    document.addEventListener('mouseup', () => {
      if (!panDragging) return;
      panDragging = false;
      elTendencia.style.cursor = '';
    }, { signal: sig });

    elTendencia.addEventListener('wheel', (e) => {
      e.preventDefault();
      e.deltaY < 0 ? zoomIn() : zoomOut();
    }, { passive: false, signal: sig });

    // ── Pan táctil (swipe) en móvil ──────────────────────────
    let touchPanStartX = 0;
    let touchPanDesde  = 0;
    let isTouchPanning = false;

    elTendencia.addEventListener('touchstart', (e) => {
      if (e.touches.length !== 1) return;
      // Si el toque empezó dentro del tooltip, no iniciar pan
      // para que el usuario pueda hacer scroll dentro del modal
      const tooltip = elTendencia.querySelector('.apexcharts-tooltip');
      if (tooltip && tooltip.contains(e.target)) {
        isTouchPanning = false;
        return;
      }
      touchPanStartX = e.touches[0].clientX;
      touchPanDesde  = desde;
      isTouchPanning = true;
    }, { passive: true, signal: sig });

    elTendencia.addEventListener('touchmove', (e) => {
      if (!isTouchPanning || e.touches.length !== 1) return;
      // Si el toque está ahora sobre el tooltip, cancelar el pan
      const tooltip = elTendencia.querySelector('.apexcharts-tooltip');
      if (tooltip && tooltip.contains(e.target)) {
        isTouchPanning = false;
        return;
      }
      const chartW   = elTendencia.getBoundingClientRect().width || 360;
      const visible  = hasta - desde + 1;
      const pxPorDia = chartW / Math.max(visible, 1);
      const delta    = Math.round((touchPanStartX - e.touches[0].clientX) / pxPorDia);
      if (delta === 0) return;
      const newDesde = Math.max(0, Math.min(totalDias - visible, touchPanDesde + delta));
      if (newDesde === desde) return;
      desde = newDesde;
      hasta = desde + visible - 1;
      renderVista();
    }, { passive: true, signal: sig });

    elTendencia.addEventListener('touchend', () => {
      isTouchPanning = false;
    }, { passive: true, signal: sig });
    // ─────────────────────────────────────────────────


    document.getElementById('btn-zoom-in')?.addEventListener('click',    zoomIn,    { signal: sig });
    document.getElementById('btn-zoom-out')?.addEventListener('click',   zoomOut,   { signal: sig });
    document.getElementById('btn-zoom-reset')?.addEventListener('click', zoomReset, { signal: sig });

    renderVista();

    if (subtitulo) {
      subtitulo.textContent = `${MES_NOMBRE} ${ANIO_LABEL} · arrastra para navegar`;
    }
  }


  /* ─────────────────────────────────────────────────────────────
     METAS DE AHORRO — actualización dinámica
     ─────────────────────────────────────────────────────────── */
  function actualizarMetasAhorro(metas) {
    const lista = document.getElementById('metas-ahorro-lista');
    if (!lista) return;

    if (!metas || metas.length === 0) {
      lista.innerHTML = `
        <div class="meta-empty">
          <i data-lucide="piggy-bank" style="width:36px;height:36px;color:#e2e8f0;"></i>
          <p>Sin metas de ahorro activas</p>
        </div>`;
      lucide.createIcons();
      return;
    }

    const filas = metas.map(m => `
      <div class="meta-row">
        <div class="meta-header">
          <div style="display:flex;align-items:center;gap:8px;min-width:0;">
            <span class="meta-dot"></span>
            <div style="min-width:0;">
              <span class="meta-nombre">${m.descripcion}</span>
              <span class="meta-frecuencia">${m.frecuencia}</span>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
            <span class="meta-pct">${m.pct}%</span>
            <span class="meta-monto">${m.acumulado_fmt}</span>
          </div>
        </div>
        <div class="meta-bar-track">
          <div class="meta-bar-fill"
               style="width:0%;"
               data-pct="${m.pct}">
          </div>
        </div>
        <div class="meta-footer">
          <span class="meta-detail">${m.categoria}</span>
          <span class="meta-detail">Meta: ${m.meta_fmt}</span>
        </div>
      </div>`).join('');

    lista.innerHTML = filas;

    /* Animar las barras después de que el DOM esté listo */
    requestAnimationFrame(() => {
      lista.querySelectorAll('.meta-bar-fill').forEach(el => {
        el.style.width = (parseFloat(el.dataset.pct) || 0) + '%';
      });
    });

    lucide.createIcons();
  }

  /* Animar barras en la carga inicial */
requestAnimationFrame(() => {
  document.querySelectorAll('.meta-bar-fill').forEach(el => {
    el.style.width = (parseFloat(el.dataset.pct) || 0) + '%';
  });
});


  /* ─────────────────────────────────────────────────────────────
     NAVEGACION DE MESES
     ─────────────────────────────────────────────────────────── */
  const btnMesActual    = document.getElementById('btn-mes-actual');
  const btnMesAnterior  = document.getElementById('btn-mes-anterior');
  const btnMesSiguiente = document.getElementById('btn-mes-siguiente');
  const navMesLabel     = document.getElementById('nav-mes-label');

  const MESES_ES = {
    1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio',
    7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre',
  };

  function fmt(v) {
    const n = parseFloat(v);
    return '$' + new Intl.NumberFormat('es-CO').format(Math.round(Math.abs(n)));
  }

  function sincronizarNavBotones() {
    const esActual = esMesActual(mesVisto, anioVisto);
    const esPrimero = (anioVisto === primerAnio && mesVisto === primerMes) ||
                      antesDelPrimero(mesAnterior(mesVisto, anioVisto).mes,
                                      mesAnterior(mesVisto, anioVisto).anio);

    if (btnMesActual)    btnMesActual.disabled    = esActual;
    if (btnMesSiguiente) btnMesSiguiente.disabled = esActual;
    if (btnMesAnterior)  btnMesAnterior.disabled  = esPrimero;
    if (navMesLabel)     navMesLabel.textContent  = `${MESES_ES[mesVisto]} ${anioVisto}`;

    const selectMes = document.getElementById('select-mes');
    const selectAnio = document.getElementById('select-anio');
    if (selectMes && selectAnio) {
      selectMes.value = mesVisto;
      selectAnio.value = anioVisto;
    }

    const badge = document.getElementById('nav-mes-historico');
    if (badge) badge.classList.toggle('visible', !esActual);
  }

  function actualizarDOM(data) {
    /* ── Stat cards ── */
    const setVal = (id, v, canBeNegative = false) => {
      const el = document.getElementById(id);
      if (!el) return;
      const n = parseFloat(v);
      el.textContent = fmt(v);
      if (canBeNegative) {
        el.classList.toggle('stat-card__value--negative', n < 0);
        el.classList.remove('stat-card__value--positive');
      }
    };

    setVal('val-total-dinero',      data.total_dinero,       true);
    setVal('val-disponible-global', data.disponible_global,  true);
    setVal('val-ahorro-total', data.ahorro_total);
    setVal('val-ingresos',     data.total_ingresos);
    setVal('val-egresos',      data.total_egresos);
    setVal('val-diferencia',   data.diferencia,  true);
    setVal('val-ahorros-mes',  data.ahorros_mes);

    /* ── Diferencia card: clase y icono ── */
    const cardDif  = document.getElementById('stat-card-diferencia');
    const iconDif  = document.getElementById('icon-diferencia');
    if (cardDif && iconDif) {
      const isPos = parseFloat(data.diferencia) >= 0;
      cardDif.className = `stat-card ${isPos ? 'stat-card--diferencia-pos' : 'stat-card--diferencia-neg'}`;
      iconDif.className  = `icon-box ${isPos ? 'icon-box--emerald' : 'icon-box--red'}`;
      iconDif.innerHTML  = `<i data-lucide="${isPos ? 'plus-circle' : 'minus-circle'}"></i>`;
    }

    /* ── Status badge ── */
    const badge = document.getElementById('status-badge-wrap');
    if (badge) {
      if (data.total_dinero < 0) {
        badge.className = 'status-badge status-badge--deficit';
        badge.innerHTML = '<i data-lucide="alert-triangle"></i> Balance global en déficit';
      } else if (data.hay_deficit) {
        badge.className = 'status-badge status-badge--warning';
        badge.innerHTML = '<i data-lucide="info"></i> Gastos superan ingresos del mes';
      } else {
        badge.className = 'status-badge status-badge--ok';
        badge.innerHTML = '<i data-lucide="check-circle"></i> Finanzas en orden';
      }
    }

    /* ── Subtítulos contextuales ── */
    const mesNombre = data.mes_nombre;
    const anio      = data.anio;

    const subPie = document.getElementById('pie-subtitulo');
    if (subPie) subPie.textContent = `Por categoría — ${mesNombre}`;

    const subMov = document.getElementById('mov-subtitulo');
    if (subMov) subMov.textContent = `${mesNombre} ${anio}`;

    /* ── Quick-add: solo visible en mes actual ── */
    const quickAdd = document.getElementById('mov-quick-add');
    if (quickAdd) quickAdd.classList.toggle('mov-quick-add--visible', data.es_mes_actual);

    /* ── Tabla de movimientos ── */
    const movTabla = document.getElementById('mov-tabla');
    if (movTabla) {
      if (data.ultimos_movimientos.length === 0) {
        const esPasado = antesDelPrimero(data.mes, data.anio);
        const mensajeEmpty = esPasado 
          ? `Período anterior a la creación de tu cuenta. No hay movimientos registrados.`
          : `Sin movimientos en ${mesNombre} ${anio}`;
        movTabla.innerHTML = `
          <div class="mov-empty">
            <i data-lucide="inbox" style="width:40px;height:40px;color:#e2e8f0;"></i>
            <p>${mensajeEmpty}</p>
          </div>`;
      } else {
        const header = `
          <div class="mov-table-header">
            <span class="mov-table-label">Descripción</span>
            <span class="mov-table-label">Categoría</span>
            <span class="mov-table-label">Fecha</span>
            <span class="mov-table-label mov-table-label--right">Monto</span>
          </div>`;

        const rows = data.ultimos_movimientos.map(m => {
          const esI    = m.tipo === 'INGRESO';
          const esA    = m.tipo === 'AHORRO';
          const dotCls = esI ? 'mov-dot--income' : esA ? 'mov-dot--saving' : 'mov-dot--expense';
          const amtCls = esI ? 'mov-amount--income' : esA ? 'mov-amount--saving' : 'mov-amount--expense';
          const signo  = esI ? '+' : esA ? '↗' : '−';
          const label  = esI ? 'Ingreso' : esA ? 'Ahorro' : 'Egreso';
          const montoF = '$' + new Intl.NumberFormat('es-CO').format(Math.round(parseFloat(m.monto)));
          return `
            <div class="mov-row" data-tipo="${m.tipo}">
              <div style="display:flex;align-items:flex-start;gap:8px;min-width:0;">
                <div class="mov-dot ${dotCls}"></div>
                <div style="min-width:0;">
                  <p class="mov-desc">${m.descripcion}</p>
                  <p class="mov-type">${label}</p>
                </div>
              </div>
              <div class="mov-cat">${m.categoria}</div>
              <div class="mov-date">${m.fecha}</div>
              <div class="mov-amount ${amtCls}">${signo}${montoF}</div>
            </div>`;
        }).join('');

        movTabla.innerHTML = header + rows;
      }
    }

    /* ── Metas de ahorro ── */
    const metasCard = document.getElementById('metas-ahorro-card');
    if (metasCard) metasCard.style.display = data.tiene_filtros ? 'none' : 'block';
    actualizarMetasAhorro(data.metas_ahorro_activas || []);

    /* ── Pie chart ── */
    renderPie(data.pie_data);

    /* Recrear iconos Lucide en nuevo HTML */
    lucide.createIcons();

    /* ── Sincronizar botones locales de tabla ── */
    const isGlobalFilterActive = !!currentFiltros.tipo;
    document.querySelectorAll('.mov-filter-btn').forEach(b => {
      b.disabled = isGlobalFilterActive;
      b.style.opacity = isGlobalFilterActive ? '0.5' : '1';
      b.style.cursor = isGlobalFilterActive ? 'not-allowed' : 'pointer';
      // Reset visual state if disabled
      if (isGlobalFilterActive) {
        b.classList.toggle('active', b.dataset.filtro === 'todos');
      }
    });
  }

  /* ── Exportación con Gráficos ── */
  async function exportarDatos(e, url) {
    e.preventDefault();
    if (e.currentTarget.dataset.empty === 'true') {
      window.GastuAlerts.error('Sin datos', 'No hay movimientos para exportar en este período.');
      return;
    }

    let imgTendencia = '';
    let imgPie = '';

    // Capturar gráfico de Tendencia
    try {
      if (window.tendenciaChartInst) {
        const tUri = await window.tendenciaChartInst.dataURI({ scale: 2 });
        imgTendencia = tUri.imgURI || '';
        console.log('Tendencia capturada:', imgTendencia ? 'OK' : 'vacía');
      } else {
        console.warn('tendenciaChartInst no encontrado en window');
      }
    } catch (err) {
      console.warn('Error capturando tendencia:', err);
    }

    // Capturar gráfico Pie
    try {
      if (window.pieChartInst) {
        const pUri = await window.pieChartInst.dataURI({ scale: 2 });
        imgPie = pUri.imgURI || '';
        console.log('Pie capturado:', imgPie ? 'OK' : 'vacío');
      } else {
        console.warn('pieChartInst no encontrado en window');
      }
    } catch (err) {
      console.warn('Error capturando pie:', err);
    }

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = url;
    form.style.display = 'none';

    // CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    if (csrfToken) {
      const csrfInput = document.createElement('input');
      csrfInput.name = 'csrfmiddlewaretoken';
      csrfInput.value = csrfToken;
      form.appendChild(csrfInput);
    }

    const payload = {
      mes: mesVisto,
      anio: anioVisto,
      min_monto: currentFiltros.min_monto,
      max_monto: currentFiltros.max_monto,
      categoria_id: currentFiltros.categoria_id,
      tipo: currentFiltros.tipo || '',
      img_tendencia: imgTendencia,
      img_pie: imgPie
    };

    for (const [k, v] of Object.entries(payload)) {
      if (v) {
        const inp = document.createElement('input');
        inp.type = 'hidden';
        inp.name = k;
        inp.value = v;
        form.appendChild(inp);
      }
    }

    document.body.appendChild(form);
    form.submit();
    setTimeout(() => form.remove(), 1000);
  }

  document.getElementById('btn-export-excel')?.addEventListener('click', (e) => {
    exportarDatos(e, '/dashboard/exportar/excel/');
  });
  
  document.getElementById('btn-export-pdf')?.addEventListener('click', (e) => {
    exportarDatos(e, '/dashboard/exportar/pdf/');
  });

  let navegarAbort = null;
  async function navegar(mes, anio) {
    if (navegarAbort) navegarAbort.abort();
    navegarAbort = new AbortController();
    const sig = navegarAbort.signal;

    mesVisto  = mes;
    anioVisto = anio;

    let q = `?mes=${mes}&anio=${anio}`;
    if (currentFiltros.min_monto) q += `&min_monto=${currentFiltros.min_monto}`;
    if (currentFiltros.max_monto) q += `&max_monto=${currentFiltros.max_monto}`;
    if (currentFiltros.categoria_id) q += `&categoria_id=${currentFiltros.categoria_id}`;
    if (currentFiltros.tipo) q += `&tipo=${currentFiltros.tipo}`;

    const url = `${URL_DASHBOARD}${q}`;
    history.pushState({ mes, anio, filtros: {...currentFiltros} }, '', url);

    const mesNombreSpan = document.getElementById('mes-nombre-actual');
    if (mesNombreSpan) {
      mesNombreSpan.dataset.mes  = MESES_ES[mes] || '';
      mesNombreSpan.dataset.anio = String(anio);
    }

    sincronizarNavBotones();

    try {
      const res = await fetch(`${URL_DASHBOARD}${q}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        signal: sig
      });
      const data = await res.json();
      if (sig.aborted) return;
      if (data.ok) actualizarDOM(data);
    } catch (e) {
      if (e.name !== 'AbortError') console.error('navegar error:', e);
    }

    try {
      if (!sig.aborted) await iniciarTendencia(mes, anio);
    } catch (e) {
      console.error('tendencia error:', e);
    }
  }

  btnMesActual?.addEventListener('click', () => {
    navegar(MES_HOY, ANIO_HOY);
  });

  btnMesAnterior?.addEventListener('click', () => {
    const { mes, anio } = mesAnterior(mesVisto, anioVisto);
    if (!antesDelPrimero(mes, anio)) navegar(mes, anio);
  });

  btnMesSiguiente?.addEventListener('click', () => {
    if (!esMesActual(mesVisto, anioVisto)) {
      const { mes, anio } = mesSiguiente(mesVisto, anioVisto);
      navegar(mes, anio);
    }
  });

  const selectMes = document.getElementById('select-mes');
  const selectAnio = document.getElementById('select-anio');
  const btnFiltrarPeriodo = document.getElementById('btn-filtrar-periodo');

  btnFiltrarPeriodo?.addEventListener('click', () => {
    if (selectMes && selectAnio) {
      const mesVal = parseInt(selectMes.value);
      const anioVal = parseInt(selectAnio.value);

      if (antesDelPrimero(mesVal, anioVal)) {
        if (window.GastuAlerts) {
          window.GastuAlerts.info('Información', 'El período seleccionado es anterior a la creación de tu cuenta.');
        }
      }
      navegar(mesVal, anioVal);
    }
  });

  window.addEventListener('popstate', (e) => {
    const state = e.state;
    if (state && state.mes && state.anio) {
      mesVisto  = state.mes;
      anioVisto = state.anio;
      if (state.filtros) currentFiltros = state.filtros;
      navegar(state.mes, state.anio);
    } else {
      navegar(MES_HOY, ANIO_HOY);
    }
  });

  async function initPrimerMes() {
    try {
      const res  = await fetch(URL_MESES_DISP, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      const data = await res.json();
      if (data.ok) {
        primerMes  = data.primer_mes;
        primerAnio = data.primer_anio;
      }
    } catch (e) {
      console.error('meses-disponibles error:', e);
    }
    sincronizarNavBotones();
  }


  /* ─────────────────────────────────────────────────────────────
     ÚLTIMOS MOVIMIENTOS — filtro por tipo (event delegation)
     ─────────────────────────────────────────────────────────── */
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.mov-filter-btn');
    if (!btn) return;

    const filtro = btn.dataset.filtro;

    // Sync ALL local filter buttons with the same value
    document.querySelectorAll('.mov-filter-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.filtro === filtro);
    });

    // Client-side filter: show/hide rows
    document.querySelectorAll('.mov-row[data-tipo]').forEach(row => {
      row.style.display = (filtro === 'todos' || row.dataset.tipo === filtro) ? '' : 'none';
    });
  });

  /* ─────────────────────────────────────────────────────────────
     FILTROS GLOBALES — filtro por tipo (event delegation)
     ─────────────────────────────────────────────────────────── */
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.global-filter-btn');
    if (!btn) return;

    const filtro = btn.dataset.filtro;

    document.querySelectorAll('.global-filter-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.filtro === filtro);
    });

    currentFiltros.tipo = filtro;
    
    const badge = document.getElementById('badge-filtros-activos');
    const tieneFiltros = currentFiltros.min_monto || currentFiltros.max_monto || currentFiltros.categoria_id || currentFiltros.tipo;
    if (badge) badge.classList.toggle('filtros-badge--visible', tieneFiltros);
    
    navegar(mesVisto, anioVisto);
  });

  /* ─────────────────────────────────────────────────────────────
     FILTROS AVANZADOS — Panel y formulario
     ─────────────────────────────────────────────────────────── */
  function bindFiltrosAvanzados() {
    const btnToggle = document.getElementById('btn-toggle-filtros');
    const panel = document.getElementById('panel-filtros-avanzados');
    const form = document.getElementById('form-filtros-avanzados');
    const btnLimpiar = document.getElementById('btn-limpiar-filtros');
    const btnLimpiarBadge = document.getElementById('btn-limpiar-filtros-badge');
    const badge = document.getElementById('badge-filtros-activos');
    const preconfigBtns = document.querySelectorAll('.btn-preconfig');

    if (btnToggle && panel) {
      btnToggle.addEventListener('click', () => {
        panel.classList.toggle('filtros-panel--open');
        btnToggle.classList.toggle('active');
      });
    }

    function aplicarFiltrosAvanzados() {
      currentFiltros.min_monto = document.getElementById('filtro-min-monto').value;
      currentFiltros.max_monto = document.getElementById('filtro-max-monto').value;
      currentFiltros.categoria_id = document.getElementById('filtro-categoria').value;
      
      const tieneFiltros = currentFiltros.min_monto || currentFiltros.max_monto || currentFiltros.categoria_id || currentFiltros.tipo;
      if (badge) badge.classList.toggle('filtros-badge--visible', tieneFiltros);
      
      navegar(mesVisto, anioVisto);
    }

    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        aplicarFiltrosAvanzados();
      });
    }

    const limpiarFiltros = (e) => {
      if (e) e.preventDefault();
      if (form) form.reset();
      currentFiltros = { min_monto: '', max_monto: '', categoria_id: '', tipo: '' };
      
      // Limpiar picker de categoría visualmente
      document.getElementById('filtro-cat-label').textContent = 'Todas las categorías';
      document.querySelectorAll('#modal-picker-cat-dash .picker-cat-card').forEach(c => c.classList.remove('selected'));
      const catTodas = document.querySelector('#modal-picker-cat-dash .picker-cat-card[data-id=""]');
      if (catTodas) catTodas.classList.add('selected');

      const filterBtns = document.querySelectorAll('.mov-filter-btn');
      filterBtns.forEach(b => b.classList.toggle('active', b.dataset.filtro === 'todos'));

      const globalBtns = document.querySelectorAll('.global-filter-btn');
      globalBtns.forEach(b => b.classList.toggle('active', b.dataset.filtro === ''));

      // Reset row visibility (client-side filter was showing/hiding rows)
      document.querySelectorAll('.mov-row[data-tipo]').forEach(row => {
        row.style.display = '';
      });
      
      if (badge) badge.classList.remove('filtros-badge--visible');
      if (panel) panel.classList.remove('filtros-panel--open');
      if (btnToggle) btnToggle.classList.remove('active');
      
      navegar(mesVisto, anioVisto);
    };

    if (btnLimpiar) btnLimpiar.addEventListener('click', limpiarFiltros);
    if (btnLimpiarBadge) btnLimpiarBadge.addEventListener('click', limpiarFiltros);

    preconfigBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        document.getElementById('filtro-min-monto').value = btn.dataset.min || '';
        document.getElementById('filtro-max-monto').value = btn.dataset.max || '';
        document.getElementById('filtro-categoria').value = '';
        currentFiltros.tipo = btn.dataset.tipo || '';
        
        document.getElementById('filtro-cat-label').textContent = 'Todas las categorías';
        
        const filterBtns = document.querySelectorAll('.mov-filter-btn');
        filterBtns.forEach(b => b.classList.toggle('active', b.dataset.filtro === currentFiltros.tipo));
        
        aplicarFiltrosAvanzados();
      });
    });

    // ── Lógica Picker de Categorías Modal ──
    const btnAbrirPicker = document.getElementById('btn-abrir-picker-cat');
    const modalPicker    = document.getElementById('modal-picker-cat-dash');
    const btnCerrarPicker= document.getElementById('btn-cerrar-picker-cat');
    const pickerCards    = document.querySelectorAll('#modal-picker-cat-dash .picker-cat-card');
    const searchInput    = document.getElementById('picker-cat-buscar');
    const tipoBtns       = document.querySelectorAll('.picker-cat-tipo-btn');

    if (btnAbrirPicker && modalPicker) {
      btnAbrirPicker.addEventListener('click', () => {
        modalPicker.hidden = false;
        if (searchInput) {
          searchInput.value = '';
          searchInput.dispatchEvent(new Event('input'));
          setTimeout(() => searchInput.focus(), 50);
        }
      });
    }

    if (btnCerrarPicker && modalPicker) {
      btnCerrarPicker.addEventListener('click', () => {
        modalPicker.hidden = true;
      });
    }

    // Cerrar modal al clickear fuera
    if (modalPicker) {
      modalPicker.addEventListener('click', (e) => {
        if (e.target === modalPicker) modalPicker.hidden = true;
      });
    }

    pickerCards.forEach(card => {
      card.addEventListener('click', () => {
        const id = card.dataset.id;
        const nombre = card.dataset.nombre;
        
        document.getElementById('filtro-categoria').value = id;
        document.getElementById('filtro-cat-label').textContent = nombre;
        
        pickerCards.forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        
        if (modalPicker) modalPicker.hidden = true;
      });
    });

    // Búsqueda en el picker
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        pickerCards.forEach(card => {
          if (!card.dataset.id) return; // 'Todas' card
          const nombre = card.dataset.nombre.toLowerCase();
          const visibleTipo = card.style.display !== 'none' || !card.hasAttribute('data-filtered-tipo');
          
          if (nombre.includes(term)) {
            if (!card.hasAttribute('data-filtered-tipo')) card.style.display = 'flex';
          } else {
            card.style.display = 'none';
          }
        });
      });
    }

    // Filtros por tipo en el picker
    tipoBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        tipoBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const tipo = btn.dataset.tipo;
        
        pickerCards.forEach(card => {
          if (!card.dataset.id) return; // 'Todas' card
          if (!tipo || card.dataset.tipo === tipo) {
            card.removeAttribute('data-filtered-tipo');
            card.style.display = 'flex';
          } else {
            card.setAttribute('data-filtered-tipo', 'true');
            card.style.display = 'none';
          }
        });
        
        if (searchInput) searchInput.dispatchEvent(new Event('input')); // re-aplicar búsqueda
      });
    });
  }


  /* ─────────────────────────────────────────────────────────────
     ARRANQUE
     ─────────────────────────────────────────────────────────── */
  initPrimerMes();
  iniciarTendencia(mesVisto, anioVisto);
  bindFiltrosAvanzados();

});
'use strict';
/* ═══════════════════════════════════════════════════════
   egresos.js — Instancia de GestorMovimientos para Egresos
   + Lógica exclusiva de alertas de presupuesto
   ═══════════════════════════════════════════════════════ */
const appEgresos = new GestorMovimientos({
  tipo:       'EGRESO',
  tipoLabel:  'egreso',
  color:      '#e11d48',
  montoClass: 'monto--egreso',
  dpAcento:   { acento: 'egreso' },
  onPostSave: (catId) => checkAlertasPresupuesto(catId),
});

/* ── Alertas de presupuesto al insertar egreso ───────── */
const ALERTA_CONFIGS = {
  nivel_50: { color: '#facc15', titulo: 'Presupuesto al 50%' },
  nivel_55: { color: '#facc15', titulo: 'Presupuesto al 55%' },
  nivel_60: { color: '#fb923c', titulo: 'Presupuesto al 60%' },
  nivel_65: { color: '#fb923c', titulo: 'Presupuesto al 65%' },
  nivel_70: { color: '#f97316', titulo: 'Presupuesto al 70%' },
  nivel_75: { color: '#f97316', titulo: 'Presupuesto al 75%' },
  nivel_80: { color: '#f97316', titulo: 'Presupuesto al 80%' },
  nivel_85: { color: '#ef4444', titulo: 'Presupuesto al 85%' },
  nivel_90: { color: '#ef4444', titulo: 'Presupuesto al 90%' },
  nivel_95: { color: '#ef4444', titulo: 'Presupuesto al 95%' },
  critica:  { color: '#b91c1c', titulo: '¡Límite superado!' },
};

function alertaPresupuestoYaVista(presupuestoId, nivel) {
  return !!localStorage.getItem(`alerta_vista_${presupuestoId}_${nivel}`);
}

function marcarAlertaPresupuestoVista(presupuestoId, nivel) {
  ['baja','nivel_50','nivel_55','nivel_60','nivel_65','nivel_70',
   'nivel_75','nivel_80','nivel_85','nivel_90','nivel_95','critica'].forEach(n => {
    localStorage.removeItem(`alerta_vista_${presupuestoId}_${n}`);
  });
  localStorage.setItem(`alerta_vista_${presupuestoId}_${nivel}`, '1');
}

function mostrarModalAlertaPresupuesto(alerta) {
  const cfg = ALERTA_CONFIGS[alerta.alerta];
  if (!cfg) return;

  document.getElementById('modal-alerta-presupuesto')?.remove();

  const modal = document.createElement('div');
  modal.id = 'modal-alerta-presupuesto';
  modal.style.cssText = `
    position:fixed; bottom:24px; right:24px; z-index:99999;
    width:min(340px,92vw); background:#fff; border-radius:12px;
    box-shadow:0 8px 32px rgba(0,0,0,0.18);
    border-left:5px solid ${cfg.color};
    padding:16px 18px 14px 16px;
    display:flex; flex-direction:column; gap:6px;
    animation:slideInRight .3s ease;
  `;
  modal.innerHTML = `
    <style>
      @keyframes slideInRight {
        from { transform:translateX(110%); opacity:0; }
        to   { transform:translateX(0);   opacity:1; }
      }
    </style>
    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
      <span style="font-size:1rem;font-weight:700;color:#0f172a;">
        ${cfg.titulo}
      </span>
      <button id="btn-cerrar-alerta-presupuesto"
              style="background:none;border:none;cursor:pointer;color:#94a3b8;font-size:1.1rem;line-height:1;padding:0 2px;">✕</button>
    </div>
    <p style="margin:0;font-size:.85rem;color:#334155;line-height:1.45;">
      Llevas <strong>${alerta.porcentaje}%</strong> del presupuesto
      en <strong>"${alerta.categoria}"</strong>.
    </p>
    <div style="background:#f1f5f9;border-radius:6px;height:6px;margin-top:4px;">
      <div style="width:${Math.min(alerta.porcentaje,100)}%;background:${cfg.color};height:6px;border-radius:6px;"></div>
    </div>
    <p style="margin:0;font-size:.75rem;color:#94a3b8;text-align:right;">
      $${alerta.gastado.toLocaleString('es-CO')} / $${alerta.limite.toLocaleString('es-CO')}
    </p>
  `;
  document.body.appendChild(modal);

  const cerrar = () => {
    modal.style.transition = 'all .25s ease';
    modal.style.opacity    = '0';
    modal.style.transform  = 'translateX(110%)';
    setTimeout(() => modal.remove(), 260);
  };
  document.getElementById('btn-cerrar-alerta-presupuesto').addEventListener('click', cerrar);
  setTimeout(cerrar, 7000);
}

async function checkAlertasPresupuesto(categoriaId) {
  try {
    const res = await fetch('/api/presupuestos/alertas/', {
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': CSRF_TOKEN }
    });
    const data = await res.json();

    const filtradas = (data.alertas || []).filter(a => {
      return String(a.categoria_id) === String(categoriaId) && a.alerta !== 'baja';
    });

    filtradas.forEach(alerta => {
      if (alertaPresupuestoYaVista(alerta.id, alerta.alerta)) return;
      mostrarModalAlertaPresupuesto(alerta);
      marcarAlertaPresupuestoVista(alerta.id, alerta.alerta);
    });
  } catch (e) {
    console.error('checkAlertasPresupuesto ERROR:', e);
  }
}
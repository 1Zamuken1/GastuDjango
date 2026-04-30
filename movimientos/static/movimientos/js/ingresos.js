'use strict';
/* ═══════════════════════════════════════════════════════
   ingresos.js — Instancia de GestorMovimientos para Ingresos
   ═══════════════════════════════════════════════════════ */
const appIngresos = new GestorMovimientos({
  tipo:       'INGRESO',
  tipoLabel:  'ingreso',
  color:      '#10b981',
  montoClass: 'monto--ingreso',
});
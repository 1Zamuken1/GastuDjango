/**
 * gastu_planificacion.js
 * Utilidades compartidas por Presupuestos y Programaciones:
 * llamadas a la API, formato de montos y fechas, escape de HTML,
 * modales, campos de monto y datepickers.
 *
 * Expone window.GastuPlan.
 */
'use strict';

(function () {
  const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

  function csrf() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  /** Une los mensajes de error de DRF en un texto legible, sin nombres de campo. */
  function mensajeDeError(data) {
    if (!data) return 'No se pudo completar la acción.';
    if (typeof data === 'string') return data;
    if (data.error) return data.error;
    if (data.detail) return data.detail;
    const mensajes = Object.values(data).flat().filter(m => typeof m === 'string');
    return mensajes.length ? mensajes.join(' ') : 'No se pudo completar la acción.';
  }

  /** fetch con sesión y CSRF. Lanza Error con un mensaje apto para el usuario. */
  async function api(url, opciones = {}) {
    const metodo = (opciones.method || 'GET').toUpperCase();
    const headers = { 'X-Requested-With': 'XMLHttpRequest' };
    if (metodo !== 'GET') headers['X-CSRFToken'] = csrf();
    if (opciones.body !== undefined) headers['Content-Type'] = 'application/json';

    let respuesta;
    try {
      respuesta = await fetch(url, {
        method: metodo,
        headers,
        credentials: 'same-origin',
        body: opciones.body !== undefined ? JSON.stringify(opciones.body) : undefined,
      });
    } catch (e) {
      throw new Error('No se pudo conectar con el servidor.');
    }
    if (respuesta.status === 204) return null;
    let data = null;
    try { data = await respuesta.json(); } catch (e) { data = null; }
    if (!respuesta.ok) throw new Error(mensajeDeError(data));
    return data;
  }

  function esc(valor) {
    return String(valor ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatMonto(valor) {
    const numero = Number(valor) || 0;
    return numero.toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 });
  }

  /** Convierte 'AAAA-MM-DD' en Date local (sin desfase de zona horaria). */
  function parseISO(iso) {
    if (!iso) return null;
    const [y, m, d] = iso.split('-').map(Number);
    return new Date(y, m - 1, d);
  }

  function hoyISO() {
    const h = new Date();
    return aISO(h);
  }

  function aISO(fecha) {
    const y = fecha.getFullYear();
    const m = String(fecha.getMonth() + 1).padStart(2, '0');
    const d = String(fecha.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  /** 'AAAA-MM-DD' -> '15 nov 2026' (o '15 nov' si es del año en curso y corto=true). */
  function formatFecha(iso, corto = false) {
    const f = parseISO(iso);
    if (!f) return '';
    const base = `${f.getDate()} ${MESES_CORTOS[f.getMonth()]}`;
    if (corto && f.getFullYear() === new Date().getFullYear()) return base;
    return `${base} ${f.getFullYear()}`;
  }

  /** Días desde hoy hasta la fecha (negativo si ya pasó). */
  function diasHasta(iso) {
    const f = parseISO(iso);
    if (!f) return null;
    const hoy = parseISO(hoyISO());
    return Math.round((f - hoy) / 86400000);
  }

  function textoRelativo(iso) {
    const dias = diasHasta(iso);
    if (dias === null) return '';
    if (dias === 0) return 'hoy';
    if (dias === 1) return 'mañana';
    if (dias === -1) return 'ayer';
    if (dias > 1) return `en ${dias} días`;
    return `hace ${Math.abs(dias)} días`;
  }

  function plural(n, singular, pluralTxt) {
    return `${n} ${n === 1 ? singular : pluralTxt}`;
  }

  /* ── Modales ─────────────────────────────────────────────── */
  function abrirModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
    if (window.lucide) window.lucide.createIcons();
  }

  function cerrarModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.hidden = true;
    if (!document.querySelector('.plan-modulo .modal-overlay:not([hidden])')) {
      document.body.style.overflow = '';
    }
  }

  /** Cierra con clic en el fondo, con Escape y con cualquier [data-cerrar-modal]. */
  function initModales(raiz = document) {
    raiz.querySelectorAll('.plan-modulo .modal-overlay').forEach(overlay => {
      overlay.addEventListener('mousedown', e => {
        if (e.target === overlay && overlay.dataset.bloqueado !== 'true') cerrarModal(overlay.id);
      });
    });
    raiz.querySelectorAll('[data-cerrar-modal]').forEach(btn => {
      btn.addEventListener('click', () => cerrarModal(btn.dataset.cerrarModal));
    });
    document.addEventListener('keydown', e => {
      if (e.key !== 'Escape') return;
      const abiertos = [...document.querySelectorAll('.plan-modulo .modal-overlay:not([hidden])')];
      const ultimo = abiertos[abiertos.length - 1];
      if (ultimo && ultimo.dataset.bloqueado !== 'true') cerrarModal(ultimo.id);
    });
  }

  /* ── Campo de monto con separador de miles ───────────────── */
  function initMonto(input, alCambiar) {
    if (!input) return;
    input.addEventListener('input', () => {
      const digitos = input.value.replace(/\D/g, '').replace(/^0+/, '');
      input.dataset.raw = digitos;
      input.value = digitos ? digitos.replace(/\B(?=(\d{3})+(?!\d))/g, '.') : '';
      if (alCambiar) alCambiar(leerMonto(input));
    });
  }

  function leerMonto(input) {
    return input && input.dataset.raw ? parseInt(input.dataset.raw, 10) : 0;
  }

  function setMonto(input, valor) {
    const digitos = valor ? String(Math.round(Number(valor))) : '';
    input.dataset.raw = digitos;
    input.value = digitos ? digitos.replace(/\B(?=(\d{3})+(?!\d))/g, '.') : '';
  }

  /* ── Datepicker ──────────────────────────────────────────── */
  function crearDatepicker(input, onChange, opciones = {}) {
    if (!input || typeof MiniDatepicker === 'undefined') return null;
    const dp = new MiniDatepicker(input, { ...opciones, onChange });
    input.parentNode.appendChild(dp.wrapper);
    return dp;
  }

  /* ── Confirmación de borrado ─────────────────────────────── */
  async function confirmarEliminar(titulo, texto) {
    if (typeof Swal === 'undefined') return window.confirm(texto);
    const base = window.GastuAlerts ? window.GastuAlerts._baseModal : {};
    const resultado = await Swal.fire({
      ...base,
      title: titulo,
      text: texto,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#ef4444',
      reverseButtons: true,
    });
    return resultado.isConfirmed;
  }

  function toast(mensaje, tipo = 'success') {
    const alertas = window.GastuAlerts;
    if (!alertas) return;
    if (tipo === 'error') alertas.toastError(mensaje);
    else if (tipo === 'info') alertas.toastInfo(mensaje);
    else alertas.toastSuccess(mensaje);
  }

  function iconos() {
    if (window.lucide) window.lucide.createIcons();
  }

  /* ── Almacenamiento por pestaña (tolerante a errores) ────── */
  function leerSesion(clave) {
    try { return window.sessionStorage.getItem(clave); } catch (e) { return null; }
  }
  function guardarSesion(clave, valor) {
    try { window.sessionStorage.setItem(clave, valor); } catch (e) { /* sin almacenamiento */ }
  }

  window.GastuPlan = {
    api, esc, formatMonto, formatFecha, parseISO, aISO, hoyISO, diasHasta, textoRelativo, plural,
    abrirModal, cerrarModal, initModales, initMonto, leerMonto, setMonto, crearDatepicker,
    confirmarEliminar, toast, iconos, leerSesion, guardarSesion,
  };
})();

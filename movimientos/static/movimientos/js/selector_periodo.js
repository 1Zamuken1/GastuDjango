/**
 * selector_periodo.js — Selector de mes y año de Ingresos y Egresos.
 *
 * Lee el periodo actual de #select-mes / #select-anio (con data-primer-mes y
 * data-primer-anio) y recarga la pagina con ?mes=&anio= al elegir. Solo ofrece
 * meses entre el primer registro del usuario y hoy. Tambien cierra el menu
 * "Descargar" al elegir un formato o al hacer clic fuera.
 */
(function () {
  "use strict";

  var MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
               "Septiembre", "Octubre", "Noviembre", "Diciembre"];

  function iniciarSelector() {
    var selectMes = document.getElementById("select-mes");
    var selectAnio = document.getElementById("select-anio");
    if (!selectMes || !selectAnio) return;

    var btnMes = document.getElementById("btn-custom-mes");
    var btnAnio = document.getElementById("btn-custom-anio");
    var labelMes = document.getElementById("label-mes");
    var labelAnio = document.getElementById("label-anio");
    var dropMes = document.getElementById("dropdown-mes");
    var dropAnio = document.getElementById("dropdown-anio");
    var divisor = document.getElementById("divisor-anio");

    var primerAnio = parseInt(selectAnio.dataset.primerAnio, 10) || 2024;
    var primerMes = parseInt(selectMes.dataset.primerMes, 10) || 1;
    var hoy = new Date();
    var anioActual = hoy.getFullYear();
    var mesActual = hoy.getMonth() + 1;

    function aplicar() {
      window.location.href = window.location.pathname +
        "?mes=" + encodeURIComponent(selectMes.value) + "&anio=" + encodeURIComponent(selectAnio.value);
    }

    function mostrarAnio(visible) {
      divisor.classList.toggle("hidden", !visible);
      btnAnio.classList.toggle("hidden", !visible);
    }

    function opcion(texto, activa, alElegir) {
      var el = document.createElement("button");
      el.type = "button";
      el.className = "mov-periodo__opcion" + (activa ? " is-activa" : "");
      el.setAttribute("role", "option");
      el.setAttribute("aria-selected", activa ? "true" : "false");
      el.textContent = texto;
      el.addEventListener("click", alElegir);
      return el;
    }

    function cerrarMenus() {
      dropMes.classList.add("hidden");
      dropAnio.classList.add("hidden");
      btnMes.setAttribute("aria-expanded", "false");
      btnAnio.setAttribute("aria-expanded", "false");
    }

    function render() {
      var anioSel = selectAnio.value === "all" ? anioActual : parseInt(selectAnio.value, 10);

      dropMes.innerHTML = "";
      dropMes.appendChild(opcion("Todas las fechas", selectMes.value === "all", function () {
        selectMes.value = "all";
        selectAnio.value = "all";
        labelMes.textContent = "Todas las fechas";
        mostrarAnio(false);
        aplicar();
      }));
      MESES.forEach(function (nombre, i) {
        var m = i + 1;
        var fuera = anioSel < primerAnio || (anioSel === primerAnio && m < primerMes) ||
                    anioSel > anioActual || (anioSel === anioActual && m > mesActual);
        if (fuera) return;
        dropMes.appendChild(opcion(nombre, String(m) === String(selectMes.value), function () {
          selectMes.value = m;
          labelMes.textContent = nombre;
          if (selectAnio.value === "all") {
            selectAnio.value = anioActual;
            labelAnio.textContent = anioActual;
          }
          mostrarAnio(true);
          aplicar();
        }));
      });

      dropAnio.innerHTML = "";
      for (var a = primerAnio; a <= anioActual; a++) {
        (function (anio) {
          dropAnio.appendChild(opcion(String(anio), String(anio) === String(selectAnio.value), function () {
            selectAnio.value = anio;
            labelAnio.textContent = anio;
            var mes = parseInt(selectMes.value, 10);
            if (anio === primerAnio && mes < primerMes) selectMes.value = primerMes;
            if (anio === anioActual && mes > mesActual) selectMes.value = mesActual;
            aplicar();
          }));
        })(a);
      }
    }

    function alternar(menu, otro, boton) {
      return function (e) {
        e.stopPropagation();
        var abrir = menu.classList.contains("hidden");
        cerrarMenus();
        menu.classList.toggle("hidden", !abrir);
        boton.setAttribute("aria-expanded", abrir ? "true" : "false");
      };
    }

    btnMes.addEventListener("click", alternar(dropMes, dropAnio, btnMes));
    btnAnio.addEventListener("click", alternar(dropAnio, dropMes, btnAnio));
    document.addEventListener("click", cerrarMenus);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") cerrarMenus(); });
    render();
  }

  function iniciarDescargar() {
    var menu = document.querySelector(".mov-descargar");
    if (!menu) return;
    menu.addEventListener("click", function (e) {
      if (e.target.closest(".btn-export")) menu.removeAttribute("open");
    });
    document.addEventListener("click", function (e) {
      if (!menu.contains(e.target)) menu.removeAttribute("open");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (window.GastuTours) window.GastuTours.init(window.CURRENT_MODULE);
    iniciarSelector();
    iniciarDescargar();
  });
})();

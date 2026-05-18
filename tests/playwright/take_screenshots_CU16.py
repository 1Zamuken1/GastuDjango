import os
import asyncio
from playwright.async_api import async_playwright

out_dir = r"c:\Users\Usuario\Downloads\GastuDjango\capturas_pruebas\CU-16"
os.makedirs(out_dir, exist_ok=True)
BASE = "http://127.0.0.1:8000"

async def login_admin(page):
    await page.goto(f"{BASE}/login/")
    await page.fill('input[type="email"]', 'p@p.com')
    await page.fill('input[name="password"]', 'playwright123')
    await page.click('button[type="submit"]')
    await page.wait_for_timeout(3000)

async def kill_overlays(page):
    await page.evaluate("""
        // Inject style to permanently hide modal and driver.js elements
        const style = document.createElement('style');
        style.innerHTML = `
            #gastu-modal-overlay { display: none !important; }
            .driver-overlay { display: none !important; }
            .driver-popover { display: none !important; }
            body.tour-active, body.driver-active { overflow: auto !important; }
        `;
        document.head.appendChild(style);

        // Also destroy current instances
        if(window.driverObj) { window.driverObj.destroy(); }
        document.body.classList.remove('tour-active', 'driver-active', 'driver-fade');
        document.querySelectorAll('.driver-overlay, .driver-popover, .driver-active-element').forEach(el => el.remove());

        const overlay = document.getElementById('gastu-modal-overlay');
        if (overlay) {
            overlay.classList.remove('gastu--visible');
            overlay.setAttribute('aria-hidden', 'true');
        }
    """)
    await page.wait_for_timeout(500)

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        await login_admin(page)

        # ── CASO 1: Ingresos -> Exportar Excel (Abril 2026) ─────────────
        try:
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Click en Excel para abrir el modal de exportación
            await page.evaluate("document.querySelector('.btn-export--excel').click()")
            await page.wait_for_timeout(1000)

            # Establecer rango de fechas para Abril 2026
            # dp-input-desde y dp-input-hasta son inputs ocultos que se actualizan mediante datepicker
            await page.evaluate("""
                document.getElementById('dp-input-desde').value = '2026-04-01';
                document.getElementById('dp-input-hasta').value = '2026-04-30';
                // También forzar check de todas las categorías disponibles
                document.querySelectorAll('.cat-check').forEach(cb => cb.checked = true);
            """)

            # Tomar captura del modal configurado para exportar a Excel
            await page.screenshot(path=os.path.join(out_dir, "1_Modal_Exportar_Excel.png"))

            # Descargar archivo
            async with page.expect_download() as download_info:
                await page.evaluate("document.getElementById('btn-descargar-reporte').click()")
            download = await download_info.value
            await download.save_as(os.path.join(out_dir, "gastuapp_ingresos_abril2026.xlsx"))
            print("Caso 1: Excel descargado correctamente.")
        except Exception as e:
            print("Error Caso 1:", e)

        # ── CASO 2: Egresos -> Exportar PDF (Abril 2026) ───────────────
        try:
            await page.goto(f"{BASE}/egresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Click en PDF para abrir el modal
            await page.evaluate("document.querySelector('.btn-export--pdf').click()")
            await page.wait_for_timeout(1000)

            # Rango de fechas
            await page.evaluate("""
                document.getElementById('dp-input-desde').value = '2026-04-01';
                document.getElementById('dp-input-hasta').value = '2026-04-30';
                document.querySelectorAll('.cat-check').forEach(cb => cb.checked = true);
            """)

            # Tomar captura del modal configurado para exportar a PDF
            await page.screenshot(path=os.path.join(out_dir, "2_Modal_Exportar_PDF.png"))

            # Descargar archivo
            async with page.expect_download() as download_info:
                await page.evaluate("document.getElementById('btn-descargar-reporte').click()")
            download = await download_info.value
            await download.save_as(os.path.join(out_dir, "gastuapp_egresos_abril2026.pdf"))
            print("Caso 2: PDF descargado correctamente.")
        except Exception as e:
            print("Error Caso 2:", e)

        # ── CASO 3: Ingresos -> Exportar CSV (Abril 2026) ──────────────
        try:
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Click en CSV para abrir el modal
            await page.evaluate("document.querySelector('.btn-export--csv').click()")
            await page.wait_for_timeout(1000)

            # Rango de fechas
            await page.evaluate("""
                document.getElementById('dp-input-desde').value = '2026-04-01';
                document.getElementById('dp-input-hasta').value = '2026-04-30';
                document.querySelectorAll('.cat-check').forEach(cb => cb.checked = true);
            """)

            # Tomar captura del modal configurado para exportar a CSV
            await page.screenshot(path=os.path.join(out_dir, "3_Modal_Exportar_CSV.png"))

            # Descargar archivo
            async with page.expect_download() as download_info:
                await page.evaluate("document.getElementById('btn-descargar-reporte').click()")
            download = await download_info.value
            await download.save_as(os.path.join(out_dir, "gastuapp_ingresos_abril2026.csv"))
            print("Caso 3: CSV descargado correctamente.")
        except Exception as e:
            print("Error Caso 3:", e)

        # ── CASO 4: Exportación sin datos (Diciembre 2027) ─────────────
        try:
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Abrir modal
            await page.evaluate("document.querySelector('.btn-export--excel').click()")
            await page.wait_for_timeout(1000)

            # Poner rango futuro
            await page.evaluate("""
                document.getElementById('dp-input-desde').value = '2027-12-01';
                document.getElementById('dp-input-hasta').value = '2027-12-31';
            """)

            # Click en descargar (bloqueado por backend)
            await page.evaluate("document.getElementById('btn-descargar-reporte').click()")
            await page.wait_for_timeout(1500)

            # Tomar captura de la alerta de error Toast de GastuAlerts
            await page.screenshot(path=os.path.join(out_dir, "4_Alerta_Exportar_Vacio.png"))
            print("Caso 4: Alerta de datos vacíos capturada.")
        except Exception as e:
            print("Error Caso 4:", e)

        # ── CASO 5: Dashboard - Utilidad no acumulable ─────────────────
        try:
            await page.goto(f"{BASE}/dashboard/")
            await page.wait_for_timeout(2500)
            await kill_overlays(page)

            # Tomar captura de pantalla del Dashboard que muestra los saldos mensuales independientes
            await page.screenshot(path=os.path.join(out_dir, "5_Dashboard_Mensual.png"))
            print("Caso 5: Captura de Dashboard mensual independiente tomada.")
        except Exception as e:
            print("Error Caso 5:", e)

        # ── CASO 6: Dashboard - Limitaciones de filtro ──────────────────
        try:
            await page.goto(f"{BASE}/dashboard/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Resaltar la toolbar del dashboard para ver que solo se filtra por mes y año, sin categorías
            # (Hacemos scroll y focus si es necesario)
            await page.screenshot(path=os.path.join(out_dir, "6_Dashboard_Filtros.png"))
            print("Caso 6: Captura de limitaciones de filtros en Dashboard tomada.")
        except Exception as e:
            print("Error Caso 6:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())

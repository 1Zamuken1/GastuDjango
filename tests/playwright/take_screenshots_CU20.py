import os
import asyncio
from playwright.async_api import async_playwright

out_dir = r"c:\Users\Usuario\Downloads\GastuDjango\capturas_pruebas\CU-20"
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

        # ── CASO 4: Intento de acceso sin autenticar ───────────────────
        try:
            print("Ejecutando Caso 4 (Acceso no autenticado)...")
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            
            # Verificar que redirigió a la pantalla de login
            url = page.url
            print(f"URL de redirección: {url}")
            await page.screenshot(path=os.path.join(out_dir, "4_Redireccion_No_Autenticado.png"))
            print("Caso 4 completado.")
        except Exception as e:
            print("Error Caso 4:", e)

        # Iniciar sesión para los demás casos
        await login_admin(page)

        # ── CASO 1: Listado de Ingresos Mes Actual ─────────────────────
        try:
            print("Ejecutando Caso 1...")
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Capturar listado completo con subtítulo, tarjetas, totales por categoría y total general
            await page.screenshot(path=os.path.join(out_dir, "1_Listado_Ingresos_Mes_Actual.png"), full_page=True)
            print("Caso 1 completado.")
        except Exception as e:
            print("Error Caso 1:", e)

        # ── CASO 2: Listado de Egresos Mes Actual ──────────────────────
        try:
            print("Ejecutando Caso 2...")
            await page.goto(f"{BASE}/egresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Capturar listado completo de egresos
            await page.screenshot(path=os.path.join(out_dir, "2_Listado_Egresos_Mes_Actual.png"), full_page=True)
            print("Caso 2 completado.")
        except Exception as e:
            print("Error Caso 2:", e)

        # ── CASO 3: Filtro de Período Mes Anterior (Abril 2026) ────────
        try:
            print("Ejecutando Caso 3...")
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Seleccionar mes 4 (Abril) y año 2026
            await page.select_option("#select-mes", "4")
            await page.select_option("#select-anio", "2026")
            
            # Capturar antes de filtrar
            await page.screenshot(path=os.path.join(out_dir, "3_Filtro_Periodo_Seleccionado.png"))

            # Hacer clic en filtrar
            await page.click('#btn-filtrar-periodo')
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Capturar listado actualizado únicamente con ingresos de Abril 2026
            await page.screenshot(path=os.path.join(out_dir, "3_Listado_Ingresos_Mes_Anterior.png"), full_page=True)
            print("Caso 3 completado.")
        except Exception as e:
            print("Error Caso 3:", e)

        # ── CASO 5: Listado de Ingresos Vacío (Enero 2024) ─────────────
        try:
            print("Ejecutando Caso 5...")
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Seleccionar mes 1 (Enero) y año 2024 (donde no hay movimientos)
            await page.select_option("#select-mes", "1")
            await page.select_option("#select-anio", "2024")
            
            # Filtrar
            await page.click('#btn-filtrar-periodo')
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Capturar estado vacío con mensaje descriptivo
            await page.screenshot(path=os.path.join(out_dir, "5_Listado_Ingresos_Vacio.png"), full_page=True)
            print("Caso 5 completado.")
        except Exception as e:
            print("Error Caso 5:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())

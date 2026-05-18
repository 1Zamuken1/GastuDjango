import os
import asyncio
from playwright.async_api import async_playwright

out_dir = r"c:\Users\Usuario\Downloads\GastuDjango\capturas_pruebas\CU-17"
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

        # Go to dashboard and clean overlays
        await page.goto(f"{BASE}/dashboard/")
        await page.wait_for_timeout(2000)
        await kill_overlays(page)

        # ── CASO 1: Filtrar período específico (Marzo 2026) ─────────────
        try:
            print("Ejecutando Caso 1...")
            # Select "Marzo" (value "3") and "2026" (value "2026")
            await page.select_option("#select-mes", "3")
            await page.select_option("#select-anio", "2026")
            await page.click("#btn-filtrar-periodo")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=os.path.join(out_dir, "1_Filtro_Marzo_2026.png"))
            print("Caso 1 completado.")
        except Exception as e:
            print("Error Caso 1:", e)

        # ── CASO 2: Filtrar mes anterior al actual ─────────────────────
        try:
            print("Ejecutando Caso 2...")
            # Retornar al mes actual primero
            is_disabled = await page.is_disabled("#btn-mes-actual")
            if not is_disabled:
                await page.click("#btn-mes-actual")
                await page.wait_for_timeout(1500)
            
            # Obtener el mes actual seleccionado y calcular el mes anterior
            mes_actual = await page.evaluate("parseInt(document.getElementById('select-mes').value)")
            anio_actual = await page.evaluate("parseInt(document.getElementById('select-anio').value)")
            
            mes_ant = mes_actual - 1
            anio_ant = anio_actual
            if mes_ant == 0:
                mes_ant = 12
                anio_ant -= 1
                
            await page.select_option("#select-mes", str(mes_ant))
            await page.select_option("#select-anio", str(anio_ant))
            await page.click("#btn-filtrar-periodo")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=os.path.join(out_dir, "2_Filtro_Mes_Anterior.png"))
            print("Caso 2 completado.")
        except Exception as e:
            print("Error Caso 2:", e)

        # ── CASO 3: Navegación por flechas (Anterior/Siguiente) ─────────
        try:
            print("Ejecutando Caso 3...")
            # Click anterior
            await page.click("#btn-mes-anterior")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=os.path.join(out_dir, "3_Navegacion_Mes_Anterior.png"))
            
            # Click siguiente
            await page.click("#btn-mes-siguiente")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=os.path.join(out_dir, "3_Navegacion_Mes_Siguiente.png"))
            print("Caso 3 completado.")
        except Exception as e:
            print("Error Caso 3:", e)

        # ── CASO 4: Período anterior a la creación de la cuenta (Enero 2024)
        try:
            print("Ejecutando Caso 4...")
            await page.select_option("#select-mes", "1")
            await page.select_option("#select-anio", "2024")
            await page.click("#btn-filtrar-periodo")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=os.path.join(out_dir, "4_Periodo_Anterior_Creacion.png"))
            print("Caso 4 completado.")
        except Exception as e:
            print("Error Caso 4:", e)

        # ── CASO 5: Período futuro sin movimientos (Diciembre 2027) ────
        try:
            print("Ejecutando Caso 5...")
            await page.select_option("#select-mes", "12")
            await page.select_option("#select-anio", "2027")
            await page.click("#btn-filtrar-periodo")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=os.path.join(out_dir, "5_Periodo_Futuro_Vacio.png"))
            print("Caso 5 completado.")
        except Exception as e:
            print("Error Caso 5:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())

import os
import asyncio
from playwright.async_api import async_playwright

out_dir = r"c:\Users\Usuario\Downloads\GastuDjango\capturas_pruebas\CU-21"
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

        # ── CASO 1: Editar "Pago quincenal" -> cambiar monto a 2.000.000 ─
        try:
            print("Ejecutando Caso 1...")
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Click en la tarjeta "Salario"
            await page.click('.categoria-card:has-text("Salario")')
            await page.wait_for_timeout(1000)

            # Click en Editar sobre el registro "Pago quincenal"
            await page.click('.btn-icon.btn-editar')
            await page.wait_for_timeout(800)

            # Cambiar monto
            await page.fill('#campo-monto', '2000000')
            
            # Guardar
            await page.click('#btn-guardar')
            await page.wait_for_timeout(2500)

            # Tomar captura del listado reflejando el monto de $2.000.000
            await page.screenshot(path=os.path.join(out_dir, "1_Listado_Ingreso_Monto_Actualizado.png"), full_page=True)
            print("Caso 1 completado.")
        except Exception as e:
            print("Error Caso 1:", e)

        # ── CASO 2: Editar egreso "Suscripción mensual" -> cambiar a "Alquileres" ─
        try:
            print("Ejecutando Caso 2...")
            await page.goto(f"{BASE}/egresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Click en la tarjeta "Tecnología"
            await page.click('.categoria-card:has-text("Tecnología")')
            await page.wait_for_timeout(1000)

            # Click en Editar sobre "Suscripción mensual"
            await page.click('.btn-icon.btn-editar')
            await page.wait_for_timeout(800)

            # Cambiar categoría
            await page.click('#btn-picker-categoria')
            await page.wait_for_timeout(800)
            await page.click('.picker-cat-card[data-nombre="Alquileres"]')
            await page.wait_for_timeout(800)

            # Guardar
            await page.click('#btn-guardar')
            await page.wait_for_timeout(2500)

            # Tomar captura del listado de egresos con Alquileres actualizado
            await page.screenshot(path=os.path.join(out_dir, "2_Listado_Egreso_Categoria_Actualizada.png"), full_page=True)
            print("Caso 2 completado.")
        except Exception as e:
            print("Error Caso 2:", e)

        # ── CASO 3: Error monto en blanco ──────────────────────────────
        try:
            print("Ejecutando Caso 3...")
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Click en la tarjeta "Salario"
            await page.click('.categoria-card:has-text("Salario")')
            await page.wait_for_timeout(1000)

            # Click en Editar
            await page.click('.btn-icon.btn-editar')
            await page.wait_for_timeout(800)

            # Dejar monto en blanco
            await page.fill('#campo-monto', '')
            
            # Guardar
            await page.click('#btn-guardar')
            await page.wait_for_timeout(800)

            # Tomar captura mostrando error del monto obligatorio
            await page.screenshot(path=os.path.join(out_dir, "3_Error_Monto_Vacio.png"))
            print("Caso 3 completado.")
        except Exception as e:
            print("Error Caso 3:", e)

        # ── CASO 4: Error monto negativo ───────────────────────────────
        try:
            print("Ejecutando Caso 4...")
            # Poner monto negativo
            await page.fill('#campo-monto', '-50000')
            
            # Guardar
            await page.click('#btn-guardar')
            await page.wait_for_timeout(800)

            # Tomar captura mostrando error del monto negativo
            await page.screenshot(path=os.path.join(out_dir, "4_Error_Monto_Negativo.png"))
            print("Caso 4 completado.")
        except Exception as e:
            print("Error Caso 4:", e)

        # ── CASO 5: Error categoría vacía ──────────────────────────────
        try:
            print("Ejecutando Caso 5...")
            # Limpiar campo de categoría por JavaScript
            await page.evaluate("""
                document.getElementById('campo-categoria').value = '';
                document.getElementById('btn-picker-categoria').textContent = 'Seleccionar categoría';
            """)
            await page.fill('#campo-monto', '15000')
            
            # Guardar
            await page.click('#btn-guardar')
            await page.wait_for_timeout(800)

            # Tomar captura mostrando error de categoría vacía
            await page.screenshot(path=os.path.join(out_dir, "5_Error_Categoria_Vacia.png"))
            print("Caso 5 completado.")
        except Exception as e:
            print("Error Caso 5:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())

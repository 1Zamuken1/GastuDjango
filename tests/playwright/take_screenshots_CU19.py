import os
import asyncio
from playwright.async_api import async_playwright

out_dir = r"c:\Users\Usuario\Downloads\GastuDjango\capturas_pruebas\CU-19"
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

async def select_picker_category(page, name):
    await page.click('#btn-picker-categoria')
    await page.wait_for_timeout(800)
    await page.click(f'.picker-cat-card[data-nombre="{name}"]')
    await page.wait_for_timeout(800)

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        await login_admin(page)

        # ── CASO 1: Creación de INGRESO con Freelance ─────────────────
        try:
            print("Ejecutando Caso 1...")
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            await page.click('#btn-nuevo')
            await page.wait_for_timeout(1000)

            # Seleccionar Freelance
            await select_picker_category(page, "Freelance")
            await page.fill('#campo-monto', '200000')
            await page.fill('#campo-descripcion', 'Trabajo de desarrollo extra')
            
            # Capturar completado
            await page.screenshot(path=os.path.join(out_dir, "1_Ingreso_Freelance_Completado.png"))

            # Guardar
            await page.click('#btn-guardar')
            await page.wait_for_timeout(3000)

            # Capturar listado con la tarjeta Freelance
            await page.screenshot(path=os.path.join(out_dir, "1_Ingreso_Freelance_Registrado.png"), full_page=True)
            print("Caso 1 completado.")
        except Exception as e:
            print("Error Caso 1:", e)

        # ── CASO 2: Edición de EGRESO (Internet -> Servicios Públicos) ─
        try:
            print("Ejecutando Caso 2...")
            await page.goto(f"{BASE}/egresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Click en la tarjeta "Internet" para ver sus movimientos
            await page.click('.categoria-card:has-text("Internet")')
            await page.wait_for_timeout(1500)

            # Click en el botón Editar del movimiento "Plan de internet mensual"
            await page.click('.btn-icon.btn-editar')
            await page.wait_for_timeout(1000)

            # Cambiar de Internet a Servicios Públicos
            await select_picker_category(page, "Servicios Públicos")
            
            # Capturar cambio en el modal
            await page.screenshot(path=os.path.join(out_dir, "2_Edicion_Cambio_Categoria.png"))

            # Guardar
            await page.click('#btn-guardar')
            await page.wait_for_timeout(3000)

            # Capturar listado de egresos actualizado
            await page.screenshot(path=os.path.join(out_dir, "2_Edicion_Servicios_Publicos_Registrado.png"), full_page=True)
            print("Caso 2 completado.")
        except Exception as e:
            print("Error Caso 2:", e)

        # ── CASO 3: Guardar sin seleccionar categoría ────────────────
        try:
            print("Ejecutando Caso 3...")
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            await page.click('#btn-nuevo')
            await page.wait_for_timeout(1000)

            await page.fill('#campo-monto', '15000')
            await page.fill('#campo-descripcion', 'Prueba categoría obligatoria')
            
            # Intentar guardar
            await page.click('#btn-guardar')
            await page.wait_for_timeout(1000)

            # Capturar error de validación
            await page.screenshot(path=os.path.join(out_dir, "3_Error_Categoria_Vacia.png"))
            print("Caso 3 completado.")
        except Exception as e:
            print("Error Caso 3:", e)

        # ── CASO 4: Selector de categorías sólo muestra tipo correspondiente ─
        try:
            print("Ejecutando Caso 4...")
            # Con el modal de nuevo ingreso abierto del Caso 3, abrimos el selector
            await page.click('#btn-picker-categoria')
            await page.wait_for_timeout(1000)

            # Capturar el picker de categorías abierto mostrando sólo ingresos
            await page.screenshot(path=os.path.join(out_dir, "4_Selector_Solo_Ingresos.png"))
            print("Caso 4 completado.")
        except Exception as e:
            print("Error Caso 4:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())

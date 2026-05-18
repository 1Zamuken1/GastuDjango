import os
import asyncio
from playwright.async_api import async_playwright

out_dir = r"c:\Users\Usuario\Downloads\GastuDjango\capturas_pruebas\CU-18"
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

        # ── CASO 1: Registro correcto de INGRESO ───────────────────────
        try:
            print("Ejecutando Caso 1...")
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            await page.click('#btn-nuevo')
            await page.wait_for_timeout(1000)

            # Completar formulario
            await select_picker_category(page, "Salario")
            await page.fill('#campo-monto', '1500000')
            await page.fill('#campo-descripcion', 'Pago quincenal')
            
            # Capturar antes de guardar
            await page.screenshot(path=os.path.join(out_dir, "1_Ingreso_Completado.png"))

            # Guardar y esperar recarga del grid
            await page.click('#btn-guardar')
            await page.wait_for_timeout(3000)
            
            # Capturar resultado con el nuevo registro
            await page.screenshot(path=os.path.join(out_dir, "1_Ingreso_Registrado_Listado.png"), full_page=True)
            print("Caso 1 completado.")
        except Exception as e:
            print("Error Caso 1:", e)

        # ── CASO 2: Registro correcto de EGRESO ────────────────────────
        try:
            print("Ejecutando Caso 2...")
            await page.goto(f"{BASE}/egresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            await page.click('#btn-nuevo')
            await page.wait_for_timeout(1000)

            # Completar formulario
            await select_picker_category(page, "Alimentación")
            await page.fill('#campo-monto', '50000')
            await page.fill('#campo-descripcion', 'Compra de supermercado')
            
            # Capturar antes de guardar
            await page.screenshot(path=os.path.join(out_dir, "2_Egreso_Completado.png"))

            # Guardar y esperar
            await page.click('#btn-guardar')
            await page.wait_for_timeout(3000)
            
            # Capturar listado actualizado
            await page.screenshot(path=os.path.join(out_dir, "2_Egreso_Registrado_Listado.png"), full_page=True)
            print("Caso 2 completado.")
        except Exception as e:
            print("Error Caso 2:", e)

        # ── CASO 3: Validación de Categoría obligatoria ────────────────
        try:
            print("Ejecutando Caso 3...")
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            await page.click('#btn-nuevo')
            await page.wait_for_timeout(1000)

            # No seleccionamos categoría
            await page.fill('#campo-monto', '1000')
            await page.fill('#campo-descripcion', 'Prueba categoría obligatoria')
            
            # Guardar para detonar validación
            await page.click('#btn-guardar')
            await page.wait_for_timeout(1000)
            
            # Capturar error de validación
            await page.screenshot(path=os.path.join(out_dir, "3_Validacion_Categoria_Obligatoria.png"))
            print("Caso 3 completado.")
        except Exception as e:
            print("Error Caso 3:", e)

        # ── CASO 4: Validación de Monto negativo ───────────────────────
        try:
            print("Ejecutando Caso 4...")
            # Seleccionar categoría para aislar el error de monto
            await select_picker_category(page, "Salario")
            await page.fill('#campo-monto', '-50000')
            
            # Guardar
            await page.click('#btn-guardar')
            await page.wait_for_timeout(1000)
            
            # Capturar error
            await page.screenshot(path=os.path.join(out_dir, "4_Validacion_Monto_Negativo.png"))
            print("Caso 4 completado.")
        except Exception as e:
            print("Error Caso 4:", e)

        # ── CASO 5: Validación de Monto no válido (abc) ────────────────
        try:
            print("Ejecutando Caso 5...")
            # Modificar tipo de input a 'text' para meter 'abc' sin que playwright lance error
            await page.evaluate("document.getElementById('campo-monto').type = 'text'")
            await page.fill('#campo-monto', '')
            await page.fill('#campo-monto', 'abc')
            
            # Guardar
            await page.click('#btn-guardar')
            await page.wait_for_timeout(1000)
            
            # Capturar error
            await page.screenshot(path=os.path.join(out_dir, "5_Validacion_Monto_Invalido.png"))
            print("Caso 5 completado.")
        except Exception as e:
            print("Error Caso 5:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())

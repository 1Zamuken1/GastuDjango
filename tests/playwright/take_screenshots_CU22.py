import os
import asyncio
from playwright.async_api import async_playwright

out_dir = r"c:\Users\Usuario\Downloads\GastuDjango\capturas_pruebas\CU-22"
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

        # ── CASO 3: Redirección usuario no autenticado ────────────────
        try:
            print("Ejecutando Caso 3...")
            # Intentar POST a eliminar/999999/ sin loguearse
            # En Django, @login_required intercepta e intentará redirigir a /login/?next=/eliminar/999999/
            await page.goto(f"{BASE}/eliminar/999999/")
            await page.wait_for_timeout(2000)

            await page.screenshot(path=os.path.join(out_dir, "3_Redireccion_Eliminacion_No_Autenticado.png"))
            print("Caso 3 completado.")
        except Exception as e:
            print("Error Caso 3:", e)

        # Iniciar sesión para los demás casos
        await login_admin(page)

        # ── CASO 1: Eliminar "Pago quincenal" (INGRESO) ───────────────
        try:
            print("Ejecutando Caso 1...")
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Click en la tarjeta "Salario"
            await page.click('.categoria-card:has-text("Salario")')
            await page.wait_for_timeout(1000)

            # Capturar antes de eliminar
            await page.screenshot(path=os.path.join(out_dir, "1_Antes_Eliminar_Ingreso.png"))

            # Click en el botón Eliminar
            await page.click('.btn-icon.btn-eliminar')
            await page.wait_for_timeout(2000)

            # Capturar listado vacío (o reflejando que desapareció del listado de ingresos)
            await page.screenshot(path=os.path.join(out_dir, "1_Ingreso_Eliminado_Listado.png"))
            print("Caso 1 completado.")
        except Exception as e:
            print("Error Caso 1:", e)

        # ── CASO 2: Eliminar "Compra supermercado" (EGRESO) ───────────
        try:
            print("Ejecutando Caso 2...")
            await page.goto(f"{BASE}/egresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Click en la tarjeta "Alimentación"
            await page.click('.categoria-card:has-text("Alimentación")')
            await page.wait_for_timeout(1000)

            # Capturar antes de eliminar
            await page.screenshot(path=os.path.join(out_dir, "2_Antes_Eliminar_Egreso.png"))

            # Click en el botón Eliminar
            await page.click('.btn-icon.btn-eliminar')
            await page.wait_for_timeout(2000)

            # Capturar listado reflejando que desapareció
            await page.screenshot(path=os.path.join(out_dir, "2_Egreso_Eliminado_Listado.png"))
            print("Caso 2 completado.")
        except Exception as e:
            print("Error Caso 2:", e)

        # ── CASO 4: Intentar eliminar movimiento inexistente ──────────
        try:
            print("Ejecutando Caso 4...")
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Ejecutar llamada AJAX fallida a un ID inexistente y mostrar el Toast
            await page.evaluate("""
                const token = document.querySelector('[name=csrfmiddlewaretoken]').value;
                fetch('/eliminar/999999/', {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': token }
                })
                .then(res => res.json())
                .then(data => {
                    // Instanciar o simular mostrar el Toast de error directamente usando la clase o función global
                    const t = document.createElement('div');
                    t.className = 'toast toast--error';
                    t.textContent = data.error || 'Movimiento no encontrado';
                    document.getElementById('toast-container').appendChild(t);
                });
            """)
            await page.wait_for_timeout(1000)

            # Tomar captura mostrando el Toast de error "Movimiento no encontrado"
            await page.screenshot(path=os.path.join(out_dir, "4_Error_Movimiento_No_Encontrado.png"))
            print("Caso 4 completado.")
        except Exception as e:
            print("Error Caso 4:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())

import os
import asyncio
from playwright.async_api import async_playwright

out_dir = r"c:\Users\Usuario\Downloads\GastuDjango\capturas_pruebas\CU-46"
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
        // Hide modal and driver.js elements
        const style = document.createElement('style');
        style.innerHTML = `
            #gastu-modal-overlay { display: none !important; }
            .driver-overlay { display: none !important; }
            .driver-popover { display: none !important; }
            body.tour-active, body.driver-active { overflow: auto !important; }
        `;
        document.head.appendChild(style);

        if(window.driverObj) { window.driverObj.destroy(); }
    """)
    await page.wait_for_timeout(500)

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        # ── CASO 4: Intento de acceso sin autenticar ───────────────────
        try:
            print("Ejecutando Caso 4...")
            await page.goto(f"{BASE}/perfil/?tab=notificaciones")
            await page.wait_for_timeout(2000)
            
            await page.screenshot(path=os.path.join(out_dir, "4_Redireccion_Notificaciones_No_Autenticado.png"))
            print("Caso 4 completado.")
        except Exception as e:
            print("Error Caso 4:", e)

        # Iniciar sesión para los demás casos
        await login_admin(page)

        # ── CASO 3: Redirección al hacer clic en la campana ────────────
        try:
            print("Ejecutando Caso 3...")
            await page.goto(f"{BASE}/ingresos/")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Clic forzado en el botón campana en la topbar
            await page.click('#notif-btn', force=True)
            await page.wait_for_timeout(2500)

            # Verificar que redirigió correctamente al tab de notificaciones del perfil
            await page.screenshot(path=os.path.join(out_dir, "3_Redireccion_Campana_A_Perfil.png"))
            print("Caso 3 completado.")
        except Exception as e:
            print("Error Caso 3:", e)

        # Asegurar que estamos en perfil/notificaciones para los siguientes casos
        await page.goto(f"{BASE}/perfil/?tab=notificaciones")
        await page.wait_for_timeout(2000)
        await kill_overlays(page)

        # ── CASO 1: Marcar una notificación específica como leída ───────
        try:
            print("Ejecutando Caso 1...")
            # Localizar el primer botón de marcar como leída y hacer clic forzado
            await page.click('.notif-read-btn', force=True)
            await page.wait_for_timeout(1500)

            # Tomar captura mostrando el cambio de estado y reducción del contador
            await page.screenshot(path=os.path.join(out_dir, "1_Notificacion_Marcada_Leida.png"))
            print("Caso 1 completado.")
        except Exception as e:
            print("Error Caso 1:", e)

        # ── CASO 2: Marcar todas como leídas ───────────────────────────
        try:
            print("Ejecutando Caso 2...")
            # Hacer clic forzado en el botón "Marcar todas como leídas"
            await page.click('#btn-marcar-todas', force=True)
            await page.wait_for_timeout(2000)

            # Capturar listado vacío y sin badges
            await page.screenshot(path=os.path.join(out_dir, "2_Todas_Marcadas_Leidas.png"))
            print("Caso 2 completado.")
        except Exception as e:
            print("Error Caso 2:", e)

        # ── CASO 5: Marcar leída notificación que ya no existe ─────────
        try:
            print("Ejecutando Caso 5...")
            # Recargar para asegurar el contexto limpio
            await page.goto(f"{BASE}/perfil/?tab=notificaciones")
            await page.wait_for_timeout(2000)
            await kill_overlays(page)

            # Enviar fetch manual en la consola del navegador a un ID inexistente
            res = await page.evaluate("""
                async () => {
                    const filterEl = document.getElementById('notif-filters');
                    const token = filterEl ? filterEl.getAttribute('data-csrf') : '';
                    const r = await fetch('/notificaciones/marcar-leidas/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest',
                            'X-CSRFToken': token
                        },
                        body: JSON.stringify({ ids: [999999] })
                    });
                    return await r.json();
                }
            """)
            print(f"Respuesta del servidor para Caso 5: {res}")
            
            # Tomar captura para evidenciar que no se produce crash
            await page.screenshot(path=os.path.join(out_dir, "5_Error_Notificacion_Inexistente.png"))
            print("Caso 5 completado.")
        except Exception as e:
            print("Error Caso 5:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())

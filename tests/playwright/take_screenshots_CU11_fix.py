import os
import asyncio
from playwright.async_api import async_playwright

out_dir = r"c:\Users\Usuario\Downloads\GastuDjango\capturas_pruebas\CU-11"
BASE = "http://127.0.0.1:8000"

async def login_admin(page):
    await page.goto(f"{BASE}/login/")
    await page.fill('input[type="email"]', 'p@p.com')
    await page.fill('input[name="password"]', 'playwright123')
    await page.click('button[type="submit"]')
    await page.wait_for_timeout(3000)

async def go_categorias(page):
    await page.goto(f"{BASE}/admin-panel/categorias/")
    await page.wait_for_timeout(2000)
    await page.evaluate("if(window.driverObj) window.driverObj.destroy();")

async def get_is_active(page, cat_id):
    return await page.evaluate(f"""
        !!document.querySelector('.js-toggle-categoria[data-id="{cat_id}"]')?.checked
    """)

async def force_toggle(page, cat_id):
    await page.evaluate(f"""
        (function() {{
            const cb = document.querySelector('.js-toggle-categoria[data-id="{cat_id}"]');
            if(cb) {{ cb.checked = !cb.checked; cb.dispatchEvent(new Event('change', {{ bubbles: true }})); }}
        }})();
    """)
    await page.wait_for_timeout(2000)

async def kill_tour(page):
    await page.evaluate("""
        if(window.driverObj) { window.driverObj.destroy(); }
        document.body.classList.remove('tour-active', 'driver-active', 'driver-fade');
        document.querySelectorAll('.driver-overlay, .driver-popover, .driver-active-element').forEach(el => el.remove());
    """)
    await page.wait_for_timeout(500)

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        await login_admin(page)

        # ── CASO 3: Picker sin "Transporte" (desactivada) ──────────────
        try:
            # 1. Desactivar Transporte (id=13, tipo EGRESO)
            await go_categorias(page)
            active = await get_is_active(page, 13)
            if active:
                print("Desactivando Transporte para la prueba...")
                await force_toggle(page, 13)

            # 2. Ir a /egresos/
            await page.goto(f"{BASE}/egresos/")
            await page.wait_for_timeout(3000)
            await kill_tour(page)

            # Click en Nuevo Egreso para abrir el modal usando JavaScript directo (evita bloqueos de overlays)
            has_btn = await page.evaluate("!!document.getElementById('btn-nuevo')")
            print(f"Has btn-nuevo: {has_btn}")

            if has_btn:
                await page.evaluate("document.getElementById('btn-nuevo').click()")
                await page.wait_for_timeout(1000)
                await kill_tour(page)

                has_picker = await page.evaluate("!!document.getElementById('btn-picker-categoria')")
                print(f"Has btn-picker-categoria: {has_picker}")

                if has_picker:
                    await page.evaluate("document.getElementById('btn-picker-categoria').click()")
                    await page.wait_for_timeout(1000)

            # Screenshot del modal picker de categorías
            await page.screenshot(path=os.path.join(out_dir, "3_Selector_Sin_Transporte.png"))
            print("Captura C3 tomada de forma exitosa!")

            # 3. Reactivar Transporte
            await go_categorias(page)
            active = await get_is_active(page, 13)
            if not active:
                print("Reactivando Transporte...")
                await force_toggle(page, 13)

        except Exception as e:
            print("Error C3:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())

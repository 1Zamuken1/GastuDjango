import os
import asyncio
from playwright.async_api import async_playwright

out_dir = r"c:\Users\Usuario\Downloads\GastuDjango\capturas_pruebas\CU-11"
os.makedirs(out_dir, exist_ok=True)

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
        document.querySelector('.js-toggle-categoria[data-id="{cat_id}"]').checked
    """)

async def force_toggle(page, cat_id):
    """Dispara el evento change del checkbox directamente, sin necesidad de visibilidad."""
    await page.evaluate(f"""
        (function() {{
            const cb = document.querySelector('.js-toggle-categoria[data-id="{cat_id}"]');
            cb.checked = !cb.checked;
            cb.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }})();
    """)
    await page.wait_for_timeout(1500)

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        await login_admin(page)

        # ── CASO 1: Desactivar "Transporte" (id=13) ─────────────────────
        try:
            await go_categorias(page)
            # Asegurar que está activa
            active = await get_is_active(page, 13)
            if not active:
                await force_toggle(page, 13)
                await go_categorias(page)

            # Desactivar
            await force_toggle(page, 13)

            # Mostrar listado filtrado a "activas" — Transporte ya no aparece
            await page.goto(f"{BASE}/admin-panel/categorias/?estado=activo")
            await page.wait_for_timeout(1500)
            await page.screenshot(path=os.path.join(out_dir, "1_Transporte_Desactivada.png"), full_page=True)
        except Exception as e:
            print("Error C1:", e)

        # ── CASO 2: Reactivar "Transporte" desde inactivas ──────────────
        try:
            await page.goto(f"{BASE}/admin-panel/categorias/?estado=inactivo")
            await page.wait_for_timeout(1500)
            await page.screenshot(path=os.path.join(out_dir, "2_Transporte_En_Inactivas.png"), full_page=True)

            await force_toggle(page, 13)

            await page.goto(f"{BASE}/admin-panel/categorias/?estado=activo")
            await page.wait_for_timeout(1500)
            await page.screenshot(path=os.path.join(out_dir, "2b_Transporte_Reactivada.png"), full_page=True)
        except Exception as e:
            print("Error C2:", e)

        # ── CASO 3: Picker de usuario sin "Transporte" ──────────────────
        try:
            # Desactivar Transporte
            await go_categorias(page)
            active = await get_is_active(page, 13)
            if active:
                await force_toggle(page, 13)

            # Abrir movimientos gastos y picker de categoría
            await page.goto(f"{BASE}/movimientos/gastos/")
            await page.wait_for_timeout(2000)
            await page.evaluate("if(window.driverObj) window.driverObj.destroy();")
            await page.evaluate("document.getElementById('btn-nuevo').click()")
            await page.wait_for_timeout(1000)
            btn_cat = page.locator('#btn-picker-categoria')
            if await btn_cat.count() > 0:
                await btn_cat.evaluate("el => el.click()")
                await page.wait_for_timeout(1000)
            await page.screenshot(path=os.path.join(out_dir, "3_Selector_Sin_Transporte.png"))

            # Reactivar
            await go_categorias(page)
            await force_toggle(page, 13)
        except Exception as e:
            print("Error C3:", e)

        # ── CASO ERROR 4: Sin permisos ────────────────────────────────────
        try:
            await page.goto(f"{BASE}/logout/")
            await page.wait_for_timeout(1000)
            await page.goto(f"{BASE}/admin-panel/categorias/13/toggle/")
            await page.wait_for_timeout(1500)
            await page.screenshot(path=os.path.join(out_dir, "4_Toggle_Sin_Permiso.png"))
        except Exception as e:
            print("Error C4:", e)

        # ── CASO ERROR 5: Desactivar una ya inactiva ────────────────────
        try:
            await login_admin(page)
            await go_categorias(page)

            # Desactivar Transporte
            active = await get_is_active(page, 13)
            if active:
                await force_toggle(page, 13)

            # Mostrar inactivas con Transporte — toggle desmarcado, sin error
            await page.goto(f"{BASE}/admin-panel/categorias/?estado=inactivo")
            await page.wait_for_timeout(1500)
            await page.screenshot(path=os.path.join(out_dir, "5_Categoria_Ya_Inactiva.png"), full_page=True)

            # Limpiar: reactivar
            await force_toggle(page, 13)
        except Exception as e:
            print("Error C5:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())

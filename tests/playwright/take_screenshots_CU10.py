import os
import asyncio
from playwright.async_api import async_playwright

out_dir = r"c:\Users\Usuario\Downloads\GastuDjango\capturas_pruebas\CU-10"
os.makedirs(out_dir, exist_ok=True)

BASE = "http://127.0.0.1:8000"

async def login(page):
    await page.goto(f"{BASE}/login/")
    await page.fill('input[type="email"]', 'p@p.com')
    await page.fill('input[name="password"]', 'playwright123')
    await page.click('button[type="submit"]')
    await page.wait_for_timeout(3000)

async def open_edit_modal(page, cat_id):
    """Hace click en el botón de editar de la categoría con el ID dado."""
    await page.goto(f"{BASE}/admin-panel/categorias/")
    await page.wait_for_timeout(2000)
    await page.evaluate("if(window.driverObj) window.driverObj.destroy();")
    btn = page.locator(f'.js-btn-editar-categoria[data-id="{cat_id}"]')
    await btn.click()
    await page.wait_for_timeout(1000)

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        # ── Login ─────────────────────────────────────────────────────
        await login(page)

        # ── CASO FELIZ 1: Editar nombre "Salario" → "Salario Mensual" ──
        try:
            await open_edit_modal(page, cat_id=1)  # Salario - INGRESO
            await page.screenshot(path=os.path.join(out_dir, "CF1_Modal_Editar_Abierto.png"))
            await page.fill('#editar-cat-nombre', '')
            await page.fill('#editar-cat-nombre', 'Salario Mensual')
            await page.screenshot(path=os.path.join(out_dir, "CF1_Nombre_Cambiado.png"))
            await page.click('#form-editar-categoria button[type="submit"]')
            await page.wait_for_timeout(2500)
            await page.screenshot(path=os.path.join(out_dir, "CF1_Nombre_Actualizado_Listado.png"), full_page=True)
            # Revertir para no afectar otras pruebas
            await open_edit_modal(page, cat_id=1)
            await page.fill('#editar-cat-nombre', '')
            await page.fill('#editar-cat-nombre', 'Salario')
            await page.click('#form-editar-categoria button[type="submit"]')
            await page.wait_for_timeout(2000)
        except Exception as e:
            print("Error CF1:", e)

        # ── CASO FELIZ 2: Cambiar tipo de EGRESO a INGRESO ─────────────
        try:
            await open_edit_modal(page, cat_id=13)  # Transporte - EGRESO
            await page.screenshot(path=os.path.join(out_dir, "CF2_Modal_Tipo_Original.png"))
            await page.select_option('#editar-cat-tipo', 'INGRESO')
            await page.screenshot(path=os.path.join(out_dir, "CF2_Tipo_Cambiado.png"))
            await page.click('#form-editar-categoria button[type="submit"]')
            await page.wait_for_timeout(2500)
            await page.screenshot(path=os.path.join(out_dir, "CF2_Tipo_Actualizado_Listado.png"), full_page=True)
            # Revertir
            await open_edit_modal(page, cat_id=13)
            await page.select_option('#editar-cat-tipo', 'EGRESO')
            await page.click('#form-editar-categoria button[type="submit"]')
            await page.wait_for_timeout(2000)
        except Exception as e:
            print("Error CF2:", e)

        # ── CASO ERROR 3: Nombre vacío ─────────────────────────────────
        try:
            await open_edit_modal(page, cat_id=9)  # Bonos - INGRESO
            # Borrar completamente el nombre
            await page.evaluate("document.getElementById('editar-cat-nombre').value = ''")
            await page.screenshot(path=os.path.join(out_dir, "CE3_Nombre_Vacio_Antes.png"))
            await page.click('#form-editar-categoria button[type="submit"]')
            await page.wait_for_timeout(1000)
            await page.screenshot(path=os.path.join(out_dir, "CE3_Validacion_Nombre_Obligatorio.png"))
        except Exception as e:
            print("Error CE3:", e)

        # ── CASO ERROR 4: Nombre duplicado existente ───────────────────
        try:
            await open_edit_modal(page, cat_id=9)  # Bonos - INGRESO
            await page.fill('#editar-cat-nombre', '')
            await page.fill('#editar-cat-nombre', 'Dividendos')  # Ya existe id=4
            await page.screenshot(path=os.path.join(out_dir, "CE4_Nombre_Duplicado_Ingresado.png"))
            await page.click('#form-editar-categoria button[type="submit"]')
            await page.wait_for_timeout(1000)
            await page.screenshot(path=os.path.join(out_dir, "CE4_Error_Nombre_Duplicado.png"))
        except Exception as e:
            print("Error CE4:", e)

        # ── CASO ERROR 5: Acceso sin permisos (usuario no admin) ────────
        try:
            # Cerrar sesión admin
            await page.goto(f"{BASE}/logout/")
            await page.wait_for_timeout(1000)
            # Intentar acceder a la URL de edición directamente sin autenticar
            await page.goto(f"{BASE}/admin-panel/categorias/1/editar/")
            await page.wait_for_timeout(1500)
            await page.screenshot(path=os.path.join(out_dir, "CE5_Acceso_Sin_Permisos.png"))
        except Exception as e:
            print("Error CE5:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())

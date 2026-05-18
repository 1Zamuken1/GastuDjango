import os
import asyncio
from playwright.async_api import async_playwright

out_dir = r"c:\Users\Usuario\Downloads\GastuDjango\capturas_pruebas"
os.makedirs(out_dir, exist_ok=True)

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        
        # Login
        try:
            await page.goto("http://127.0.0.1:8000/login/")
            await page.fill('input[type="email"]', 'p@p.com')
            await page.fill('input[name="password"]', 'playwright123')
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(3000)
            await page.goto("http://127.0.0.1:8000/dashboard/")
            await page.wait_for_timeout(2000)
            await page.evaluate("if(window.driverObj) window.driverObj.destroy();")
            await page.screenshot(path=os.path.join(out_dir, "CU-17_Dashboard.png"), full_page=True)
        except Exception: pass
        
        # CU-16 Exportar (abrir modal pdf o hacer click en excel)
        try:
            await page.evaluate("document.getElementById('btn-export-excel').click()")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=os.path.join(out_dir, "CU-16_Exportar_Vacio.png"))
        except Exception: pass
        
        # Go to Categorias
        try:
            await page.goto("http://127.0.0.1:8000/panel/categorias/")
            await page.wait_for_timeout(2000)
            await page.evaluate("if(window.driverObj) window.driverObj.destroy();")
            await page.screenshot(path=os.path.join(out_dir, "CU-07_Categorias_Vista.png"))
            await page.evaluate("document.getElementById('btn-nueva-categoria').click()")
            await page.wait_for_timeout(1000)
            await page.fill('#nombre', 'Test Categoria')
            await page.evaluate("document.getElementById('btn-guardar').click()")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=os.path.join(out_dir, "CU-07_Categoria_Creada.png"))
        except Exception: pass
        
        # Go to Movimientos (Ingresos)
        try:
            await page.goto("http://127.0.0.1:8000/movimientos/ingresos/")
            await page.wait_for_timeout(2000)
            await page.evaluate("if(window.driverObj) window.driverObj.destroy();")
            await page.evaluate("document.getElementById('btn-nuevo').click()")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=os.path.join(out_dir, "CU-19_Crear_Movimiento.png"))
            await page.evaluate("document.getElementById('btn-cancelar-modal').click()")
            
            # CU-18 Ver historial (Registros)
            await page.evaluate("document.querySelector('.categoria-card').click()")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=os.path.join(out_dir, "CU-18_Historial_Movimientos.png"))
            
            # CU-22 Eliminar movimiento
            await page.evaluate("document.querySelector('.btn-eliminar').click()")
            await page.wait_for_timeout(1000)
            await page.screenshot(path=os.path.join(out_dir, "CU-22_Eliminar_Movimiento_Confirmacion.png"))
        except Exception: pass
        
        # CU-46 Notificaciones (Campana)
        try:
            await page.goto("http://127.0.0.1:8000/perfil/?tab=notificaciones")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=os.path.join(out_dir, "CU-46_Notificaciones.png"))
        except Exception: pass
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())

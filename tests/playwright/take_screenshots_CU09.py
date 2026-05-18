import os
import asyncio
from playwright.async_api import async_playwright

out_dir = r"c:\Users\Usuario\Downloads\GastuDjango\capturas_pruebas\CU-09"
os.makedirs(out_dir, exist_ok=True)

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        
        # 1. Intentar acceder sin autenticación a Categorías
        try:
            await page.goto("http://127.0.0.1:8000/admin-panel/categorias/")
            await page.wait_for_timeout(1500)
            await page.screenshot(path=os.path.join(out_dir, "5_Acceso_No_Autenticado.png"))
        except Exception as e: print("Error 5:", e)

        # Iniciar sesión como administrador
        try:
            await page.goto("http://127.0.0.1:8000/login/")
            await page.fill('input[type="email"]', 'p@p.com')
            await page.fill('input[name="password"]', 'playwright123')
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(3000)
        except Exception as e: print("Error Login:", e)

        # 2. Búsqueda sin coincidencias ("zzzzz")
        try:
            await page.goto("http://127.0.0.1:8000/admin-panel/categorias/?q=zzzzz")
            await page.wait_for_timeout(2000)
            await page.evaluate("if(window.driverObj) window.driverObj.destroy();")
            await page.screenshot(path=os.path.join(out_dir, "6_Busqueda_Sin_Coincidencia.png"))
        except Exception as e: print("Error 6:", e)

        # 3. Filtro de tipo sin resultados
        try:
            # We can use a search string and type to ensure it's empty
            await page.goto("http://127.0.0.1:8000/admin-panel/categorias/?tipo=AHORRO&q=nada_aqui")
            await page.wait_for_timeout(2000)
            await page.evaluate("if(window.driverObj) window.driverObj.destroy();")
            await page.screenshot(path=os.path.join(out_dir, "7_Filtro_Sin_Coincidencia.png"))
        except Exception as e: print("Error 7:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())

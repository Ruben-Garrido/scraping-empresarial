"""Scraping de SPAs y páginas protegidas con Playwright (Chromium headless)."""
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

VIEWPORT = {"width": 1280, "height": 800}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


async def scrape_dynamic(url: str) -> dict:
    """
    Abre la página con Chromium headless, espera a que cargue el JS
    y extrae el texto visible del body.

    Retorna:
        {
            "success": bool,
            "raw_text": str,
            "status_code": int,
            "error": str | None,
        }
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport=VIEWPORT,
            locale="es-CO",
        )
        page = await context.new_page()

        try:
            response = await page.goto(
                url,
                wait_until="networkidle",   # espera a que no haya requests activos
                timeout=40_000,             # 40 segundos máximo
            )

            status_code = response.status if response else 0

            if status_code not in (0, 200):
                return {
                    "success": False,
                    "raw_text": "",
                    "status_code": status_code,
                    "error": f"HTTP {status_code}",
                }

            # Espera extra para frameworks lentos
            await page.wait_for_timeout(3_000)

            raw_text = await page.inner_text("body")

            if not raw_text.strip():
                return {
                    "success": False,
                    "raw_text": "",
                    "status_code": status_code,
                    "error": "Body vacío tras renderizado JS",
                }

            return {
                "success": True,
                "raw_text": raw_text,
                "status_code": status_code,
                "error": None,
            }

        except PWTimeout:
            return {"success": False, "raw_text": "", "status_code": 0, "error": "Playwright timeout"}
        except Exception as e:
            return {"success": False, "raw_text": "", "status_code": 0, "error": str(e)}
        finally:
            await browser.close()

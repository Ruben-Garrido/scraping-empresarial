"""Auto-detección: ¿la página es HTML estático o SPA dinámica?"""
import httpx
from bs4 import BeautifulSoup

# Palabras clave que indican que la página usa un framework JS (SPA)
SPA_SIGNALS = [
    "__next_data__",      # Next.js
    "react",
    "reactdom",
    "__vue__",
    "ng-version",         # Angular
    "window.__state__",
    "window.__store__",
    "id=\"root\"",
    "id=\"app\"",
    "data-reactroot",
]

STATIC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
}


async def detect_page_type(url: str) -> str:
    """
    Devuelve 'static' o 'dynamic'.

    Heurística:
    - Si el texto visible del HTML crudo es < 300 caracteres Y hay señales SPA → 'dynamic'
    - Si el request falla del todo → asumir 'dynamic' (Playwright puede con más casos)
    - En cualquier otro caso → 'static'
    """
    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers=STATIC_HEADERS,
        ) as client:
            response = await client.get(url)

        if response.status_code in (403, 429, 503):
            # Protección anti-bots → probablemente necesita Playwright
            return "dynamic"

        html_lower = response.text.lower()
        soup = BeautifulSoup(response.text, "lxml")
        visible_text = soup.get_text(strip=True)

        has_spa_signal = any(sig in html_lower for sig in SPA_SIGNALS)
        text_too_short = len(visible_text) < 300

        if text_too_short and has_spa_signal:
            return "dynamic"

        return "static"

    except Exception:
        # Si no podemos ni hacer la request, intentemos con Playwright
        return "dynamic"

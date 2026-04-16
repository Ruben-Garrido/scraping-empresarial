"""Scraping de páginas HTML estáticas con httpx + BeautifulSoup."""
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Tags que no aportan contenido de vacantes
REMOVE_TAGS = ["script", "style", "nav", "footer", "header", "noscript", "iframe"]


async def scrape_static(url: str) -> dict:
    """
    Descarga la página y extrae el texto visible.

    Retorna:
        {
            "success": bool,
            "raw_text": str,       # texto limpio de la página
            "status_code": int,
            "error": str | None,
        }
    """
    try:
        async with httpx.AsyncClient(
            timeout=25,
            follow_redirects=True,
            headers=HEADERS,
        ) as client:
            response = await client.get(url)

        if response.status_code == 403:
            return {
                "success": False,
                "raw_text": "",
                "status_code": response.status_code,
                "error": "403 Forbidden — posible protección anti-bots",
            }

        if response.status_code != 200:
            return {
                "success": False,
                "raw_text": "",
                "status_code": response.status_code,
                "error": f"HTTP {response.status_code}",
            }

        soup = BeautifulSoup(response.text, "lxml")

        # Eliminar ruido
        for tag in soup(REMOVE_TAGS):
            tag.decompose()

        raw_text = soup.get_text(separator="\n", strip=True)

        return {
            "success": True,
            "raw_text": raw_text,
            "status_code": response.status_code,
            "error": None,
        }

    except httpx.TimeoutException:
        return {"success": False, "raw_text": "", "status_code": 0, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "raw_text": "", "status_code": 0, "error": str(e)}

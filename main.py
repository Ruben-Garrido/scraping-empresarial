"""
main.py — Orquestador principal del Job Monitor v2.0

Usa CSV para snapshots + OpenAI para extracción de vacantes.

Uso:
    python main.py --csv organizations.csv
    python main.py --csv organizations.csv --tier tier1
    python main.py --csv organizations.csv --dry-run
"""

import asyncio
import argparse
from pathlib import Path

from storage.csv_loader import load_organizations, Organization
from storage.snapshots import get_last_hash, save_snapshot
from storage.vacantes import sync_vacancies_for_org
from utils.mailer import send_new_vacancies_email
from scraper.detector import detect_page_type
from scraper.static_scraper import scrape_static
from scraper.dynamic_scraper import scrape_dynamic
from utils.logger import get_logger
from utils.hasher import compute_hash
from utils.html_to_json import html_to_json_dom
from ai.analyzer import analyze_vacancies

logger = get_logger("job-monitor")

# Pausa entre requests para evitar bloqueos (segundos)
REQUEST_DELAY = 2
AI_DELAY = 1  # Pausa entre calls a OpenAI


# ──────────────────────────────────────────────────────────────────────────────
# Procesamiento de una sola organización
# ──────────────────────────────────────────────────────────────────────────────

async def process_org(org: Organization, dry_run: bool = False) -> dict:
    """
    Ejecuta el ciclo completo para una organización:
    1. Determinar método de scraping
    2. Scraping (estático o dinámico)
    3. Comparar hash vs. snapshot anterior
    4. Si cambió: convertir HTML → JSON y analizar con OpenAI
    5. Guardar vacantes extraídas
    6. Guardar nuevo snapshot

    Retorna un dict con el resultado para el resumen final.
    """
    logger.info(f"📡  {org.name}")
    logger.info(f"     URL : {org.careers_url}")

    result = {
        "org":    org.name,
        "url":    org.careers_url,
        "status": "error",
        "method": org.scrape_method,
        "vacancies": 0,
        "error":  None,
    }

    # ── 1. Determinar método ──────────────────────────────────────────────────
    method = org.scrape_method
    if method == "auto":
        method = await detect_page_type(org.careers_url)
        logger.info(f"     Tipo detectado → {method}")

    result["method"] = method

    # ── 2. Scraping ───────────────────────────────────────────────────────────
    if method == "static":
        scrape_result = await scrape_static(org.careers_url)
    else:
        scrape_result = await scrape_dynamic(org.careers_url)

    if not scrape_result["success"]:
        # Si el scraping estático falló, lo reintentamos con Playwright
        if method == "static":
            logger.warning(f"     ⚠️  Estático falló ({scrape_result['error']}) → reintentando con Playwright")
            scrape_result = await scrape_dynamic(org.careers_url)
            result["method"] = "dynamic (fallback)"

        if not scrape_result["success"]:
            logger.error(f"     ❌  Error definitivo: {scrape_result['error']}")
            result["error"] = scrape_result["error"]
            result["status"] = "error"
            return result

    raw_text = scrape_result["raw_text"]
    logger.debug(f"     Texto extraído: {len(raw_text):,} caracteres")

    # ── 3. Comparar hash ──────────────────────────────────────────────────────
    new_hash  = compute_hash(raw_text)
    last_hash = get_last_hash(org.name)

    if last_hash == new_hash:
        logger.info("     ⏭️  Sin cambios detectados\n")
        result["status"] = "unchanged"
        return result

    # ── 4. Cambio detectado — preparar para IA ────────────────────────────────
    if last_hash is None:
        logger.info("     🆕  Primera ejecución — analizando con OpenAI")
        result["status"] = "first_run"
    else:
        logger.info("     🔔  ¡CAMBIO DETECTADO! — analizando con OpenAI")
        result["status"] = "changed"

    # ── 5. Convertir HTML → JSON DOM ──────────────────────────────────────────
    logger.info("     📄 Convirtiendo HTML a estructura JSON...")
    json_dom = html_to_json_dom(raw_text)

    # ── 6. Analizar con OpenAI ───────────────────────────────────────────────
    if not dry_run:
        vacancies = await analyze_vacancies(org.name, json_dom, org.careers_url)
        
        # Sincronizar (insertar, actualizar, cerrar) y obtener solo el conteo de genuinamente NUEVAS
        new_vacancies_found = sync_vacancies_for_org(org.name, vacancies, org.careers_url)

        result["vacancies"] = new_vacancies_found
        
        if new_vacancies_found > 0:
            logger.info(f"     ✅ {new_vacancies_found} vacantes nuevas extraídas de {len(vacancies)} totales descubiertas hoy")
        else:
            logger.info(f"     ℹ️ {len(vacancies)} vacantes procesadas (0 nuevas para alertar)")

        # Guardar snapshot solo después de procesar con IA
        save_snapshot(org.name, org.careers_url, new_hash, raw_text)
        logger.info("")  # line break

        # Pausa entre calls a OpenAI para respetar rate limits
        await asyncio.sleep(AI_DELAY)
    else:
        logger.info("     [dry-run] No se enviaron datos a OpenAI ni se guardaron vacantes")

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Loop principal
# ──────────────────────────────────────────────────────────────────────────────

async def run(csv_path: Path, tier_filter: str | None, dry_run: bool) -> None:
    logger.info("=" * 60)
    logger.info("🚀  Job Monitor v2.0 — CSV Scraper + OpenAI")
    logger.info("=" * 60)
    logger.info(f"CSV  : {csv_path}")
    if dry_run:
        logger.info("MODE : dry-run (sin análisis OpenAI, sin guardar)")

    # Cargar organizaciones
    organizations = load_organizations(csv_path)
    logger.info(f"Organizaciones cargadas: {len(organizations)}")

    # Aplicar filtro de tier si se especificó
    if tier_filter:
        organizations = [o for o in organizations if o.tier == tier_filter]
        logger.info(f"Filtro tier '{tier_filter}': {len(organizations)} organizaciones")

    if not organizations:
        logger.warning("No hay organizaciones que procesar. Revisa el CSV o el filtro.")
        return

    # Contadores para el resumen
    counts = {
        "changed": 0,
        "first_run": 0,
        "unchanged": 0,
        "error": 0,
    }
    total_vacancies = 0

    # Procesar cada organización
    for org in organizations:
        result = await process_org(org, dry_run=dry_run)
        counts[result["status"]] = counts.get(result["status"], 0) + 1
        total_vacancies += result.get("vacancies", 0)
        await asyncio.sleep(REQUEST_DELAY)

    # ── Resumen final ─────────────────────────────────────────────────────────
    total = len(organizations)
    logger.info("=" * 60)
    logger.info("📊  RESUMEN DE EJECUCIÓN")
    logger.info(f"     Total procesadas : {total}")
    logger.info(f"     Primera vez      : {counts.get('first_run', 0)}")
    logger.info(f"     Con cambios  🔔  : {counts.get('changed', 0)}")
    logger.info(f"     Sin cambios      : {counts.get('unchanged', 0)}")
    logger.info(f"     Errores      ❌  : {counts.get('error', 0)}")
    logger.info(f"     Nuevas vacantes  : {total_vacancies}")
    logger.info("=" * 60)

    # Enviar correo si hay nuevas vacantes y no es dry-run
    if total_vacancies > 0 and not dry_run:
        logger.info("📧 Enviando notificación por correo...")
        success = send_new_vacancies_email(total_vacancies)
        if success:
            logger.info("✅ Correo enviado correctamente.")
        else:
            logger.error("❌ Falló el envío del correo.")


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Job Monitor v2.0 — Scraping + análisis OpenAI de vacantes"
    )
    parser.add_argument(
        "--csv",
        default="organizations.csv",
        help="Ruta al archivo CSV con las organizaciones (default: organizations.csv)",
    )
    parser.add_argument(
        "--tier",
        choices=["tier1", "tier2"],
        default=None,
        help="Filtrar por tier (por defecto procesa todos)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ejecuta el scraping pero NO analiza con OpenAI ni guarda",
    )
    args = parser.parse_args()

    asyncio.run(run(
        csv_path=Path(args.csv),
        tier_filter=args.tier,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()

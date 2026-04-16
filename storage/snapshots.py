"""Gestión de snapshots en CSV para monitoreo de cambios."""
import csv
from pathlib import Path
from datetime import datetime


SNAPSHOTS_CSV = Path(__file__).resolve().parents[1] / "snapshots.csv"


def load_snapshots() -> dict:
    """
    Lee snapshots.csv y retorna un dict: {org_name: {hash, timestamp, ...}}
    """
    snapshots = {}
    if not SNAPSHOTS_CSV.exists():
        return snapshots
    
    try:
        with open(SNAPSHOTS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                org_name = row.get("org_name", "").strip()
                if org_name:
                    snapshots[org_name] = {
                        "url": row.get("careers_url", ""),
                        "hash": row.get("content_hash", ""),
                        "last_checked": row.get("last_checked", ""),
                        "raw_text_snip": row.get("raw_text_snip", ""),
                    }
    except Exception as e:
        print(f"Error leyendo snapshots.csv: {e}")
    
    return snapshots


def get_last_hash(org_name: str) -> str | None:
    """Retorna el último hash guardado para esta organización, o None si es nueva."""
    snapshots = load_snapshots()
    return snapshots.get(org_name, {}).get("hash")


def save_snapshot(org_name: str, careers_url: str, content_hash: str, raw_text: str) -> None:
    """Inserta o actualiza un snapshot en snapshots.csv."""
    
    snip = raw_text[:500].replace("\n", " ") if raw_text else ""
    now = datetime.utcnow().isoformat()
    
    # Leer snapshots existentes
    snapshots = load_snapshots()
    
    # Actualizar o agregar
    snapshots[org_name] = {
        "url": careers_url,
        "hash": content_hash,
        "last_checked": now,
        "raw_text_snip": snip,
    }
    
    # Escribir de vuelta
    try:
        with open(SNAPSHOTS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "org_name", "careers_url", "content_hash", "raw_text_snip", "last_checked"
            ])
            writer.writeheader()
            
            for name, data in snapshots.items():
                writer.writerow({
                    "org_name": name,
                    "careers_url": data["url"],
                    "content_hash": data["hash"],
                    "raw_text_snip": data["raw_text_snip"],
                    "last_checked": data["last_checked"],
                })
    except Exception as e:
        print(f"Error guardando snapshot: {e}")

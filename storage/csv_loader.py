"""Carga y validación del archivo CSV de organizaciones."""
import csv
from dataclasses import dataclass, field
from pathlib import Path


REQUIRED_COLUMNS = {"organization_name", "careers_url"}

VALID_TIERS = {"tier1", "tier2"}
VALID_METHODS = {"auto", "static", "dynamic"}


@dataclass
class Organization:
    name: str
    careers_url: str
    tier: str = "tier1"
    scrape_method: str = "auto"   # auto | static | dynamic
    hr_contact: str = ""
    notes: str = ""


def load_organizations(csv_path: str | Path) -> list[Organization]:
    """
    Lee el CSV y devuelve una lista de Organization.
    Valida que las columnas requeridas existan y que los valores
    de tier/scrape_method sean reconocidos.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV no encontrado: {csv_path}")

    organizations: list[Organization] = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # Validar encabezados
        headers = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - headers
        if missing:
            raise ValueError(f"El CSV no tiene columnas requeridas: {missing}")

        for i, row in enumerate(reader, start=2):  # fila 1 = encabezado
            name = row["organization_name"].strip()
            url  = row["careers_url"].strip()

            if not name or not url:
                print(f"  ⚠️  Fila {i}: nombre o URL vacío — se omite")
                continue

            tier   = row.get("tier", "tier1").strip().lower() or "tier1"
            method = row.get("scrape_method", "auto").strip().lower() or "auto"

            if tier not in VALID_TIERS:
                print(f"  ⚠️  Fila {i} ({name}): tier '{tier}' no válido — usando 'tier1'")
                tier = "tier1"

            if method not in VALID_METHODS:
                print(f"  ⚠️  Fila {i} ({name}): scrape_method '{method}' no válido — usando 'auto'")
                method = "auto"

            organizations.append(Organization(
                name=name,
                careers_url=url,
                tier=tier,
                scrape_method=method,
                hr_contact=row.get("hr_contact", "").strip(),
                notes=row.get("notes", "").strip(),
            ))

    return organizations

"""Gestión de vacantes extraídas en CSV."""
import csv
from pathlib import Path
from datetime import datetime


VACANTES_CSV = Path(__file__).resolve().parents[1] / "vacantes.csv"


def save_vacancy(
    org_name: str,
    title: str,
    description: str = "",
    requirements: str = "",
    salary: str = "",
    location: str = "",
    source_url: str = "",
    extracted_date: str | None = None,
) -> None:
    """
    Agrega una nueva vacante a vacantes.csv.
    Si el archivo no existe, lo crea con headers.
    """
    
    if extracted_date is None:
        extracted_date = datetime.utcnow().isoformat()
    
    # Verificar si el archivo existe
    file_exists = VACANTES_CSV.exists()
    
    try:
        with open(VACANTES_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "org_name", "title", "description", "requirements", 
                "salary", "location", "source_url", "extracted_date"
            ])
            
            # Escribir header solo si el archivo es nuevo
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                "org_name": org_name,
                "title": title,
                "description": description,
                "requirements": requirements,
                "salary": salary,
                "location": location,
                "source_url": source_url,
                "extracted_date": extracted_date,
            })
    except Exception as e:
        print(f"Error guardando vacante: {e}")


def get_vacancies_by_org(org_name: str) -> list[dict]:
    """Retorna todas las vacantes de una organización."""
    if not VACANTES_CSV.exists():
        return []
    
    vacancies = []
    try:
        with open(VACANTES_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("org_name", "").strip() == org_name:
                    vacancies.append(row)
    except Exception as e:
        print(f"Error leyendo vacantes: {e}")
    
    return vacancies

"""Gestión de vacantes extraídas en CSV."""
import csv
import hashlib
from pathlib import Path
from datetime import datetime


VACANTES_CSV = Path(__file__).resolve().parents[1] / "vacantes.csv"

FIELDNAMES = [
    "job_id", "content_hash", "org_name", "title", "description", 
    "requirements", "salary", "location", "source_url", "status", 
    "extracted_date", "updated_date", "closed_date"
]

def _generate_job_id(org_name: str, title: str) -> str:
    """Genera ID único y determinista robusto (ignora mayúsculas y espacios extra)."""
    clean_org = " ".join(org_name.lower().split())
    clean_title = " ".join(title.lower().split())
    text = f"{clean_org}|{clean_title}"
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]

def _generate_content_hash(description: str, requirements: str, salary: str, location: str) -> str:
    """Genera hash para detectar cambios en el contenido descriptivo de la vacante."""
    text = f"{description}|{requirements}|{salary}|{location}"
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]

def get_all_vacancies_dict() -> dict:
    """Carga todas las vacantes existentes en un diccionario indexado por job_id."""
    vacancies = {}
    if not VACANTES_CSV.exists():
        return vacancies
        
    try:
        with open(VACANTES_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Soporte de migración si el archivo viejo no tenía job_id
                job_id = row.get("job_id")
                if not job_id:
                    org = row.get("org_name", "")
                    title = row.get("title", "")
                    if not org or not title:
                        continue
                    job_id = _generate_job_id(org, title)
                    row["job_id"] = job_id
                    row["content_hash"] = _generate_content_hash(
                        row.get("description", ""), row.get("requirements", ""),
                        row.get("salary", ""), row.get("location", "")
                    )
                    row["status"] = row.get("status") or "activa"
                    row["updated_date"] = row.get("updated_date") or row.get("extracted_date", "")
                    row["closed_date"] = row.get("closed_date") or ""
                
                vacancies[job_id] = row
    except Exception as e:
        print(f"Error cargando base de datos de vacantes: {e}")
        
    return vacancies

def _save_all_vacancies(vacancies_dict: dict) -> None:
    """Sobrescribe el CSV completo con el diccionario de vacantes actualizado."""
    try:
        with open(VACANTES_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            
            for job_id, row in vacancies_dict.items():
                # Limpiar y asegurar que todos los campos del FIELDNAMES existan en la row
                clean_row = {field: row.get(field, "") for field in FIELDNAMES}
                writer.writerow(clean_row)
    except Exception as e:
        print(f"Error guardando base de datos de vacantes: {e}")

def sync_vacancies_for_org(org_name: str, current_vacancies: list, source_url: str = "") -> int:
    """
    Concilia las vacantes encontradas hoy con la base de datos CSV.
    Identifica nuevas, modificaciones y eliminadas (las cierra).
    Retorna la cantidad de vacantes genuinamente NUEVAS descubiertas.
    """
    all_vacancies = get_all_vacancies_dict()
    now_iso = datetime.utcnow().isoformat()
    
    current_job_ids = set()
    new_vacancies_count = 0
    
    # 1. Cruzar lo que descubrimos hoy (current_vacancies)
    for v in current_vacancies:
        title = v.get("title", "")
        if not title:
            continue
            
        desc = v.get("description", "")
        req = v.get("requirements", "")
        sal = v.get("salary", "")
        loc = v.get("location", "")
        
        job_id = _generate_job_id(org_name, title)
        c_hash = _generate_content_hash(desc, req, sal, loc)
        current_job_ids.add(job_id)
        
        if job_id not in all_vacancies:
            # CASO 1: Vacante completamente nueva
            all_vacancies[job_id] = {
                "job_id": job_id,
                "content_hash": c_hash,
                "org_name": org_name,
                "title": title,
                "description": desc,
                "requirements": req,
                "salary": sal,
                "location": loc,
                "source_url": source_url,
                "status": "activa",
                "extracted_date": now_iso,
                "updated_date": now_iso,
                "closed_date": ""
            }
            new_vacancies_count += 1
            
        else:
            # La vacante ya existía. Analizar si mutó.
            existing = all_vacancies[job_id]
            if existing.get("content_hash") != c_hash:
                # CASO 2: La editaron (modificada)
                existing["content_hash"] = c_hash
                existing["description"] = desc
                existing["requirements"] = req
                existing["salary"] = sal
                existing["location"] = loc
                existing["source_url"] = source_url
                existing["updated_date"] = now_iso
                existing["status"] = "activa"  # por si estaba cerrada y la reabrieron
                existing["closed_date"] = ""
            else:
                # CASO 3: Sanción Intacta
                if existing.get("status") != "activa":
                    # Si estaba cerrada, la reabrieron pero no cambiaron texto
                    existing["status"] = "activa"
                    existing["updated_date"] = now_iso
                    existing["closed_date"] = ""

    # 2. Encontrar eliminadas (estaban activas pero no vinieron en la corrida de hoy)
    for job_id, v_data in all_vacancies.items():
        if v_data.get("org_name") == org_name:
            if job_id not in current_job_ids and v_data.get("status") == "activa":
                # CASO 4: Vacante eliminada (cerrada)
                v_data["status"] = "cerrada"
                v_data["closed_date"] = now_iso

    # 3. Guardar el estado consolidado de TODA la base de datos
    _save_all_vacancies(all_vacancies)
    
    return new_vacancies_count

def get_vacancies_by_org(org_name: str) -> list[dict]:
    """Retorna todas las vacantes de una organización."""
    vacancies = get_all_vacancies_dict()
    return [v for v in vacancies.values() if v.get("org_name") == org_name]

"""AI Analyzer — Extrae vacantes usando OpenAI (versión simplificada)."""
import asyncio
import json
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

from utils.logger import get_logger

logger = get_logger("ai-analyzer")

# Cargar variables de entorno
load_dotenv()


class VacancyAnalyzer:
    """Análisis de vacantes con OpenAI gpt-4o-mini (versión simplificada)."""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in .env")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
    
    async def analyze_vacancies(
        self,
        org_name: str,
        json_dom: dict,
        source_url: str,
    ) -> list[dict]:
        """
        Extrae vacantes directamente del JSON DOM.
        
        Estrategia simplificada:
        1. Envía JSON DOM a OpenAI
        2. Pide extraer TODAS las vacantes de tech/dev
        
        Args:
            org_name: Nombre de la organización
            json_dom: Estructura JSON del DOM
            source_url: URL original
        
        Returns:
            Lista de vacantes: [{title, description, requirements, salary, location}, ...]
        """
        
        logger.info(f"     🤖 Analizando vacantes con OpenAI para {org_name}")
        
        try:
            vacancies = await self._extract_vacancies_direct(org_name, json_dom, source_url)
            
            if vacancies:
                logger.info(f"     ✅ {len(vacancies)} vacantes extraídas")
            else:
                logger.info(f"     ℹ️  No se encontraron vacantes de tech/dev")
            
            return vacancies
        
        except Exception as e:
            logger.error(f"     ❌ Error en análisis OpenAI: {str(e)}")
            return []
    
    async def _extract_vacancies_direct(
        self,
        org_name: str,
        json_dom: dict,
        source_url: str,
    ) -> list[dict]:
        """
        Extrae TODAS las vacantes directamente del JSON DOM.
        """
        
        # Limitar tamaño del JSON para no exceder contexto
        json_str = json.dumps(json_dom, ensure_ascii=False)
        if len(json_str) > 8000:
            json_str = json_str[:8000] + "...truncated"
        
        prompt = f"""Del siguiente JSON (estructura DOM de HTML de una página de carreras/empleos), 
extrae TODAS las vacantes o PUESTOS DE TRABAJO disponibles que sean de TECH/SOFTWARE/DESARROLLO/INGENIERIA DE SISTEMAS/INFRAESTRUCTURA/DEVOPS.

Para cada vacante encontrada, extrae:
- title: Título del puesto (ej: "Senior Developer", "Full-stack Engineer")
- description: Descripción breve del trabajo (máximo 200 caracteres)
- requirements: Requisitos técnicos principales separados por comas
- salary: Rango salarial o moneda (si está disponible, si no disponible dejar vacío)
- location: Ubicación geográfica (país, ciudad, remoto, etc.)

Retorna un JSON array válido con SOLO objeto vacío [] si no hay vacantes:
[
  {{"title": "...", "description": "...", "requirements": "...", "salary": "...", "location": "..."}},
  ...
]

IMPORTANTE:
- Si NO HAY VACANTES o TODAS son de áreas NO TECH (HR, Sales, Marketing, etc.), retorna: []
- SOLO vacantes relacionadas con tech/dev/software/engineering
- Si el JSON no contiene texto claro de vacantes, retorna: []

DOM JSON:
{json_str}
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Más bajo para respuestas consistentes
                max_tokens=2500,
            )
            
            content = response.choices[0].message.content
            
            # Limpiar respuesta (a veces OpenAI devuelve con markdown)
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Parsear JSON
            vacancies = json.loads(content) if content else []
            
            # Validar que sea una lista
            if not isinstance(vacancies, list):
                vacancies = []
            
            # Agregar campos adicionales y limpiar
            cleaned_vacancies = []
            for v in vacancies:
                if isinstance(v, dict) and v.get("title"):
                    cleaned_vacancies.append({
                        "title": v.get("title", "").strip()[:100],
                        "description": v.get("description", "").strip()[:300],
                        "requirements": v.get("requirements", "").strip()[:200],
                        "salary": v.get("salary", "").strip()[:50],
                        "location": v.get("location", "").strip()[:100],
                        "org_name": org_name,
                        "source_url": source_url,
                    })
            
            return cleaned_vacancies
        
        except json.JSONDecodeError as e:
            logger.warning(f"     ⚠️  Error parseando JSON de vacantes: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"     ❌ Error en extracción: {str(e)}")
            return []


# Instancia global
analyzer = VacancyAnalyzer()


async def analyze_vacancies(
    org_name: str,
    json_dom: dict,
    source_url: str,
) -> list[dict]:
    """
    Función pública que expone el analizador.
    """
    return await analyzer.analyze_vacancies(org_name, json_dom, source_url)

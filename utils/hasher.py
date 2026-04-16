"""Hash MD5 para comparar contenido de páginas."""
import hashlib


def compute_hash(text: str) -> str:
    """
    Normaliza el texto y calcula su hash MD5.
    Normalizar (lower + colapsar espacios) evita falsos positivos
    por cambios menores de formato.
    """
    normalized = " ".join(text.lower().split())
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()

"""Conversión de HTML a estructura JSON DOM para análisis de IA."""
import json
from bs4 import BeautifulSoup
from typing import Any


def html_to_json_dom(raw_html: str, max_depth: int = 10) -> dict:
    """
    Convierte HTML a estructura JSON que representa el árbol DOM.
    
    Preserva:
    - Estructura jerárquica de tags (enfoque en divs)
    - Atributos importantes (class, id)
    - Textos dentro de elementos
    - Contexto sin ruido excesivo
    
    Args:
        raw_html: HTML crudo como string
        max_depth: Profundidad máxima de recursión (evita órboles enormes)
    
    Returns:
        dict con estructura: {
            "tag": "html",
            "attributes": {"class": "...", "id": "..."},
            "text": "...",
            "children": [...]
        }
    """
    try:
        soup = BeautifulSoup(raw_html, "lxml")
        root = soup.find("body") or soup
        return _tag_to_json(root, depth=0, max_depth=max_depth)
    except Exception as e:
        return {
            "tag": "error",
            "error": str(e),
            "text": "Error al parsear HTML"
        }


def _tag_to_json(tag: Any, depth: int = 0, max_depth: int = 10) -> dict:
    """Convierte recursivamente un tag de BeautifulSoup a JSON."""
    
    # Limitar profundidad
    if depth > max_depth:
        return {"tag": "depth_limit", "text": "..."}
    
    # Si es texto puro
    if isinstance(tag, str):
        text = tag.strip()
        return {"text": text} if text else None
    
    # Si no tiene name, es texto
    if not hasattr(tag, "name"):
        return None
    
    result = {
        "tag": tag.name,
    }
    
    # Atributos relevantes
    attrs = tag.attrs if hasattr(tag, "attrs") else {}
    important_attrs = {k: v for k, v in attrs.items() if k in ["class", "id", "data-*"]}
    if important_attrs:
        result["attributes"] = important_attrs
    
    # Texto directo (sin hijos)
    text_content = tag.get_text(strip=True)
    if text_content and len(text_content) < 500:  # Limitar longitud de texto
        result["text"] = text_content[:200]  # truncar muy largo
    
    # Children (recursivamente)
    children = []
    if hasattr(tag, "children"):
        for child in tag.children:
            # Ignorar comentarios y scripts
            if hasattr(child, "name"):
                if child.name in ["script", "style", "noscript"]:
                    continue
            
            child_json = _tag_to_json(child, depth + 1, max_depth)
            if child_json:
                children.append(child_json)
    
    if children:
        result["children"] = children
    
    return result


def json_dom_to_text(json_dom: dict, indent: int = 0) -> str:
    """
    Convierte JSON DOM de vuelta a una representación legible en texto.
    Útil para debugging.
    """
    if not isinstance(json_dom, dict):
        return ""
    
    indent_str = "  " * indent
    
    tag = json_dom.get("tag", "unknown")
    text = json_dom.get("text", "")
    
    line = f"{indent_str}<{tag}>"
    if text:
        line += f" {text[:50]}"
    
    lines = [line]
    
    children = json_dom.get("children", [])
    for child in children:
        lines.append(json_dom_to_text(child, indent + 1))
    
    return "\n".join(filter(None, lines))

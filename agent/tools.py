"""Tool de búsqueda semántica (search_faq) y prompt del sistema para el agente."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Reutilizar conexión y configuración de BD de Persona A (loader/db.py)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "loader"))
from db import get_connection, get_embedding_model_name

DEFAULT_TOP_K = 3
DEFAULT_MAX_DISTANCE = float(os.environ.get("FAQ_MAX_DISTANCE", "0.55"))
_MODEL = None


def get_embedding_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer(get_embedding_model_name())
    return _MODEL


# Esquema estándar para function calling / tools
SEARCH_FAQ_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_faq",
        "description": "Busca preguntas frecuentes, políticas, precios y requisitos de Parachute S.A.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Pregunta o texto a buscar semánticamente"},
                "top_k": {"type": "integer", "description": "Resultados máximos", "default": DEFAULT_TOP_K},
            },
            "required": ["query"],
        },
    },
}

SYSTEM_PROMPT = """Eres el asistente oficial de atención al cliente de Parachute S.A.
Reglas estrictas:
1. Para responder sobre precios, políticas, seguridad o logística, DEBES consultar `search_faq`.
2. Responde ÚNICAMENTE basándote en lo que devuelva `search_faq`. Prohibido inventar datos.
3. Si no hay resultados o la información no coincide, di explícitamente: "Lo siento, no tengo esa información en mi base de conocimientos."
4. Sé profesional, conciso y cordial."""

SEARCH_SQL = """
    SELECT faq_code, category, question, answer, embedding <=> %s AS distance
    FROM faqs ORDER BY distance ASC LIMIT %s;
"""


def search_faq(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    max_distance: Optional[float] = DEFAULT_MAX_DISTANCE,
    conn: Optional[Any] = None,
) -> list[dict[str, Any]]:
    """Ejecuta búsqueda semántica por similitud coseno en pgvector.

    Args:
        query: Pregunta o texto a buscar.
        top_k: Cantidad máxima de resultados a recuperar (por defecto 3).
        max_distance: Umbral de distancia coseno máxima; si distance > max_distance, is_relevant=False.
        conn: Conexión opcional a Postgres (si es None, abre y cierra una automáticamente).

    Returns:
        Lista de dicts con: faq_code, category, question, answer, distance, is_relevant.
    """
    query = query.strip()
    if not query:
        return []

    embedding = get_embedding_model().encode(query, normalize_embeddings=True)
    should_close = conn is None
    conn = conn or get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(SEARCH_SQL, (embedding, top_k))
            rows = cur.fetchall()

        return [
            {
                "faq_code": code,
                "category": cat,
                "question": q,
                "answer": a,
                "distance": round(float(dist), 4),
                "is_relevant": max_distance is None or float(dist) <= max_distance,
            }
            for code, cat, q, a, dist in rows
        ]
    finally:
        if should_close:
            conn.close()


def format_search_results(results: list[dict[str, Any]]) -> str:
    """Formatea las FAQs relevantes en texto plano para inyectar como contexto al LLM.

    Args:
        results: Lista de diccionarios retornada por search_faq.

    Returns:
        String formateado con las FAQs relevantes o mensaje de no coincidencia.
    """
    hits = [r for r in results if r.get("is_relevant", True)]
    if not hits:
        return "No se encontraron preguntas frecuentes relevantes en la base de conocimientos."

    return "\n\n".join(
        f"[{r['faq_code']}] {r['question']}\n{r['answer']}" for r in hits
    )
"""Tests para la tool search_faq y utilidades del agente."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from tools import (
    SEARCH_FAQ_TOOL_DEFINITION,
    SYSTEM_PROMPT,
    format_search_results,
    search_faq,
)


def test_tool_definition_and_prompt():
    """Valida la estructura del schema para function calling y directrices del prompt."""
    fn = SEARCH_FAQ_TOOL_DEFINITION["function"]
    assert fn["name"] == "search_faq"
    assert "query" in fn["parameters"]["required"]
    assert "search_faq" in SYSTEM_PROMPT
    assert "Parachute S.A." in SYSTEM_PROMPT


def test_format_search_results():
    """Verifica el formateo de resultados para el LLM."""
    assert "No se encontraron" in format_search_results([])

    hits = [
        {"faq_code": "FAQ-001", "question": "¿Lugar?", "answer": "Puerto San José", "is_relevant": True},
        {"faq_code": "FAQ-002", "question": "¿Clima?", "answer": "Soleado", "is_relevant": False},
    ]
    formatted = format_search_results(hits)
    assert "FAQ-001" in formatted and "Puerto San José" in formatted
    assert "FAQ-002" not in formatted


def test_search_faq_empty():
    """Verifica que consultas vacías no ejecuten búsquedas."""
    assert search_faq("") == []
    assert search_faq("   ") == []


def test_search_faq_mocked():
    """Valida el filtrado de relevancia por umbral con conexión simulada."""
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = [
        ("FAQ-001", "General", "¿Lugar?", "En la costa.", 0.2),
        ("FAQ-002", "General", "¿Vuelos?", "Sí.", 0.8),
    ]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    with patch("tools.get_embedding_model") as mock_model:
        mock_model.return_value.encode.return_value = [0.1] * 384
        results = search_faq("¿Dónde?", top_k=2, max_distance=0.55, conn=mock_conn)

    assert len(results) == 2
    assert results[0]["faq_code"] == "FAQ-001" and results[0]["is_relevant"] is True
    assert results[1]["faq_code"] == "FAQ-002" and results[1]["is_relevant"] is False


def test_search_faq_integration_real_db():
    """Prueba de integración con pgvector si el contenedor está levantado."""
    try:
        from tools import get_connection
        conn = get_connection()
    except Exception:
        pytest.skip("Postgres/pgvector no disponible en localhost:5432.")

    try:
        results = search_faq("¿Dónde es el salto?", top_k=2, conn=conn)
        assert len(results) >= 1
        assert "faq_code" in results[0]
    finally:
        conn.close()

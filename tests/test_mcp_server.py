"""Tests del servidor MCP (mcp_server/server.py). No requieren API de OpenAI.

`search_faq` necesita Postgres levantado y cargado (igual que tests/test_tools.py).
"""

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp_server"))

import server  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def test_server_exposes_both_tools():
    tools = _run(server.mcp.list_tools())
    assert {t.name for t in tools} == {"search_faq", "check_weather"}


def test_tool_schemas_have_descriptions():
    for tool in _run(server.mcp.list_tools()):
        assert tool.description, f"{tool.name} no tiene descripción"


def test_check_weather_past_date_returns_error_and_logs(caplog):
    with caplog.at_level(logging.INFO, logger="parachute.mcp"):
        result = _run(server.check_weather("2020-01-01"))
    assert "ya pasó" in result
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "CALL  check_weather" in messages
    assert "OK    check_weather" in messages


def test_check_weather_invalid_format():
    result = _run(server.check_weather("mañana"))
    assert "YYYY-MM-DD" in result


def test_search_faq_finds_weight_limit(caplog):
    with caplog.at_level(logging.INFO, logger="parachute.mcp"):
        result = _run(server.search_faq("¿Cuál es el peso máximo para saltar?"))
    assert "100 kg" in result
    assert any("CALL  search_faq" in r.getMessage() for r in caplog.records)

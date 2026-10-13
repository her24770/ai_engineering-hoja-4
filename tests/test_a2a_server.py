"""Tests unitarios y de integración para el servidor A2A (a2a_server/).

No requieren API key de OpenAI ni contenedor de base de datos para correr.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from a2a_server.card import get_agent_card
from a2a_server.server import ParachuteAgentExecutor, create_app


def test_agent_card_metadata_and_skills():
    """Valida que el AgentCard cumpla con todas las especificaciones y recomendaciones."""
    card = get_agent_card(base_url="http://127.0.0.1:9000")

    assert card.name == "Parachute Customer Service Agent"
    assert card.version == "1.0.0"
    assert "text/plain" in card.default_input_modes
    assert "text/plain" in card.default_output_modes
    assert len(card.supported_interfaces) == 1
    assert card.supported_interfaces[0].protocol_binding == "JSONRPC"

    # Verificar que existan exactamente 2 skills
    skill_ids = {s.id for s in card.skills}
    assert skill_ids == {"faqs", "citas_clima"}

    # Verificar detalles de cada skill
    for skill in card.skills:
        assert skill.name
        assert skill.description
        assert len(skill.tags) > 0
        assert len(skill.examples) > 0
        assert "text/plain" in skill.input_modes
        assert "text/plain" in skill.output_modes

    # Verificar la aclaración explícita en la skill de citas
    citas_skill = next(s for s in card.skills if s.id == "citas_clima")
    assert "no realiza reservas" in citas_skill.description.lower()


def test_agent_card_http_endpoint():
    """Valida que el endpoint /.well-known/agent-card.json responda HTTP 200 con el JSON esperado."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/.well-known/agent-card.json")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Parachute Customer Service Agent"
    assert data["version"] == "1.0.0"
    assert len(data.get("skills", [])) == 2


import asyncio

from unittest.mock import AsyncMock, MagicMock, patch

def test_executor_processes_message_and_logs(caplog):
    """Valida que el ejecutor procese la consulta, llame al agente y emita los logs estructurados."""
    async def _test():
        executor = ParachuteAgentExecutor()

        mock_context = MagicMock()
        mock_context.get_user_input.return_value = "¿Cuál es el peso máximo para saltar?"
        mock_context.task_id = "task-test-1234"
        mock_context.context_id = "ctx-test-5678"

        mock_queue = AsyncMock()

        mock_response = {
            "final_output": "El peso máximo permitido es de 100 kg según el manual de seguridad.",
            "tool_calls": [{"name": "faq_worker", "arguments": "{}"}],
        }

        with caplog.at_level(logging.INFO, logger="parachute.a2a"):
            with patch("a2a_server.server.run_query_async", new=AsyncMock(return_value=mock_response)):
                await executor.execute(mock_context, mock_queue)

        # Verificar que el mensaje fue encolado
        assert mock_queue.enqueue_event.called
        enqueued_msg = mock_queue.enqueue_event.call_args[0][0]
        assert "100 kg" in enqueued_msg.parts[0].text

        # Verificar los logs generados
        logs = " ".join(r.getMessage() for r in caplog.records)
        assert "[MENSAJE RECIBIDO]" in logs
        assert "¿Cuál es el peso máximo para saltar?" in logs
        assert "[RESPUESTA EMITIDA]" in logs
        assert "tools: faq_worker" in logs

    asyncio.run(_test())


def test_jsonrpc_send_message_endpoint():
    """Valida el flujo end-to-end de envío de mensaje vía JSON-RPC a través de HTTP."""
    mock_response = {
        "final_output": "Condiciones climáticas APTAS para saltar este sábado.",
        "tool_calls": [{"name": "weather_worker", "arguments": "{}"}],
    }

    with patch("a2a_server.server.run_query_async", new=AsyncMock(return_value=mock_response)):
        app = create_app()
        client = TestClient(app)

        rpc_payload = {
            "jsonrpc": "2.0",
            "id": 42,
            "method": "SendMessage",
            "params": {
                "message": {
                    "message_id": "msg-001",
                    "role": 1,
                    "parts": [{"text": "¿Puedo saltar este sábado?"}],
                }
            },
        }

        response = client.post("/", json=rpc_payload, headers={"a2a-version": "1.0"})
        assert response.status_code == 200

        data = response.json()
        assert "result" in data
        assert "message" in data["result"]
        parts = data["result"]["message"]["parts"]
        assert any("APTAS" in p.get("text", "") for p in parts)

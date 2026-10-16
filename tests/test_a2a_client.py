"""Tests del cliente A2A (a2a_client/). No requieren servidores ni API key."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from a2a.helpers import new_text_message
from a2a.types import Role, StreamResponse

from a2a_client.client import send_text


class FakeClient:
    """Cliente A2A falso que emite una respuesta fija y guarda la petición recibida."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.requests = []

    async def send_message(self, request):
        self.requests.append(request)
        yield StreamResponse(message=new_text_message(self.reply))


def test_send_text_returns_agent_reply_and_sends_user_message():
    client = FakeClient("Hola desde el agente")

    reply = asyncio.run(send_text(client, "¿Qué es Parachute?", "ctx-123"))

    assert reply == "Hola desde el agente"
    message = client.requests[0].message
    assert message.role == Role.ROLE_USER
    assert message.context_id == "ctx-123"
    assert message.parts[0].text == "¿Qué es Parachute?"

"""Cliente A2A en terminal de Parachute S.A.

Envía cada mensaje por A2A al servidor y este usa las herramientas del servidor MCP
Lee la URL del servidor desde A2A_SERVER_URL.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

from a2a.client import ClientConfig, create_client
from a2a.helpers import get_stream_response_text, new_text_message
from a2a.types import Role, SendMessageRequest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

A2A_SERVER_URL = os.getenv("A2A_SERVER_URL", "http://127.0.0.1:9000")
A2A_TIMEOUT_SECONDS = float(os.getenv("A2A_TIMEOUT_SECONDS", "120"))


async def send_text(client, text: str, context_id: str) -> str:
    """Envía un mensaje de usuario al agente remoto y devuelve el texto de la respuesta."""
    message = new_text_message(text, context_id=context_id, role=Role.ROLE_USER)
    request = SendMessageRequest(message=message)

    parts: list[str] = []
    async for response in client.send_message(request):
        chunk = get_stream_response_text(response)
        if chunk:
            parts.append(chunk)
    return "\n".join(parts)


async def _amain() -> None:
    print(f"Conectando al servidor A2A en {A2A_SERVER_URL} ...")
    http = httpx.AsyncClient(timeout=httpx.Timeout(A2A_TIMEOUT_SECONDS))
    client = await create_client(A2A_SERVER_URL, ClientConfig(httpx_client=http))

    print("\n--- Cliente A2A de Parachute S.A. ---")
    print(f"Servidor: {A2A_SERVER_URL}")
    print("Escribe tu solicitud. Para salir presiona Ctrl-C o escribe 'Bye'.\n")

    # Mismo context_id durante toda la sesión para que el servidor agrupe la conversación.
    context_id = str(uuid.uuid4())

    try:
        while True:
            try:
                pregunta = await asyncio.to_thread(input, "Tu mensaje: ")
            except (KeyboardInterrupt, EOFError):
                print("\nHasta luego.")
                break

            if not pregunta or pregunta.lower() == "bye":
                print("Hasta luego.")
                break

            print("Pensando...")
            try:
                respuesta = await send_text(client, pregunta, context_id)
                print(f"\nAgente/Respuesta Final: {respuesta}\n")
            except Exception as e:
                print(f"Error al comunicarse con el servidor A2A: {e}\n")
    finally:
        await client.close()
        await http.aclose()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        print("\nHasta luego.")


if __name__ == "__main__":
    main()

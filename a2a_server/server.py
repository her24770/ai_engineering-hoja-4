"""Servidor A2A de Parachute S.A.

Expone el Manager Agent (sistema multi-agente centralizado) como un solo
agente unificado y compatible con el protocolo A2A (Agent-to-Agent).

Publica:
  - AgentCard en: GET /.well-known/agent-card.json
  - Endpoint JSON-RPC en: POST / (y /rpc)

Emite logs legibles y detallados para cada mensaje recibido y respondido.

Uso:
    python a2a_server/server.py
    # -> http://127.0.0.1:9000
"""

from __future__ import annotations

import contextlib
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import uvicorn
from starlette.applications import Starlette

from a2a.helpers import new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore

# Asegurar que la raíz del proyecto esté en el path para imports de paquetes
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

from agent.agent_centralized import manager_session, run_query_async
from a2a_server.card import get_agent_card

# Configuración de Logging para A2A
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("parachute.a2a")


class ParachuteAgentExecutor(AgentExecutor):
    """Ejecutor A2A que conecta las peticiones entrantes con el Manager Agent."""

    def __init__(self, manager_agent=None) -> None:
        self.manager_agent = manager_agent

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Procesa una consulta del usuario mediante el Manager Agent y emite logs."""
        user_input = context.get_user_input()
        task_id = context.task_id or "sin-id"

        # Log del mensaje recibido
        logger.info('[MENSAJE RECIBIDO] (task=%s) "%s"', task_id[:8], user_input)
        start_time = time.perf_counter()

        try:
            # Reutiliza el Manager Agent persistente si está activo en lifespan,
            # o abre una sesión por petición si se corre de forma aislada.
            result = await run_query_async(user_input, self.manager_agent)
            final_text = result.get("final_output", "")
            tool_calls = result.get("tool_calls", [])

            # Herramientas llamadas por el Manager Agent
            tools_used = [t.get("name") for t in tool_calls if t.get("name")]
            tools_summary = ", ".join(tools_used) if tools_used else "ninguna"

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            preview = final_text.replace("\n", " ")[:120]

            # Log de la respuesta emitida
            logger.info(
                '[RESPUESTA EMITIDA] en %.0f ms (tools: %s) -> "%s"',
                elapsed_ms,
                tools_summary,
                preview,
            )

            # Construir y encolar el mensaje de respuesta de A2A
            response_message = new_text_message(
                text=final_text,
                task_id=context.task_id,
                context_id=context.context_id,
            )
            await event_queue.enqueue_event(response_message)

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.exception('[ERROR EN EJECUCIÓN] tras %.0f ms: %s', elapsed_ms, exc)
            error_message = new_text_message(
                text=f"Lo sentimos, ocurrió un error interno al procesar su solicitud: {exc}",
                task_id=context.task_id,
                context_id=context.context_id,
            )
            await event_queue.enqueue_event(error_message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Maneja solicitudes de cancelación de tareas."""
        logger.info('[CANCELACIÓN SOLICITADA] task=%s', context.task_id)


def create_app(
    base_url: str = "http://127.0.0.1:9000",
    executor: ParachuteAgentExecutor | None = None,
) -> Starlette:
    """Crea y configura la aplicación Starlette con el protocolo A2A."""
    card = get_agent_card(base_url=base_url)
    active_executor = executor or ParachuteAgentExecutor()
    task_store = InMemoryTaskStore()

    handler = DefaultRequestHandler(
        agent_executor=active_executor,
        task_store=task_store,
        agent_card=card,
    )

    # Lifespan: Mantiene la sesión MCP activa durante la vida del servidor
    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        logger.info("Iniciando sesión del Manager Agent y conectando a MCP...")
        try:
            async with manager_session() as agent:
                active_executor.manager_agent = agent
                logger.info("Manager Agent conectado con éxito a MCP. Servidor A2A listo.")
                yield
        except Exception as exc:
            logger.warning(
                "No se pudo conectar a MCP al inicio (%s). Se reintentará en cada mensaje.",
                exc,
            )
            yield
        finally:
            active_executor.manager_agent = None
            logger.info("Sesión del Manager Agent finalizada.")

    # Rutas para el AgentCard y el protocolo JSON-RPC
    card_routes = create_agent_card_routes(card)
    jsonrpc_routes = create_jsonrpc_routes(
        handler,
        rpc_url="/",
        enable_v0_3_compat=True,
    )

    return Starlette(
        routes=card_routes + jsonrpc_routes,
        lifespan=lifespan,
    )


def main() -> None:
    host = os.getenv("A2A_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("A2A_SERVER_PORT", "9000"))
    base_url = f"http://{host}:{port}"

    logger.info("==================================================")
    logger.info("Iniciando Servidor A2A de Parachute S.A.")
    logger.info("Dirección base: %s", base_url)
    logger.info("AgentCard URL:  %s/.well-known/agent-card.json", base_url)
    logger.info("Endpoint A2A:   %s/", base_url)
    logger.info("==================================================")

    app = create_app(base_url=base_url)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()

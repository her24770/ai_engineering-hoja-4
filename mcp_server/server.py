"""Servidor MCP de Parachute S.A. (transporte Streamable HTTP).

Abstrae en un solo servidor las herramientas que antes vivían dentro de los
agentes:
  - search_faq:    búsqueda semántica en pgvector (agent/tools.py)
  - check_weather: pronóstico Open-Meteo para saltar (agent/tools_weather.py)

Cada ejecución de herramienta emite logs (llamada, resultado/error y duración).

Uso:
    python mcp_server/server.py
    # -> http://127.0.0.1:8000/mcp   (cambiar con MCP_HOST / MCP_PORT)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from mcp.server import MCPServer

AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

load_dotenv()

from tools import DEFAULT_TOP_K, format_search_results, get_embedding_model, search_faq as _search_faq  # noqa: E402
from tools_weather import check_weather as _check_weather  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("parachute.mcp")

mcp = MCPServer(
    "parachute-tools",
    instructions=(
        "Herramientas de Parachute S.A.: búsqueda en la base de conocimientos de FAQs "
        "(search_faq) y verificación del clima para saltos (check_weather)."
    ),
)


async def _run_logged(tool_name: str, args: dict, fn, *fn_args) -> str:
    """Ejecuta `fn` en un hilo (las tools son bloqueantes) y loguea cada ejecución."""
    logger.info("CALL  %s args=%s", tool_name, json.dumps(args, ensure_ascii=False))
    start = time.perf_counter()
    try:
        result = await asyncio.to_thread(fn, *fn_args)
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        logger.exception("ERROR %s tras %.0f ms", tool_name, elapsed)
        raise
    elapsed = (time.perf_counter() - start) * 1000
    preview = result.replace("\n", " ")[:120]
    logger.info("OK    %s en %.0f ms (%d chars) -> %s", tool_name, elapsed, len(result), preview)
    return result


@mcp.tool()
async def search_faq(query: str, top_k: int = DEFAULT_TOP_K) -> str:
    """Busca preguntas frecuentes, políticas, precios y requisitos de Parachute S.A.

    Args:
        query: Pregunta o texto a buscar semánticamente.
        top_k: Cantidad máxima de resultados a recuperar.
    """

    def _run() -> str:
        return format_search_results(_search_faq(query, top_k=top_k))

    return await _run_logged("search_faq", {"query": query, "top_k": top_k}, _run)


@mcp.tool()
async def check_weather(date_str: str) -> str:
    """Verifica si el clima es apto para saltar en paracaídas en una fecha dada.

    Args:
        date_str: Fecha a consultar en formato YYYY-MM-DD (máximo 16 días a futuro).
    """
    return await _run_logged("check_weather", {"date_str": date_str}, _check_weather, date_str)


def main() -> None:
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8000"))

    logger.info("Cargando modelo de embeddings...")
    get_embedding_model()

    logger.info("Servidor MCP escuchando en http://%s:%d/mcp (Streamable HTTP)", host, port)
    logger.info("Tools expuestas: search_faq, check_weather")
    mcp.run(transport="streamable-http", host=host, port=port)


if __name__ == "__main__":
    main()

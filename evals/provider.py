"""Custom provider de promptfoo para el Manager Agent.

Permite que promptfoo invoque a `run_query` de agent_centralized.py
en vez de llamar a un modelo genérico. Cada test case de promptfoo manda su
pregunta como `prompt`, y este provider devuelve:
  - output: la respuesta final del agente (texto, para asserts de factuality/
    contains/regex).
  - metadata.tool_calls: lista de tools invocadas con sus argumentos, para los
    asserts de tool execution (accesible en asserts python como context["metadata"]).
"""

import sys
import time
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from agent_centralized import run_query  # noqa: E402


def call_api(prompt: str, options: dict, context: dict) -> dict:
    start = time.perf_counter()
    try:
        result = run_query(prompt)
    except Exception as e:
        return {"error": str(e)}

    latency_ms = (time.perf_counter() - start) * 1000

    return {
        "output": result["final_output"],
        "metadata": {
            "tool_calls": result["tool_calls"],
            "tool_names": [tc["name"] for tc in result["tool_calls"]],
            "latency_ms": latency_ms,
        },
    }

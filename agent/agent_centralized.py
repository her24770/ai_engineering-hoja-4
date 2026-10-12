import asyncio
import contextlib
import datetime
import os
import sys
import threading
from dotenv import load_dotenv

# Dependencias para agentes
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp, create_static_tool_filter

load_dotenv()

# Las herramientas (search_faq, check_weather) viven en el servidor MCP
# (mcp_server/server.py) y los workers las consumen por Streamable HTTP.
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")


def _mcp_client(name: str, allowed_tools: list[str]) -> MCPServerStreamableHttp:
    """Cliente MCP hacia el servidor de herramientas, expone solo las tools del worker."""
    return MCPServerStreamableHttp(
        name=name,
        params={"url": MCP_SERVER_URL, "timeout": 30},
        tool_filter=create_static_tool_filter(allowed_tool_names=allowed_tools),
        cache_tools_list=True,
        client_session_timeout_seconds=60,
    )


def _build_manager_agent(faq_mcp: MCPServerStreamableHttp, weather_mcp: MCPServerStreamableHttp) -> Agent:
    """Construye el Manager Agent (arquitectura centralizada) y sus workers.

    Los workers obtienen sus herramientas del servidor MCP vía `faq_mcp` / `weather_mcp`."""
    today_str = datetime.date.today().isoformat()
    weekday_str = datetime.date.today().strftime("%A")

    # 1. Definir los Agentes "Workers"
    faq_agent = Agent(
        name="FAQ Worker",
        instructions=(
            "Eres un agente de base de conocimiento especializado en responder preguntas frecuentes de Parachute S.A. "
            "Utiliza tu herramienta 'search_faq' para buscar en la base de datos vectorial y proveer respuestas precisas. "
            "Responde únicamente con lo que aparezca en los resultados de la búsqueda. "
            "Si el resultado no contiene la información pedida, dilo claramente y sugiere contactar a soporte@parachutesa.gt; "
            "no afirmes que existe un servicio, área o dato que no esté escrito en el resultado. "
            "No debes invocar al clima."
        ),
        mcp_servers=[faq_mcp],
    )

    weather_agent = Agent(
        name="Weather and Scheduling Worker",
        instructions=(
            f"Hoy es {today_str} ({weekday_str}). Usa siempre esta fecha como referencia real "
            "para resolver cualquier expresión relativa del usuario ('mañana', 'este fin de semana', "
            "'el próximo sábado', 'en una semana', etc.) y calcula la fecha exacta en formato YYYY-MM-DD "
            "a partir de ella; nunca asumas ni inventes otro año o mes. "
            "Eres un agente especializado en verificar el clima y calendarizar citas para saltos en paracaídas de Parachute S.A. Utiliza tu herramienta 'check_weather' pasándole la fecha calculada en formato YYYY-MM-DD para saber si las condiciones son APTAS, MARGINALES o PROHIBIDAS, e informa al usuario basándote en el resultado."
        ),
        mcp_servers=[weather_mcp],
    )

    # 2. Definir el Agente Manager (Centralizado) que usa a los workers como herramientas
    manager_agent = Agent(
        name="Manager Agent",
        instructions=(
            f"Hoy es {today_str} ({weekday_str}). "
            "Eres el supervisor principal de atención al cliente de Parachute S.A. "
            "Tu deber es enrutar las peticiones de los usuarios al agente correcto usando tus herramientas. "
            "Si el usuario tiene una duda general sobre el servicio, normas, políticas o precios, utiliza la herramienta del FAQ Worker. "
            "Si el usuario menciona una fecha (explícita o relativa, como 'mañana', 'este fin de semana', 'el próximo sábado', "
            "'quiero agendar/calendarizar'), o quiere saber si un día es bueno para saltar, utiliza SIEMPRE la herramienta del Weather Worker "
            "y déjale a él el cálculo de la fecha exacta. "
            "Siempre responde de forma amable y delega el trabajo al worker adecuado. "
            "Toda pregunta sobre Parachute S.A. debe pasar por el FAQ Worker antes de responder. "
            "Si el FAQ Worker indica que no encontró la información, responde que no puedes contestar esa pregunta "
            "con la información disponible y sugiere contactar a soporte@parachutesa.gt. "
            "Nunca respondas con conocimiento general que no provenga de los workers, aunque la respuesta parezca obvia."
        ),
        tools=[
            faq_agent.as_tool(tool_name="faq_worker", tool_description="Consulta la base de conocimientos y FAQs de Parachute S.A."),
            weather_agent.as_tool(tool_name="weather_worker", tool_description="Verifica el clima y evalúa fechas para saltos en paracaídas")
        ]
    )
    return manager_agent


@contextlib.asynccontextmanager
async def manager_session():
    """Abre las conexiones MCP y entrega el Manager Agent listo para usar."""
    faq_mcp = _mcp_client("parachute-faq", ["search_faq"])
    weather_mcp = _mcp_client("parachute-weather", ["check_weather"])
    async with faq_mcp, weather_mcp:
        yield _build_manager_agent(faq_mcp, weather_mcp)


def _extract_tool_calls(result) -> list[dict]:
    tool_calls = []
    for item in result.new_items:
        if item.type == "tool_call_item":
            tool_calls.append({
                "name": getattr(item.raw_item, "name", None),
                "arguments": getattr(item.raw_item, "arguments", None),
            })
    return tool_calls


async def run_query_async(pregunta: str, manager_agent: Agent | None = None) -> dict:
    """Ejecuta una pregunta contra el Manager Agent.

    Si `manager_agent` es None abre (y cierra) sus propias conexiones MCP.
    Devuelve {'final_output': str, 'tool_calls': list[dict]}.
    """
    if manager_agent is not None:
        result = await Runner.run(starting_agent=manager_agent, input=pregunta)
    else:
        async with manager_session() as agent:
            result = await Runner.run(starting_agent=agent, input=pregunta)

    return {
        "final_output": result.final_output,
        "tool_calls": _extract_tool_calls(result),
    }


_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()


def run_query(pregunta: str) -> dict:
    """Versión síncrona de `run_query_async` (la usan los evals de promptfoo).

    Returns:
        dict con:
            final_output: str, la respuesta final del agente.
            tool_calls: list[dict], cada uno con 'name' y 'arguments' (JSON string)
                de las herramientas invocadas por el Manager, en orden.
    """
    load_dotenv()
    # Un único event loop por proceso: el cliente HTTP de OpenAI queda ligado al
    # loop donde se creó, y `asyncio.run` repetido lo dejaría apuntando a uno cerrado.
    global _loop
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()
        return _loop.run_until_complete(run_query_async(pregunta))


async def _amain() -> None:
    print(f"Conectando al servidor MCP en {MCP_SERVER_URL} ...")
    async with manager_session() as manager_agent:
        print("\n--- Arquitectura Centralizada Inicializada ---")
        print("Manager Agent listo. Puedes hacerle preguntas de FAQs o preguntarle sobre el clima para un día específico.")
        print("Escribe tu solicitud. Para salir presiona Ctrl-C o escribe 'Bye'.\n")

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
                result = await run_query_async(pregunta, manager_agent)
                print(f"\nManager/Respuesta Final: {result['final_output']}\n")
            except Exception as e:
                print(f"Error al ejecutar el agente: {e}\n")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Falta OPENAI_API_KEY en .env")

    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        print("\nHasta luego.")


if __name__ == "__main__":
    main()

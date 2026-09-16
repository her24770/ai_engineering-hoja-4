import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Dependencias para agentes del OpenAI Agents SDK
from agents import Agent, Runner, function_tool

# Asegurar que el directorio agent esté en sys.path para importaciones directas
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Importar las herramientas existentes
from tools import search_faq, format_search_results, get_embedding_model
from tools_weather import check_weather

# Comandos reconocidos para finalizar la sesión
EXIT_COMMANDS = {"bye", "goodbye", "exit", "salir", "adios", "adiós"}

# System prompts definidos para la arquitectura descentralizada
RECEPTION_INSTRUCTIONS = (
    "Eres el agente de recepción de atención al cliente de Parachute S.A. "
    "Tu deber es identificar la intención del usuario y transferir la conversación al especialista adecuado: "
    "si tiene dudas generales sobre el servicio, normas o FAQs, transfiere al FAQ Agent; "
    "si pregunta por el clima o fechas para saltar, transfiere al Weather Agent. "
    "No uses herramientas ni respondas consultas especializadas. "
    "Si la consulta no corresponde a estos temas, explica amablemente qué consultas puedes atender."
)

FAQ_INSTRUCTIONS = (
    "Eres un agente de base de conocimiento especializado en responder preguntas frecuentes de Parachute S.A. "
    "Utiliza tu herramienta 'search_faq' para buscar en la base de datos vectorial y proveer respuestas precisas. "
    "No inventes datos. Si el usuario pregunta por el clima o fechas para saltar, transfiere la conversación al Weather Agent."
)

WEATHER_INSTRUCTIONS = (
    "Eres un agente especializado en verificar el clima y fechas para saltos en paracaídas de Parachute S.A. "
    "Utiliza tu herramienta 'check_weather' pasándole una fecha en formato YYYY-MM-DD para saber si las condiciones "
    "son IDEAL, MARGINAL o NO SEGURO/PROHIBIDO, e informa al usuario basándote en el resultado. "
    "Si el usuario tiene una duda general sobre el servicio, normas o FAQs, transfiere la conversación al FAQ Agent."
)


def _search_faq_handler(query: str) -> str:
    """Busca en la base de datos vectorial de Parachute S.A. y retorna los resultados formateados."""
    results = search_faq(query)
    return format_search_results(results)


def create_decentralized_agents() -> tuple[Agent, Agent, Agent]:
    """Crea y configura los tres agentes con handoffs para la arquitectura descentralizada."""
    search_faq_tool = function_tool(
        _search_faq_handler,
        name_override="search_faq",
        description_override="Busca preguntas frecuentes, políticas, precios y requisitos de Parachute S.A."
    )

    # 1. FAQ Agent (Especialista en FAQs)
    faq_agent = Agent(
        name="FAQ Agent",
        instructions=FAQ_INSTRUCTIONS,
        tools=[search_faq_tool],
    )

    # 2. Weather Agent (Especialista en Clima y Fechas)
    weather_agent = Agent(
        name="Weather Agent",
        instructions=WEATHER_INSTRUCTIONS,
        tools=[function_tool(check_weather)],
    )

    # Configuración de Handoffs bidireccionales entre especialistas
    faq_agent.handoffs = [weather_agent]
    weather_agent.handoffs = [faq_agent]

    # 3. Reception Agent (Punto de entrada, sin herramientas, handoffs a especialistas)
    reception_agent = Agent(
        name="Reception Agent",
        instructions=RECEPTION_INSTRUCTIONS,
        tools=[],
        handoffs=[faq_agent, weather_agent],
    )

    return reception_agent, faq_agent, weather_agent


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Falta OPENAI_API_KEY en .env")

    print("Cargando modelo de embeddings para FAQ...")
    get_embedding_model()

    # Inicializar agentes descentralizados
    reception_agent, _, _ = create_decentralized_agents()

    print("\n--- Arquitectura Descentralizada Inicializada ---")
    print("Reception Agent listo. Las solicitudes se delegarán vía handoffs al especialista correspondiente.")
    print("Escribe tu solicitud. Para salir presiona Ctrl-C o escribe 'Bye'.\n")

    runner = Runner()

    while True:
        try:
            pregunta = input("Tu mensaje: ")
        except (KeyboardInterrupt, EOFError):
            print("\nHasta luego.")
            break

        cleaned_input = pregunta.strip()
        if not cleaned_input:
            continue

        if cleaned_input.lower() in EXIT_COMMANDS:
            print("Hasta luego.")
            break

        print("Pensando...")
        try:
            # Ejecuta el flujo iniciando en el Reception Agent con handoffs
            result = runner.run_sync(starting_agent=reception_agent, input=cleaned_input)
            agent_name = result.last_agent.name if result.last_agent else "Desconocido"
            print(f"\nAgente que respondió: {agent_name}")
            print(f"Respuesta: {result.final_output}\n")
        except Exception as e:
            print(f"Error al ejecutar el agente: {e}\n")


if __name__ == "__main__":
    main()

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from agents import Agent, Runner, function_tool
from tools import search_faq, format_search_results, get_embedding_model
from tools_weather import check_weather


def _search_faq_handler(query: str) -> str:
    """Busca en la base de datos vectorial de Parachute S.A. y retorna los resultados formateados."""
    results = search_faq(query)
    return format_search_results(results)


def create_hierarchical_agents() -> tuple[Agent, Agent, Agent, Agent, Agent]:
    """Crea y configura la jerarquía de 3 niveles usando as_tool()."""
    search_faq_tool = function_tool(
        _search_faq_handler,
        name_override="search_faq",
        description_override="Busca preguntas frecuentes, políticas, precios y requisitos de Parachute S.A."
    )

    # Nivel 3: Agentes Workers que son especialistas
    faq_agent = Agent(
        name="FAQ Worker",
        instructions="Eres un agente de base de conocimiento especializado en responder preguntas frecuentes de Parachute S.A. Utiliza tu herramienta 'search_faq' para buscar en la base de datos vectorial y proveer respuestas precisas. No debes invocar al clima.",
        tools=[search_faq_tool]
    )

    weather_agent = Agent(
        name="Weather and Scheduling Worker",
        instructions="Eres un agente especializado en verificar el clima y calendarizar citas para saltos en paracaídas de Parachute S.A. Utiliza tu herramienta 'check_weather' pasándole una fecha en formato YYYY-MM-DD para saber si las condiciones son APTAS, MARGINALES o PROHIBIDAS, e informa al usuario basándote en el resultado.",
        tools=[function_tool(check_weather)]
    )

    # Nivel 2: Agentes Manager de cada departamento cada uno supervisa a un worker
    customer_service_manager = Agent(
        name="Customer Service Manager",
        instructions=(
            "Eres el manager del departamento de Atención al Cliente de Parachute S.A. "
            "Toda petición que recibas es sobre dudas generales, políticas, precios o requisitos del servicio. "
            "Delega siempre la resolución a tu herramienta del FAQ Worker y transmite su respuesta al usuario."
        ),
        tools=[
            faq_agent.as_tool(tool_name="faq_worker", tool_description="Consulta la base de conocimientos y FAQs de Parachute S.A.")
        ]
    )

    operations_manager = Agent(
        name="Operations Manager",
        instructions=(
            "Eres el manager del departamento de Operaciones de Parachute S.A. "
            "Toda petición que recibas es sobre clima o calendarización de citas para saltos. "
            "Delega siempre la resolución a tu herramienta del Weather Worker y transmite su respuesta al usuario."
        ),
        tools=[
            weather_agent.as_tool(tool_name="weather_worker", tool_description="Verifica el clima y evalúa fechas para saltos en paracaídas")
        ]
    )

    # Nivel 1: Agente Director maneja los managers
    director_agent = Agent(
        name="Director Agent",
        instructions=(
            "Eres el director general de atención al cliente de Parachute S.A. "
            "No resuelves consultas directamente: tu deber es identificar a qué departamento pertenece la "
            "petición del usuario y delegarla usando tus herramientas. "
            "Si el usuario tiene una duda general sobre el servicio, normas o FAQs, delega al Customer Service Manager. "
            "Si el usuario quiere saber si un día específico es bueno para saltar o quiere calendarizar, delega al Operations Manager. "
            "Siempre responde de forma amable y transmite la respuesta del departamento correspondiente."
        ),
        tools=[
            customer_service_manager.as_tool(tool_name="customer_service_manager", tool_description="Departamento de Atención al Cliente: resuelve dudas generales, políticas, precios y requisitos de Parachute S.A."),
            operations_manager.as_tool(tool_name="operations_manager", tool_description="Departamento de Operaciones: verifica el clima y calendariza citas para saltos en paracaídas")
        ]
    )

    return director_agent, customer_service_manager, operations_manager, faq_agent, weather_agent


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Falta OPENAI_API_KEY en .env")

    print("Cargando modelo de embeddings para FAQ...")
    get_embedding_model()

    director_agent, _, _, _, _ = create_hierarchical_agents()

    print("\n--- Arquitectura Jerárquica Inicializada ---")
    print("Director Agent listo. Delega a Customer Service Manager u Operations Manager según la petición.")
    print("Escribe tu solicitud. Para salir presiona Ctrl-C o escribe 'Bye'.\n")

    runner = Runner()

    while True:
        try:
            pregunta = input("Tu mensaje: ")
        except (KeyboardInterrupt, EOFError):
            print("\nHasta luego.")
            break

        if not pregunta or pregunta.lower() == "bye":
            print("Hasta luego.")
            break

        print("Pensando...")
        try:
            # Ejecuta el flujo utilizando Runner de openai-agents
            result = runner.run_sync(starting_agent=director_agent, input=pregunta)
            print(f"\nDirector/Respuesta Final: {result.final_output}\n")
        except Exception as e:
            print(f"Error al ejecutar el agente: {e}\n")


if __name__ == "__main__":
    main()

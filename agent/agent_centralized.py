import os
import sys
from dotenv import load_dotenv

# Dependencias para agentes
from agents import Agent, Runner, function_tool

# Importar las herramientas (como funciones de python)
from tools import search_faq, format_search_results, get_embedding_model
from tools_weather import check_weather

def _search_faq_handler(query: str) -> str:
    """Busca en la base de datos vectorial de Parachute S.A. y retorna los resultados formateados."""
    results = search_faq(query)
    return format_search_results(results)

def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Falta OPENAI_API_KEY en .env")

    print("Cargando modelo de embeddings para FAQ...")
    get_embedding_model()

    search_faq_tool = function_tool(
        _search_faq_handler,
        name_override="search_faq",
        description_override="Busca preguntas frecuentes, políticas, precios y requisitos de Parachute S.A."
    )

    # 1. Definir los Agentes "Workers"
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

    # 2. Definir el Agente Manager (Centralizado) que usa a los workers como herramientas
    manager_agent = Agent(
        name="Manager Agent",
        instructions=(
            "Eres el supervisor principal de atención al cliente de Parachute S.A. "
            "Tu deber es enrutar las peticiones de los usuarios al agente correcto usando tus herramientas. "
            "Si el usuario tiene una duda general sobre el servicio, normas o FAQs, utiliza la herramienta del FAQ Worker. "
            "Si el usuario quiere saber si un día específico es bueno para saltar o quiere calendarizar, utiliza la herramienta del Weather Worker. "
            "Siempre responde de forma amable y delega el trabajo al worker adecuado."
        ),
        tools=[
            faq_agent.as_tool(tool_name="faq_worker", tool_description="Consulta la base de conocimientos y FAQs de Parachute S.A."),
            weather_agent.as_tool(tool_name="weather_worker", tool_description="Verifica el clima y evalúa fechas para saltos en paracaídas")
        ]
    )

    print("\n--- Arquitectura Centralizada Inicializada ---")
    print("Manager Agent listo. Puedes hacerle preguntas de FAQs o preguntarle sobre el clima para un día específico.")
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
            result = runner.run_sync(starting_agent=manager_agent, input=pregunta)
            print(f"\nManager/Respuesta Final: {result.final_output}\n")
        except Exception as e:
            print(f"Error al ejecutar el agente: {e}\n")

if __name__ == "__main__":
    main()

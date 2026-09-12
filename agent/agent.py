import json
import os
import sys

from dotenv import load_dotenv
from groq import BadRequestError, Groq
from tools import SEARCH_FAQ_TOOL_DEFINITION, SYSTEM_PROMPT, format_search_results, get_embedding_model, search_faq

MODEL = "openai/gpt-oss-120b"
AVAILABLE_TOOLS = {"search_faq": search_faq}

def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    if not os.getenv("GROQ_API_KEY"):
        sys.exit("Falta GROQ_API_KEY")

    client = Groq()

    print("Cargando modelo de embeddings...")
    get_embedding_model()

    print("Agente FAQ - Parachute S.A.")
    print("Escribe tu pregunta. Para salir haz Ctrl-C o escribe 'Bye'.\n")
    while True:
        try:
            pregunta = input("Tu pregunta: ")
        except (KeyboardInterrupt, EOFError):
            print("\nHasta luego.")
            break

        if not pregunta:
            continue
        if pregunta.lower() == "bye":
            print("Hasta luego.")
            break

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": pregunta},
        ]

        try:
            respuesta = ask_llm(client, messages, force_tool=True)
        except Exception as e:
            print(f"Error al llamar al modelo: {e}\n")
            continue

        print(f"\n{respuesta}\n")


def ask_llm(client: Groq, messages: list[dict], force_tool: bool = False) -> str:
    tool_choice = (
        {"type": "function", "function": {"name": "search_faq"}}
        if force_tool
        else "auto"
    )
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=[SEARCH_FAQ_TOOL_DEFINITION],
            tool_choice=tool_choice,
            temperature=0,
            reasoning_format="hidden",
        )
    except BadRequestError:
        if not force_tool:
            raise
        pregunta = messages[-1]["content"]
        content = format_search_results(search_faq(pregunta))
        messages.append(
            {"role": "system", "content": f"Resultado de search_faq para '{pregunta}':\n{content}"}
        )
        return ask_llm(client, messages, force_tool=False)

    message = completion.choices[0].message

    if not message.tool_calls:
        messages.append({"role": "assistant", "content": message.content})
        return message.content

    messages.append(
        {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [tc.model_dump() for tc in message.tool_calls],
        }
    )

    for tool_call in message.tool_calls:
        fn = AVAILABLE_TOOLS.get(tool_call.function.name)
        args = json.loads(tool_call.function.arguments)
        results = fn(**args) if fn else []
        content = format_search_results(results) if fn else "Tool desconocida."
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": content,
            }
        )

    return ask_llm(client, messages)

if __name__ == "__main__":
    main()



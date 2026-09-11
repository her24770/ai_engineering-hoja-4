import os
import sys

from dotenv import load_dotenv
from groq import Groq

MODEL = "openai/gpt-oss-120b"

def main() -> None:
    load_dotenv()
    if not os.getenv("GROQ_API_KEY"):
        sys.exit("Falta GROQ_API_KEY")

    client = Groq()
    messages = [
        {
            "role": "system",
            "content": "Eres un agente de FAQ de Parachute S.A. Responde de forma breve y clara.",
        }
    ]

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

        messages.append({"role": "user", "content": pregunta})

        try:
            completion = client.chat.completions.create(
                model=MODEL,
                messages=messages,
            )
        except Exception as e:
            print(f"Error al llamar al modelo: {e}\n")
            messages.pop()
            continue

        respuesta = completion.choices[0].message.content
        messages.append({"role": "assistant", "content": respuesta})
        print(f"\n{respuesta}\n")

if __name__ == "__main__":
    main()



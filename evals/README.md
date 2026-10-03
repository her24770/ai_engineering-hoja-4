# Evals del Manager Agent (Parachute S.A.)

Evaluación con [promptfoo](https://promptfoo.dev) del agente centralizado (`agent/agent_centralized.py`),
que cubre sus dos funcionalidades: FAQs (RAG sobre pgvector) y citas/clima (Open-Meteo).

## Requisitos antes de correr

1. **Python 3.10 o superior** para el agente (`agent/agent_centralized.py` usa `X | None`).
   Con Homebrew: `brew install python@3.12`, y crear el venv con esa versión:
   ```bash
   /opt/homebrew/bin/python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **promptfoo** (Node 18+): `npm i -g promptfoo`.
3. Levantar la base de datos del proyecto:
   ```bash
   docker compose up -d
   ```
4. Que la tabla `faqs` esté poblada: `python loader/load_embeddings.py`.
5. Poner una `OPENAI_API_KEY` válida en `.env`. La usan el agente y el juez de los asserts `llm-rubric`.

## Cómo correr los evals

Desde esta carpeta (`evals/`):

```bash
promptfoo eval --env-file ../.env
```

Para generar el archivo de reporte que se entrega (HTML):

```bash
promptfoo eval --env-file ../.env -o ../reports/promptfoo-report.html
```

Para ver los resultados en el navegador:

```bash
promptfoo view
```

## Estructura

- `provider.py` — custom provider que le pasa el `prompt` a `run_query()`
  de `agent/agent_centralized.py` y devuelve la respuesta final junto con metadata de las tool calls.
- `asserts.py` — asserts de Python reutilizables (por ahora, `used_tool` para tool execution).
- `promptfooconfig.yaml` — config base: provider, umbral de latencia por defecto, y la lista de
  archivos de test cases.
- `faq_tests.yaml` — test cases de la funcionalidad de FAQs.
- `citas_tests.yaml` — test cases de la funcionalidad de citas/clima.

## Qué trae `context['metadata']` en cada respuesta

El provider expone esto para usar en asserts `type: python`:

| campo         | contenido                                                                 |
|---------------|----------------------------------------------------------------------------|
| `tool_names`  | lista de nombres de tools que el Manager invocó (`"faq_worker"`, `"weather_worker"`) |
| `tool_calls`  | lista completa `{name, arguments}` con los argumentos (JSON string) de cada tool call |
| `latency_ms`  | latencia medida manualmente (alternativa al assert nativo `latency`)       |


## Cómo agregar un test case

Cada test case va en `faq_tests.yaml` o `citas_tests.yaml` según su funcionalidad, con esta forma:

```yaml
- vars:
    inquiry: "tu pregunta aquí"
    expected_tool: "faq_worker"   # o "weather_worker"
  assert:
    # Determinístico
    - type: icontains
      value: "palabra clave esperada"
    # Factuality usa OPENAI_API_KEY 
    - type: llm-rubric
      value: "la respuesta debe indicar correctamente que..."
    # Latencia
    - type: latency
      threshold: 60000
    # Tool execution
    - type: python
      value: "file://asserts.py:used_tool"
```

Cada test case debería cubrir los 4 tipos pedidos (factuality, determinístico, latencia, tool execution).

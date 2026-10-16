# ai_engineering-hoja-7 — Protocolos Agénticos (MCP + A2A)

Hoja de trabajo #7 — Protocolos agénticos: Model Context Protocol (MCP) y Agent-to-Agent (A2A) — CC3116, UVG.

Este proyecto evoluciona el sistema multi-agente de atención al cliente de **Parachute S.A.** incorporando dos protocolos estándar de la industria:
1. **Model Context Protocol (MCP):** Abstrae las herramientas del sistema (`search_faq` y `check_weather`) en un servidor centralizado con transporte **Streamable HTTP**. Los agentes workers se conectan como clientes MCP sin tener las herramientas embebidas.
2. **Agent-to-Agent (A2A):** Envuelve el sistema multi-agente (Manager + Workers) y lo expone hacia el exterior como **un único agente unificado**, publicando su `AgentCard` con sus dos habilidades (*Skills*) oficiales y procesando mensajes vía JSON-RPC 2.0.

---

## Video

[Video ejecutándose simultáneamente](https://youtu.be/qoO3DEEgTFc)

## Integrantes
* Josué Hernández Gonzales - 24770
* Jackelyn Girón - 24737
* Sergio Tan - 24759

---

## Arquitectura de Protocolos Agénticos

```text
[Cliente Terminal / Hoppscotch]
               │
               │  Protocolo A2A (HTTP / JSON-RPC 2.0) en :9000
               ▼
   [Servidor A2A (a2a_server)]
   (AgentCard con 2 Skills)
               │
               │  run_query_async()
               ▼
     [Manager Agent (Supervisor)]
         ┌─────┴──────────────┐
         ▼                    ▼
   [FAQ Worker]      [Weather Worker]
         └─────┬──────────────┘
               │
               │  Protocolo MCP (Streamable HTTP) en :8000/mcp
               ▼
     [Servidor MCP (mcp_server)]
         ├── search_faq   (RAG con PostgreSQL pgvector)
         └── check_weather (API Open-Meteo)
```

### Funcionamiento por Capas

1. **Servidor MCP (`mcp_server/server.py`):**
   - Corre sobre **Streamable HTTP** en `http://127.0.0.1:8000/mcp`.
   - Expone las herramientas `search_faq` (búsqueda semántica de políticas y preguntas frecuentes) y `check_weather` (pronóstico meteorológico para salto).
   - Emite logs estructurados por cada ejecución indicando argumentos, tiempo en ms y preview del resultado (`CALL`, `OK`, `ERROR`).
2. **Workers como Clientes MCP (`agent/agent_centralized.py`):**
   - Los agentes especializados (`FAQ Worker` y `Weather and Scheduling Worker`) ya **no** tienen herramientas embebidas. Las consumen dinámicamente conectándose al servidor MCP vía `MCPServerStreamableHttp`.
3. **Servidor A2A (`a2a_server/server.py`):**
   - Construido sobre Starlette y `a2a-sdk`, escucha en `http://127.0.0.1:9000`.
   - Mantiene una sesión *warm* con el Manager Agent mediante lifespan para mínima latencia.
   - Publica la tarjeta de capacidades `AgentCard` en `/.well-known/agent-card.json`.
   - Procesa consultas en `POST /` vía JSON-RPC 2.0 y emite logs por cada mensaje recibido y respondido.

---

## API Reference — Servidor A2A

### Tabla de Endpoints

| Método | Endpoint | Descripción | Formato |
| :--- | :--- | :--- | :--- |
| `GET` | `/.well-known/agent-card.json` | Retorna los metadatos del agente, interfaces compatibles y sus 2 skills oficiales. | JSON |
| `POST` | `/` | Endpoint principal de mensajería y tareas bajo el protocolo A2A. | JSON-RPC 2.0 |

---

### 1. `GET /.well-known/agent-card.json`
Retorna la especificación del agente:
* **Nombre:** `Parachute Customer Service Agent`
* **Versión:** `1.0.0`
* **Skills publicadas:**
  1. `faqs`: Consulta de normativas, peso máximo (100 kg), edad mínima (18 o 16 con tutor), precios y recargos.
  2. `citas_clima`: Factibilidad meteorológica (APTA, MARGINAL, PROHIBIDA) para saltar en una fecha (aclara que *no* realiza reservas en base de datos).

---

### 2. `POST /` — Ejecución de Mensajes (JSON-RPC)

#### Headers requeridos
```http
Content-Type: application/json
a2a-version: 1.0
```

#### Caso 1: Consulta de FAQs (Skill `faqs`)

**Request Body:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "SendMessage",
  "params": {
    "message": {
      "message_id": "msg-001",
      "role": 1,
      "parts": [
        { "text": "¿Cuál es el peso máximo permitido para saltar?" }
      ]
    }
  }
}
```

**Response (200 OK):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "message": {
      "role": "ROLE_AGENT",
      "parts": [
        { "text": "El peso máximo permitido para realizar un salto en paracaídas es de 100 kg..." }
      ]
    }
  }
}
```

#### Caso 2: Consulta Meteorológica (Skill `citas_clima`)

**Request Body:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "SendMessage",
  "params": {
    "message": {
      "message_id": "msg-002",
      "role": 1,
      "parts": [
        { "text": "¿Las condiciones son aptas para saltar este sábado?" }
      ]
    }
  }
}
```

**Response (200 OK):**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "message": {
      "role": "ROLE_AGENT",
      "parts": [
        { "text": "Para este sábado las condiciones se pronostican APTAS: velocidad de viento adecuada y sin precipitación..." }
      ]
    }
  }
}
```

---

## Formato de Logs en Consola

Durante la ejecución, cada componente emite logs en tiempo real para trazabilidad:

### Logs del Servidor MCP (`mcp_server`)
```text
18:16:11 | INFO | parachute.mcp | CALL  search_faq args={"query": "¿Cuál es el peso máximo?", "top_k": 3}
18:16:12 | INFO | parachute.mcp | OK    search_faq en 115 ms (1010 chars) -> [FAQ-021] Límite de peso...
```

### Logs del Servidor A2A (`a2a_server`)
```text
23:10:05 | INFO | parachute.a2a | [MENSAJE RECIBIDO] (task=sin-id) "¿Cuál es el peso máximo permitido para saltar?"
23:10:07 | INFO | parachute.a2a | [RESPUESTA EMITIDA] en 1650 ms (tools: faq_worker) -> "El peso máximo permitido..."
```

---

## Guía de Ejecución

### Requisitos previos
1. Clonar el repositorio y activar el entorno virtual con Python 3.10+:
   ```bash
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. Configurar variables de entorno copiando `.env.example` a `.env` (incluyendo `OPENAI_API_KEY`).

### Orden de arranque de servicios

1. **Paso 1 — Base de datos vectorial (Docker):**
   ```bash
   docker compose up -d
   ```
   *(Si es la primera vez, poblar embeddings con `python loader/load_embeddings.py`)*

2. **Paso 2 — Servidor MCP:**
   ```bash
   python mcp_server/server.py
   ```
   *(Escuchando en `http://127.0.0.1:8000/mcp`)*

3. **Paso 3 — Servidor A2A:**
   ```bash
   python a2a_server/server.py
   ```
   *(Escuchando en `http://127.0.0.1:9000`)*

4. **Paso 4 — Cliente A2A interactivo (terminal):**
   ```bash
   python a2a_client/client.py
   ```
   *(Lee la URL de `A2A_SERVER_URL`)*

### Pruebas Automatizadas

```bash
# Tests del Servidor MCP
pytest tests/test_mcp_server.py -v

# Tests del Servidor A2A
pytest tests/test_a2a_server.py -v

# Tests del Cliente A2A
pytest tests/test_a2a_client.py -v
```

---

## Estructura del Proyecto

```text
ai_engineering-hoja-4/
├── docker-compose.yml          # PostgreSQL 16 + pgvector en contenedor
├── db/
│   └── init.sql                # Extensión pgvector y tabla `faqs`
├── data/
│   ├── Corpus_FAQs_Parachute_SA_2026.txt   # Corpus oficial de Parachute S.A.
│   └── faqs_clean.jsonl        # Corpus estructurado y normalizado
├── loader/
│   ├── preprocess.py           # Parser del corpus a JSON estructurado
│   ├── db.py                   # Conexión y utilidades de base de datos
│   └── load_embeddings.py      # Carga de embeddings con sentence-transformers
├── agent/
│   ├── agent_centralized.py    # Arquitectura Centralizada (Manager Agent + Workers clientes MCP)
│   ├── tools.py                # Implementación base de búsqueda semántica
│   └── tools_weather.py        # Implementación base de consulta meteorológica
├── mcp_server/
│   └── server.py               # Servidor MCP (Streamable HTTP): search_faq + check_weather
├── a2a_server/
│   ├── card.py                 # Definición del AgentCard y sus 2 Skills (FAQs y Citas/Clima)
│   └── server.py               # Servidor A2A (Starlette + Uvicorn) envolviendo el Manager Agent
├── a2a_client/
│   ├── __init__.py
│   └── client.py               # Cliente A2A interactivo de terminal (lee A2A_SERVER_URL, reutiliza context_id en toda la sesión)
├── evals/                      # Evaluaciones de calidad previas (Promptfoo - HDT6)
│   ├── promptfooconfig.yaml    # Configuración principal de promptfoo
│   ├── provider.py             # Custom provider conectado al Manager Agent
│   ├── faq_tests.yaml          # Suite de pruebas para FAQs
│   └── citas_tests.yaml        # Suite de pruebas para citas y clima
├── reports/
│   └── promptfoo-report.html   # Reporte visual exportado de la evaluación previa
├── tests/
│   ├── test_mcp_server.py      # Pruebas unitarias y de integración del servidor MCP
│   ├── test_a2a_server.py      # Pruebas del AgentCard, logs y JSON-RPC de A2A
│   └── test_a2a_client.py      # Pruebas del cliente A2A de terminal
├── requirements.txt            # Dependencias del proyecto
└── .env.example                # Variables de entorno requeridas
```

---

## Sección Secundaria — Evaluaciones de Calidad (Evals — HDT6)

> En la fase anterior del proyecto se implementó el ciclo de aseguramiento de calidad y evaluaciones continuas (**Evals**) utilizando **[promptfoo](https://promptfoo.dev)**. El reporte interactivo generado se encuentra en:
> **[reports/promptfoo-report.html](./reports/promptfoo-report.html)**

### Resumen de Pruebas Evaluadas (Promptfoo)
* **FAQs:** Límites de peso (100 kg), edad mínima (18 años), velocidad en caída libre (200 km/h), recargos administrativos (Q250), preguntas sin datos en corpus y preguntas fuera de dominio.
* **Citas y Clima:** Consulta dinámica válida de fechas relativas, casos borde en fechas pasadas, fechas mayores a 16 días y formatos inválidos.
* **Tipos de aserciones cubiertas:** Latencia (`latency`), Tool Execution (`asserts.py:used_tool`), Determinísticas (`regex`/`contains`) y Semánticas (`llm-rubric`).

Para reproducir los evals:
```bash
cd evals
promptfoo eval --env-file ../.env -o ../reports/promptfoo-report.html
```

---

## Enunciado Oficial de la Entrega

### Universidad del Valle de Guatemala — Hoja de trabajo #7 - Protocolos Agénticos — CC3116

**Objetivos:**
* Familiarizarse con los protocolos para herramientas, prompts y recursos (MCP) y para comunicación entre agentes (A2A).

**Instrucciones:**
* Abstraer las herramientas de los agentes en un solo servidor MCP con transporte **Streamable HTTP**.
* Exponer el sistema multi-agente como un solo agente con sus skills utilizando **A2A**.
* Entregar el código en el repositorio y un video donde se visualicen simultáneamente:
  1. El servidor MCP ejecutándose y emitiendo logs por cada tool call.
  2. El servidor A2A ejecutándose y emitiendo logs por cada mensaje.
  3. La aplicación de terminal interactuando con el servidor A2A.

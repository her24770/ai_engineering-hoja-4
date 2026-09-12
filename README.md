# ai_engineering-hoja-4

Hoja de trabajo #4 — Herramientas (bases de datos vectoriales + tools/function calling) — CC3116, UVG.

## Video de demostración

[![Demo del agente Parachute S.A.](https://img.youtube.com/vi/PZP9XT4yhNo/0.jpg)](https://youtu.be/PZP9XT4yhNo)

## Estructura del proyecto

```
ai_engineering-hoja-4/
├── docker-compose.yml      # PostgreSQL + pgvector en contenedor
├── db/
│   └── init.sql            # crea la extensión vector y la tabla `faqs`
├── data/
│   ├── Corpus_FAQs_Parachute_SA_2026.txt   # corpus original entregado por Parachute S.A.
│   └── faqs_clean.jsonl    # (generado) corpus preprocesado, un JSON por línea
├── loader/
│   ├── preprocess.py       # parsea el .txt a registros estructurados
│   ├── db.py                # conexión a Postgres/pgvector
│   └── load_embeddings.py  # genera embeddings y los carga a la base de datos
├── agent/
│   ├──  tools.py            # definición de la tool search_faq, handler con pgvector y system prompt
|   └──  agent.py            #
├── tests/
│   ├── test_preprocess.py       # tests unitarios del parser (no requieren BD)
│   ├── test_load_embeddings.py  # tests de integración contra pgvector ya cargado
│   └── test_tools.py            # tests unitarios y de integración de la tool search_faq
├── requirements.txt
└── .env.example
```

## Requisitos previos

- **Docker** (o Podman) con soporte para `docker compose`. En macOS con Colima: `colima start`.
- **Python 3.9+**.

## Cómo inicializar la infraestructura

1. Copiar el archivo de variables de entorno de ejemplo:

   ```bash
   cp .env.example .env
   ```

2. Levantar el contenedor de PostgreSQL + pgvector:

   ```bash
   docker-compose up -d
   ```

   Esto crea automáticamente (vía `db/init.sql`, montado en `docker-entrypoint-initdb.d`):
   - La extensión `vector` (pgvector).
   - La tabla `faqs(id, faq_code, category, question, answer, metadata, embedding vector(384))`.
   - Un índice HNSW (`faqs_embedding_hnsw_idx`) para búsquedas por similitud coseno.

3. Verificar que el contenedor esté sano:

   ```bash
   docker ps --filter name=parachute-pgvector
   docker exec parachute-pgvector psql -U parachute -d parachute_faqs -c "\dx" -c "\d faqs"
   ```

4. Para reiniciar la base de datos desde cero (borra todos los datos y vuelve a correr `init.sql`):

   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

## Cómo instalar las dependencias de Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Cómo correr el script de carga

Con el contenedor de PostgreSQL ya levantado (paso anterior):

```bash
source .venv/bin/activate
python loader/load_embeddings.py
```

Esto:
1. Parsea `data/Corpus_FAQs_Parachute_SA_2026.txt` (120 FAQs) y guarda una versión limpia en `data/faqs_clean.jsonl`.
2. Genera un embedding por cada pregunta con `sentence-transformers` (modelo `all-MiniLM-L6-v2`, 384 dimensiones).
3. Vacía la tabla `faqs` (`TRUNCATE`) y la vuelve a poblar — el script se puede correr las veces que sea necesario sin duplicar datos.

## Cómo correr los tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

- `test_preprocess.py` no necesita base de datos: valida que el corpus se parsea completo (120 FAQs, códigos únicos, campos no vacíos).
- `test_load_embeddings.py` sí necesita el contenedor levantado **y** el script de carga ya ejecutado: valida el conteo de filas, la dimensión de los embeddings, y que una búsqueda por similitud (`<=>`, distancia coseno de pgvector) sobre una pregunta parafraseada devuelva el FAQ correcto.
- `test_tools.py` incluye tests unitarios para los esquemas de tools (OpenAI / Anthropic), directrices del prompt del sistema, formateo de resultados y ejecución mockeada de `search_faq`. Además, incluye un test de integración contra la base de datos real (que se omite limpiamente si Postgres no está en ejecución).

## Agente (Tool de Búsqueda y Function Calling)

El módulo `agent/` contiene los componentes del asistente conversacional de Parachute S.A.:

### 1. Tool de búsqueda de conocimiento (`agent/tools.py`)
Provee:
- **`search_faq(query: str, top_k: int = 3, max_distance: float = 0.55)`**: Recibe la pregunta en texto, genera su embedding mediante `sentence-transformers` (`all-MiniLM-L6-v2`, con normalización) y ejecuta una consulta SQL con el operador de distancia coseno de pgvector (`<=>`) sobre la tabla `faqs`.
- **Definición de la Tool (Schemas)**:
  - `SEARCH_FAQ_TOOL_OPENAI`: compatible con la API de tools / function calling de OpenAI, Ollama o LiteLLM.
  - `SEARCH_FAQ_TOOL_ANTHROPIC`: compatible con la API de Tool Use de Anthropic Claude.
- **`SYSTEM_PROMPT`**: Instrucciones estrictas que obligan al LLM a consultar `search_faq`, prohibiendo alucinaciones y forzando a admitir cuando no se tiene información.
- **`format_search_results(results)`**: Utilidad para formatear los resultados encontrados en texto claro para el LLM.

#### Cómo probar la tool individualmente:
Con la base de datos levantada y cargada:
```bash
python agent/tools.py "¿Dónde se realizan los saltos?"
```

### 2. Loop de terminal e integración (`agent/agent.py`)
Gestiona el bucle interactivo de terminal, las llamadas al cliente LLM y el corte de sesión con `Bye` o `Ctrl-C`.

#### Cómo correr el agente:
Con la base de datos levantada y cargada:
```bash
python agent/agent.py
```


## Enunciado original del laboratorio

### Universidad del Valle de Guatemala — Hoja de trabajo #4 - Herramientas — CC3116

**Objetivos**
- Familiarizarse con bases de datos vectoriales y herramientas/tools/function calls de un LLM

**Instrucciones**

Continuar con una implementación más robusta de la hoja de trabajo #3, siguiendo los siguientes criterios:

- Como base de datos vectorial tiene que usar PostgreSQL con la extensión pgvector para almacenar embeddings. Se recomienda utilizar Podman o Docker para manejar un contenedor con la base de datos.
- Debe colocarse en el README.md del repositorio cómo inicializar la infraestructura.
- Deberán entregarse dos scripts/programas:
  1. Un script/programa de **carga** que llena una tabla de PostgreSQL con los embeddings obtenidos de la base de conocimiento.
  2. Un **agente** que responde preguntas frecuentes, tal y como se hizo en la hoja de trabajo #3.
- Puede utilizarse cualquier lenguaje de programación, pero por velocidad de desarrollo se recomienda Python con la siguiente librería:
  - `sentence-transformers` para generar los vectores de embeddings.
  - Se recomienda utilizar modelos de embeddings muy pequeños como `all-MiniLM-L6-v2` para poder ejecutarlos localmente.
- El agente tiene que tener una **herramienta**, configurada con el SDK, que le permita consultar la base de conocimientos y extraer información de esta.
- Debe entregarse un **video** (lo más corto posible) del funcionamiento del script de carga y el agente respondiendo preguntas de la base de conocimientos. No es necesario que hable, puede ser solamente demostrativo.

**Problema**

Parachute S.A. quedó bastante impresionada del demo que se le entregó, por lo que ahora requiere que se implemente ya una solución más robusta con un dump real de su base de datos de FAQs.

El archivo que ellos enviaron es: `Corpus_FAQs_Parachute_SA_2026.txt`.

Puede realizarse cualquier transformación al archivo para facilitar su carga.

Parachute S.A. especificó que aún no quiere un producto funcional, por lo que una interfaz en la terminal está bien para evaluar el comportamiento del agente.

Tomar en cuenta que el agente debe de:
- Responder únicamente basado en la información del archivo. Si la pregunta que el usuario hace no está, el agente tiene que admitir que no la puede responder.
- Debe poder responder múltiples preguntas en una sola sesión, hasta que el usuario salga del loop (con `Ctrl-C`) o escriba la palabra `Bye`.

**Profesor:** Rodrigo Custodio | jrcustodio@uvg.edu.gt

### Rúbrica HDT4

| Criterio | Descripción (Exceeds) | Puntos |
|---|---|---|
| Herramientas | Implementa una herramienta de búsqueda de conocimiento | 30 pts |
| Base de datos vectorial | Utiliza pgvector para realizar consultas en una base de conocimiento | 20 pts |
| Script de carga | Provee un script de extracción de embeddings y carga a una base de datos | 20 pts |
| Agente funciona | Provee un video del funcionamiento del agente, una guía para ejecutar el agente, y se ejecuta correctamente | 30 pts |

**Total:** 100 pts

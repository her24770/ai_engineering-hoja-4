# ai_engineering-hoja-5

Hoja de trabajo #5 — Orquestación (jerárquica, centralizada y decentralizada) — CC3116, UVG.

## Video de demostración

[Demo del agente Parachute S.A.](https://youtu.be/lKm34A7OqEk)

## Estructura del proyecto

```
ai_engineering-hoja-5/
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
│   ├── __init__.py
│   ├── agent.py                 # agente individual de prueba (HDT4)
│   ├── agent_centralized.py     # arquitectura centralizada (manager supervisor con as_tool)
│   ├── agent_decentralized.py   # arquitectura descentralizada (reception y especialistas con handoffs)
│   ├── agent_jerarquico.py      # arquitectura jerárquica (director, managers y workers de 3 niveles)
│   ├── tools.py                 # herramienta search_faq y handler con pgvector
│   └── tools_weather.py         # herramienta check_weather con API Open-Meteo
├── docs/
│   ├── arquitectura.md          # diagramas Mermaid y documentación técnica de arquitecturas
│   └── HDT 5 AI .pdf            # respuestas a las preguntas teóricas del laboratorio
├── tests/
│   ├── test_preprocess.py            # tests unitarios del parser (no requieren BD)
│   ├── test_load_embeddings.py       # tests de integración contra pgvector ya cargado
│   ├── test_tools.py                 # tests unitarios y de integración de la tool search_faq
│   ├── test_weather.py               # tests de evaluación climática (Open-Meteo)
│   └── test_agent_decentralized.py   # tests unitarios de configuración y handoffs
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
- `test_tools.py` valida la tool `search_faq`, esquemas, formateo y búsqueda simulada y real en base de datos.
- `test_weather.py` valida la lógica de predicción climática de `check_weather` contra los umbrales de seguridad.
- `test_agent_decentralized.py` valida la configuración de agentes, aislamiento de herramientas y handoffs descentralizados.

## Arquitecturas Multiagente (MAS)

El proyecto resuelve la atención de FAQs y evaluación climática de saltos bajo tres arquitecturas de orquestación independientes.

Para detalles conceptuales y diagramas de flujo de cada arquitectura, consulta **[docs/arquitectura.md](./docs/arquitectura.md)**.

### 1. Arquitectura Centralizada (`agent/agent_centralized.py`)
Un `Manager Agent` supervisor central orquesta a los especialistas (`FAQ Worker` y `Weather and Scheduling Worker`) como herramientas vía `as_tool()`.

```bash
python agent/agent_centralized.py
```

### 2. Arquitectura Descentralizada (`agent/agent_decentralized.py`)
Sin supervisor central. `Reception Agent` enruta al usuario transfiriendo el control directo de la conversación vía `handoff` a `FAQ Agent` o `Weather Agent`.

```bash
python agent/agent_decentralized.py
```

### 3. Arquitectura Jerárquica (`agent/agent_jerarquico.py`)
Organización de 3 niveles (`Director Agent` $\rightarrow$ `Customer Service / Operations Managers` $\rightarrow$ `Workers especialistas`) coordinados en cadena vía `as_tool()`.

```bash
python agent/agent_jerarquico.py
```

### Herramientas Compartidas
- **`search_faq` (`agent/tools.py`):** Búsqueda semántica en PostgreSQL (`pgvector`) sobre las 120 FAQs.
- **`check_weather` (`agent/tools_weather.py`):** Consulta a Open-Meteo evaluando viento, ráfagas, precipitación y nubes para saltos.


## Enunciado original del laboratorio

### Universidad del Valle de Guatemala — Hoja de trabajo #5 - Orquestación  — CC3116

**Objetivos**
- Familiarizarse con sistemas multiagentes (MAS) orquestrados de manera jerárquica, centralizada y decentralizada.

**Instrucciones**

Resuelvan el siguiente problema utilizando las arquitecturas de orquestación centralizada, jerárquica y decentralizada.

Si ustedes utilizan el SDK de OpenAI, para la arquitectura centralizada y jerárquica puede utilizar la función de as_tool() para crear los agentes  supervisor/manager. Para la arquitectura decentralizada puede utilizar el parámetro de handoff de un agente.

Debe de entregar 3 programas en un repositorio en conjunto con un diagrama de como quedaron organizados sus agentes en cada arquitectura, cada uno resolviendo el mismo problema con una arquitectura distinta, en conjunto con un PDF con las respuestas a las preguntas planteadas en el problema.

**Problema**

Parachute S.A le gustó mucho su trabajo realizado, por lo que ahora le ha pedido los siguientes nuevos requerimientos funcionales adicionales a los ya realizados con la base de conocimientos de FAQs:

* Desean que el agente ahora pueda calendarizar citas chequeando el clima antes. Esto lo debe lograr consultando la API gratuita de Open-Meteo  para la fecha que el usuario desea, los parámetros de búsqueda son los siguientes:
   * Coordenadas del lugar de aterrizaje: 14.013722, -90.771611
   * Fecha que el usuario desea calendarizar cita (Open Meteo unicamente provee hasta 16 días de predicción), si el usuario pide la fecha despues de 16 días se le debe corregir que no se puede.
   * Para la API de open meteo utiliza la opción de current o daily.
   * Tiene que obtener los valores de ráfaga de viento (wind_gust_10m), temperatura (temperature_2m), precipitación (precipitation), visibilidad (cloud_cover) y velocidad de viento superficie (wind_speed_10m) 
* Una vez cuente con esta información el critero para aceptar si el día es bueno para saltar es el siguiente:
   * Velocidad del viento en superficie:
      * Ideal: < 20 km/h
      * Marginal (Solo tándem experimentado): 20–28 km/h
      * NO SEGURO / PROHIBIDO: > 28 km/h (Muy díficil de controlar el salto)
   * Ráfagas de viento:
      * NO SEGURO / PROHIBIDO: > 35 km/h
   * Precipitación:
      * NO SEGURO / PROHIBIDO: > 0.0 mm (Saltar con lluvia daña el equipo y lastima la piel)
   * Cobertura de nubes / Visibilidad:
      * Ideal: < 30% (Visibilidad clara)
      * Marginal: 30 - 75% (Nubes dispersas)
      * NO SEGURO / PROHIBIDO: > 75% (Un techo de nubes bajo impide las reglas de vuelo visual)

* Parachute S.A le ha advertido que va a seguir incrementando los requerimientos funcionales
* Se le recomienda que realice las abstracciones necesarias para que sea facil realizar la implementación de las 3 arquitecturas sin cambiar la lógica de las integraciones.

Las preguntas fueron respondidas en el PDF **[HDT 5 AI](./docs/HDT%205%20AI%20.pdf)**

**Profesor:** Rodrigo Custodio | jrcustodio@uvg.edu.gt

### Rúbrica HDT4

# HDT5

| Criterios | Calificaciones | Puntos |
|---|---|---:|
| **Arquitectura centralizada** | **Exceeds:** Se implementa una arquitectura con un solo manager/supervisor y múltiples workers, funciona correctamente y el diagrama está presente. Responde las preguntas. **33.34 pts**<br><br>**No Evidence:** 0 pts | /33.34 pts |
| **Arquitectura descentralizada** | **Exceeds:** Se implementa una arquitectura descentralizada en donde existen múltiples agentes independientes y las tareas se delegan con handoffs. Se provee un diagrama de la organización de los agentes y su funcionamiento es correcto. Responde las preguntas. **33.33 pts**<br><br>**No Evidence:** 0 pts | /33.33 pts |
| **Arquitectura Jerárquica** | **Exceeds:** Se implementa una arquitectura jerárquica en donde existen al menos 2 managers y workers. Se provee un diagrama de la organización de los agentes y su funcionamiento es correcto. Responde las preguntas. **33.33 pts**<br><br>**No Evidence:** 0 pts | /33.33 pts |


**Total:** 100 pts

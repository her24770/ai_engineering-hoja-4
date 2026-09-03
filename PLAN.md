# Plan de acción — HDT4: Herramientas (Bases de datos vectoriales + Tools/Function Calling)

> Curso CC3116 · UVG · Equipo de 3 personas
> Este documento es la guía de trabajo interna del equipo. Las instrucciones originales del laboratorio están en el [README.md](./README.md).

## 1. Resumen del problema

Parachute S.A. quiere pasar del demo (HDT3) a una versión más robusta:

- Base de datos vectorial real: **PostgreSQL + pgvector** (en contenedor, Docker o Podman).
- Un **script de carga** que lee `Corpus_FAQs_Parachute_SA_2026.txt`, genera embeddings con `sentence-transformers` (modelo pequeño, ej. `all-MiniLM-L6-v2`) y los inserta en PostgreSQL.
- Un **agente conversacional de terminal** que usa una **tool/function call** (configurada con el SDK del LLM que usemos) para consultar esa base de datos vectorial y responder únicamente con información del corpus.
- El agente debe sostener una **sesión con múltiples preguntas** hasta que el usuario escriba `Bye` o presione `Ctrl-C`.
- Si la respuesta no está en el corpus, el agente debe **admitir que no puede responder** (nada de alucinar).
- Entregables: código, README con instrucciones de infraestructura, y un **video corto** demostrando el script de carga + el agente respondiendo preguntas.

## 2. Rúbrica → a qué módulo del código corresponde

| Criterio | Puntos | Dónde se demuestra |
|---|---|---|
| Herramientas (tool de búsqueda de conocimiento) | 30 | `agent/` — definición de la tool + su handler |
| Base de datos vectorial (pgvector) | 20 | `infra/` (docker-compose) + queries SQL con `<->`/`<=>` |
| Script de carga (extracción de embeddings + carga) | 20 | `loader/` |
| Agente funciona (video + guía + ejecución correcta) | 30 | `agent/` + `README.md` + video |

## 3. Arquitectura propuesta

```
ai_engineering-hoja-4/
├── README.md                  # instrucciones de infraestructura + ejecución
├── PLAN.md                    # este documento
├── docker-compose.yml         # postgres + pgvector
├── db/
│   └── init.sql               # CREATE EXTENSION vector; CREATE TABLE faqs (...)
├── data/
│   └── Corpus_FAQs_Parachute_SA_2026.txt   # corpus original
│   └── faqs_clean.jsonl       # (opcional) corpus preprocesado en Q/A
├── loader/
│   ├── preprocess.py          # parsea el .txt -> pares pregunta/respuesta
│   └── load_embeddings.py     # genera embeddings (sentence-transformers) y hace INSERT/UPSERT a pgvector
├── agent/
│   ├── tools.py                # definición de la tool "search_faq" + conexión a pgvector
│   ├── agent.py                # loop de terminal, function calling, prompt de sistema
│   └── llm_client.py           # wrapper del SDK del LLM elegido (Anthropic/OpenAI/etc.)
├── requirements.txt
└── .env.example                # DATABASE_URL, API_KEY, etc.
```

## 4. Decisiones técnicas a tomar como equipo (bloque de kickoff, ~30 min)

1. **Proveedor del LLM y SDK de function calling**: Anthropic Claude (tool_use) vs OpenAI (function calling). Debe soportar tools nativamente.
2. **Modelo de embeddings**: `all-MiniLM-L6-v2` (384 dimensiones) vía `sentence-transformers`.
3. **Motor de contenedores**: Docker o Podman (usar el que todos tengan disponible; documentar ambos si es fácil).
4. **Estrategia de chunking del corpus**: ¿una fila por par pregunta/respuesta o por bloque temático? (recomendado: una fila por Q/A, ya que el corpus es un FAQ).
5. **Umbral de "no lo sé"**: definir una distancia/similaridad de corte (ej. cosine distance > 0.5) por debajo de la cual el agente responde que no tiene esa información.
6. **Formato de la tabla pgvector**: `id, question, answer, source_line, embedding vector(384)`.

## 5. División del trabajo (3 personas)

### Persona A — Infraestructura + Base de datos vectorial (20 pts) + apoyo en script de carga
- Levantar `docker-compose.yml` con imagen `pgvector/pgvector:pg16` (o similar).
- Script `db/init.sql`: `CREATE EXTENSION IF NOT EXISTS vector;`, tabla `faqs` con columna `vector(384)`, índice `ivfflat` o `hnsw` para similaridad coseno.
- Documentar en el README cómo levantar/bajar/resetear el contenedor.
- Probar conexión desde Python (`psycopg2` / `psycopg`).
- Entregable: infra reproducible con un solo comando (`docker compose up -d`).

### Persona B — Script de carga + preprocesamiento del corpus (20 pts)
- Analizar `Corpus_FAQs_Parachute_SA_2026.txt` y escribir `loader/preprocess.py` para extraer pares pregunta/respuesta (limpieza de encabezados, numeración, etc.).
- Escribir `loader/load_embeddings.py`:
  - Carga el corpus preprocesado.
  - Genera embeddings con `sentence-transformers` (`all-MiniLM-L6-v2`).
  - Inserta/actualiza en la tabla `faqs` de PostgreSQL (usar `psycopg2`/`psycopg` + `pgvector` adapter).
  - Debe ser idempotente (se pueda re-ejecutar sin duplicar filas — TRUNCATE o UPSERT por hash del texto).
- Entregable: `python loader/load_embeddings.py` deja la base de datos lista para consultas.

### Persona C — Agente + Tool/Function calling + integración final (30 pts) + video
- Definir la tool `search_faq(query: str, top_k: int)` según el SDK elegido (JSON schema de la tool).
- Handler de la tool: genera embedding de la query del usuario (mismo modelo, `all-MiniLM-L6-v2`) y hace `SELECT ... ORDER BY embedding <=> %s LIMIT top_k` contra pgvector.
- Prompt de sistema: el agente **solo** puede responder con base en los resultados devueltos por la tool; si no hay match suficientemente cercano, debe decir explícitamente que no tiene esa información.
- Loop de terminal: lee input del usuario en bucle, corta con `Bye` (case-insensitive) o `Ctrl-C` (manejar `KeyboardInterrupt` con salida limpia).
- Entregable: `python agent/agent.py` — sesión interactiva funcional.
- Responsable de grabar el **video** corto (carga + preguntas variadas: dentro del corpus, fuera del corpus, y salida con `Bye`).

### Trabajo compartido (todos)
- Revisar el corpus real enviado por Parachute S.A. y acordar juntos el formato de preprocesamiento antes de que Persona B lo implemente (evita retrabajo).
- Pruebas cruzadas: cada persona prueba el módulo de otro compañero antes de integrar a `develop`.
- Actualizar el README conforme cada módulo quede listo.
- Code review vía Pull Request de cada rama de feature hacia `develop` (no commits directos a `main`).

## 6. Flujo de ramas sugerido

```
main
 └── develop
      ├── feature/infra-pgvector       (Persona A)
      ├── feature/loader-embeddings    (Persona B)
      └── feature/agent-tool-calling   (Persona C)
```

- Cada feature branch nace de `develop` y se mergea de vuelta a `develop` vía PR.
- `main` solo recibe merge de `develop` cuando el laboratorio esté completo y probado (video incluido).
- **No se hace push a ningún remoto hasta que el equipo lo confirme explícitamente.**

## 7. Cronograma sugerido (orientativo)

| Etapa | Contenido | Bloqueante para |
|---|---|---|
| 1. Kickoff | Decisiones técnicas (sección 4), reparto confirmado | Todo lo demás |
| 2. Infra lista | `docker compose up -d` levanta Postgres+pgvector, tabla creada | Script de carga y agente |
| 3. Carga lista | Corpus preprocesado + embeddings cargados en la BD | Pruebas del agente |
| 4. Agente lista | Tool conectada, loop funcionando, filtro de "no lo sé" | Grabación del video |
| 5. Integración | Merge de las 3 ramas a `develop`, pruebas end-to-end | Merge a `main` |
| 6. Entrega | README final, video grabado, merge a `main`, entrega | — |

## 8. Checklist de entrega final

- [ ] `docker-compose.yml` / infra documentada y reproducible.
- [ ] `loader/` genera embeddings y carga pgvector correctamente (re-ejecutable).
- [ ] `agent/` implementa la tool de búsqueda vía SDK y responde solo con datos del corpus.
- [ ] El agente admite explícitamente cuando no sabe la respuesta.
- [ ] El agente soporta múltiples preguntas por sesión y sale con `Bye` o `Ctrl-C`.
- [ ] README con instrucciones claras de inicialización de infraestructura y ejecución.
- [ ] Video corto grabado (carga + agente respondiendo preguntas).
- [ ] Merge final `develop` → `main`.

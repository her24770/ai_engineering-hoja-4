# ai_engineering-hoja-6 — Evaluaciones de Calidad (Evals)

Hoja de trabajo #6 — Evals, métricas y graders en la evaluación de sistemas de IA — CC3116, UVG.

Este proyecto implementa el ciclo de aseguramiento de calidad y evaluaciones continuas (**Evals**) para el agente de atención al cliente de **Parachute S.A.** previo a su puesta en producción, utilizando la librería y framework de evaluación **[promptfoo](https://promptfoo.dev)**.

## Integrantes
* Josué Hernández Gonzales - 24770
* Jackelyn Girón - 24737
* Sergio Tan - 24759

---

## Reporte de Evaluación

El reporte interactivo generado por Promptfoo con los 10 casos de prueba y sus respectivas aserciones se encuentra en:
 **[reports/promptfoo-report.html](./reports/promptfoo-report.html)**

---

## Estructura del proyecto

```
ai_engineering-hoja-6/
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
│   ├── agent_centralized.py    # Arquitectura Centralizada (Manager Agent + Workers)
│   ├── tools.py                # Tool `search_faq` con búsqueda semántica en pgvector
│   └── tools_weather.py        # Tool `check_weather` con integración a Open-Meteo
├── evals/
│   ├── promptfooconfig.yaml    # Configuración principal de promptfoo
│   ├── provider.py             # Custom provider que conecta promptfoo con el Manager Agent
│   ├── asserts.py              # Aserción reutilizable en Python para tool execution
│   ├── faq_tests.yaml          # Suite de pruebas para la funcionalidad de FAQs
│   ├── citas_tests.yaml        # Suite de pruebas para citas, clima y casos borde
│   └── README.md               # Guía técnica de ejecución de los evals
├── reports/
│   └── promptfoo-report.html   # Reporte visual exportado de la evaluación
├── docs/
│   └── arquitectura.md         # Documentación de la arquitectura centralizada
├── requirements.txt            # Dependencias de Python
└── .env.example                # Variables de entorno requeridas
```

---

## Arquitectura del Agente

Tras evaluar las distintas alternativas de orquestación en la entrega anterior, se seleccionó y mantuvo la **Arquitectura Centralizada** ([agent/agent_centralized.py](./agent/agent_centralized.py)) como la solución más robusta y adecuada para producción:

- **Manager Agent (Supervisor Central):** Analiza la intención del usuario y delega las tareas a especialistas usando el patrón `as_tool()`.
- **FAQ Worker:** Especialista en base de conocimientos. Ejecuta la herramienta `search_faq` para realizar búsqueda vectorial RAG (`all-MiniLM-L6-v2`) sobre PostgreSQL con `pgvector`.
- **Weather and Scheduling Worker:** Especialista en calendarización y meteorología. Resuelve expresiones temporales dinámicamente y consulta la API de **Open-Meteo** para clasificar si un día es `IDEAL`, `MARGINAL` o `NO SEGURO / PROHIBIDO` para el salto.

Para ejecutar el agente interactivamente en consola:

```bash
python agent/agent_centralized.py
```

---

## Sistema de Evals (Evaluación con Promptfoo)

El agente cuenta con dos funcionalidades centrales (FAQs y citas/clima). Cada caso de prueba implementado en Promptfoo cubre **los 4 tipos de aserciones requeridas**:

1. **Rendimiento / Latencia (`type: latency`):** Verifica que la inferencia, búsqueda semántica y llamadas a APIs externas respondan dentro del umbral de tiempo permitido (< 60s).
2. **Tool Execution (`type: python` -> `asserts.py:used_tool`):** Inspecciona los metadatos devueltos por [evals/provider.py](./evals/provider.py) para certificar que el Manager haya delegado la tarea a la herramienta correcta (`faq_worker` o `weather_worker`).
3. **Determinístico (`type: regex` / `contains` / `not-icontains`):** Comprueba de forma exacta la presencia de cifras oficiales, políticas o códigos de estado.
4. **Factuality / Semántica (`type: llm-rubric`):** Un modelo evaluador califica que la respuesta sea fiel a las políticas de la empresa y no invente datos fuera de contexto ni alucine.

### Listado de Pruebas Evaluadas

#### 1. Funcionalidad de Preguntas Frecuentes (FAQs — [evals/faq_tests.yaml](./evals/faq_tests.yaml))
* **Prueba 1 — Límite de peso:** Consulta sobre el peso máximo permitido (FAQ-021: 100 kg).
* **Prueba 2 — Edad mínima:** Consulta sobre la edad mínima para saltar (FAQ-023: 18 años y excepciones para 16-17 años acompañados).
* **Prueba 3 — Velocidad en caída libre:** Consulta sobre la velocidad alcanzada en caída libre (FAQ-053: 200 km/h promedio).
* **Prueba 4 — Recargos por peso:** Consulta sobre cobros adicionales (FAQ-074: recargo administrativo de Q250 entre 90 y 100 kg).
* **Prueba 5 — Caso sin datos en corpus:** Pregunta sobre instalaciones no documentadas (*zona de espectadores*). Valida que no invente datos y remita a `soporte@parachutesa.gt`.
* **Prueba 6 — Caso fuera de dominio:** Pregunta general ajena (*"¿Cuál es la capital de Francia?"*). Valida prevención de alucinaciones y rechazo de preguntas fuera del negocio.

#### 2. Funcionalidad de Citas y Clima ([evals/citas_tests.yaml](./evals/citas_tests.yaml))
* **Prueba 7 — Consulta válida de clima / cita (Dinámica):** Consulta relativa (*"¿El próximo sábado es buen día para saltar?"*). Valida resolución dinámica de fechas relativas a partir de `today` y reporte de estado meteorológico.
* **Prueba 8 — Caso borde: Fecha en el pasado:** Intento de agendar en una fecha pasada (`2020-01-01`). Valida que detecte que la fecha ya pasó y rechace el agendamiento.
* **Prueba 9 — Caso borde: Fecha a más de 16 días:** Consulta para el futuro lejano (`2030-01-01`). Valida que informe el límite de predicción de 16 días de Open-Meteo.
* **Prueba 10 — Caso borde: Formato de fecha inválido:** Fecha con formato incorrecto o inexistente (`2026-99-99`). Valida manejo del error de formato.

---

## Cómo ejecutar los Evals

### Requisitos previos

1. **Docker:** Levantar la base de datos con pgvector:
   ```bash
   docker-compose up -d
   ```
2. **Datos poblados:** Si es la primera vez, cargar el corpus:
   ```bash
   python loader/load_embeddings.py
   ```
3. **Promptfoo:** Instalado globalmente vía npm:
   ```bash
   npm i -g promptfoo
   ```
4. **Archivo `.env`:** Debe incluir una `OPENAI_API_KEY` válida (utilizada por el agente y el evaluador LLM de las rúbricas).

### Ejecución de las pruebas

Desde la carpeta `evals/`:

```bash
cd evals
```

* **Para correr la evaluación en consola:**
  ```bash
  promptfoo eval --env-file ../.env
  ```

* **Para regenerar el reporte HTML:**
  ```bash
  promptfoo eval --env-file ../.env -o ../reports/promptfoo-report.html
  ```

* **Para abrir el panel interactivo de resultados en el navegador:**
  ```bash
  promptfoo view
  ```

---

## Enunciado original del laboratorio

### Universidad del Valle de Guatemala — Hoja de trabajo #6 - Evals — CC3116

**Objetivos**
- Familiarizarse con los evals, métricas, graders en la evaluación de sistemas de inteligencia artificial para asegurar la calidad de estos.

**Instrucciones**
Resuelvan el siguiente problema utilizando la herramienta/librería [promptfoo](https://www.promptfoo.dev/) para realizar los evals faltantes de la hoja de trabajo anterior. Utilizando la arquitectura que ustedes consideraron la mejor.
Se debe de entregar un link al repositorio con el código y el archivo de reporte generado por promptfoo.

**Problema**
Debido a que Parachute S.A. ya consideró el producto que ustedes realizaron como ya terminado, le ha indicado que tiene pronto la intención de ponerlo en productivo. Como buenos ingenieros, deciden cerrar el ciclo de desarrollo con el bloque faltante, los evals, ya que Parachute S.A. le ha advertido que seguirá iterando el producto.

Dado a que el agente actual que desarrolló tiene dos funcionalidades, agendar citas y resolver preguntas frecuentes, debe de realizar evals para ambos. Debe contener evals de:
- Factuality
- Determinísticos (contains/regex)
- Latencia
- Tool execution (verificar si las herramientas han sido llamadas correctamente)

**Recursos de guía:**
- [Promptfoo: Evaluate RAG](https://www.promptfoo.dev/docs/guides/evaluate-rag/)
- [Promptfoo: Getting Started](https://www.promptfoo.dev/docs/getting-started/)

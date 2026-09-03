# ai_engineering-hoja-4

Hoja de trabajo #4 — Herramientas (bases de datos vectoriales + tools/function calling) — CC3116, UVG.

> **Estado:** en planificación. Ver [PLAN.md](./PLAN.md) para el plan de acción y la división de trabajo del equipo.

## Cómo inicializar la infraestructura

> Pendiente de completar conforme se implemente `docker-compose.yml` y `db/init.sql` (ver [PLAN.md](./PLAN.md), sección de Persona A). Aquí quedará documentado:
> - Cómo levantar el contenedor de PostgreSQL + pgvector (Docker o Podman).
> - Cómo ejecutar el script de carga de embeddings.
> - Cómo ejecutar el agente de preguntas frecuentes.

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

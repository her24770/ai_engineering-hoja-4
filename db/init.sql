-- Se ejecuta automáticamente una sola vez, cuando el volumen de datos del
-- contenedor de Postgres está vacío (ver docker-compose.yml,
-- docker-entrypoint-initdb.d).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS faqs (
    id          SERIAL PRIMARY KEY,
    faq_code    TEXT NOT NULL UNIQUE,      -- ej. "FAQ-001", viene del corpus original
    category    TEXT NOT NULL,
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    metadata    JSONB,
    embedding   VECTOR(384) NOT NULL       -- 384 = dimensión de all-MiniLM-L6-v2
);

-- Índice HNSW para similitud coseno. No requiere que la tabla tenga datos
-- previos (a diferencia de ivfflat), por lo que se puede crear en el
-- arranque aunque la tabla todavía esté vacía.
CREATE INDEX IF NOT EXISTS faqs_embedding_hnsw_idx
    ON faqs USING hnsw (embedding vector_cosine_ops);

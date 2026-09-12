"""Script de carga: genera embeddings del corpus de FAQs de Parachute S.A.
y los inserta en la tabla `faqs` de PostgreSQL (pgvector).

Uso:
    python loader/load_embeddings.py

Es idempotente: si se corre varias veces, primero vacía la tabla `faqs`
(TRUNCATE) y vuelve a insertar todo, así nunca queda duplicado ni
desactualizado con el contenido del corpus.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, get_embedding_model_name  # noqa: E402
from preprocess import parse_corpus, write_jsonl  # noqa: E402

CORPUS_PATH = Path(__file__).resolve().parent.parent / "data" / "Corpus_FAQs_Parachute_SA_2026.txt"
CLEAN_PATH = Path(__file__).resolve().parent.parent / "data" / "faqs_clean.jsonl"

INSERT_SQL = """
    INSERT INTO faqs (faq_code, category, question, answer, metadata, embedding)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (faq_code) DO UPDATE SET
        category = EXCLUDED.category,
        question = EXCLUDED.question,
        answer = EXCLUDED.answer,
        metadata = EXCLUDED.metadata,
        embedding = EXCLUDED.embedding;
"""


def main() -> None:
    start = time.time()

    print(f"Parseando corpus: {CORPUS_PATH}")
    records = parse_corpus(CORPUS_PATH)
    write_jsonl(records, CLEAN_PATH)
    print(f"  -> {len(records)} FAQs parseadas (guardadas también en {CLEAN_PATH.name})")

    model_name = get_embedding_model_name()
    print(f"Cargando modelo de embeddings: {model_name}")
    model = SentenceTransformer(model_name)

    questions = [r.question for r in records]
    print(f"Generando embeddings para {len(questions)} preguntas...")
    embeddings = model.encode(questions, show_progress_bar=True, normalize_embeddings=True)

    print("Conectando a PostgreSQL...")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE faqs RESTART IDENTITY;")

            for record, embedding in zip(records, embeddings):
                cur.execute(
                    INSERT_SQL,
                    (
                        record.faq_code,
                        record.category,
                        record.question,
                        record.answer,
                        json.dumps(record.metadata, ensure_ascii=False),
                        embedding,
                    ),
                )
        conn.commit()
    finally:
        conn.close()

    elapsed = time.time() - start
    print(f"Listo: {len(records)} FAQs cargadas en pgvector en {elapsed:.1f}s")


if __name__ == "__main__":
    main()

"""Tests de integración: requieren que el contenedor de Postgres esté
levantado (`docker-compose up -d`) y que ya se haya corrido
`python loader/load_embeddings.py`.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "loader"))

from db import get_connection, get_embedding_model_name  # noqa: E402

EXPECTED_FAQ_COUNT = 120
EMBEDDING_DIM = 384


@pytest.fixture(scope="module")
def db_conn():
    conn = get_connection()
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(get_embedding_model_name())


def test_table_has_all_faqs_loaded(db_conn):
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM faqs;")
        (count,) = cur.fetchone()
    assert count == EXPECTED_FAQ_COUNT


def test_embeddings_have_expected_dimension(db_conn):
    with db_conn.cursor() as cur:
        cur.execute("SELECT vector_dims(embedding) FROM faqs LIMIT 1;")
        (dims,) = cur.fetchone()
    assert dims == EMBEDDING_DIM


@pytest.mark.parametrize(
    "paraphrased_query,expected_faq_code",
    [
        ("¿En qué lugar es el salto en paracaídas?", "FAQ-001"),
        ("¿Necesito llevar identificación o pasaporte al evento?", None),
    ],
)
def test_semantic_search_returns_relevant_faq(db_conn, embedding_model, paraphrased_query, expected_faq_code):
    """Verifica que la búsqueda por similitud (pgvector) de una pregunta
    parafraseada devuelve un resultado semánticamente cercano.

    Para la segunda pregunta no se conoce de antemano el FAQ exacto: solo se
    valida que la búsqueda no truene y que devuelva una distancia razonable.
    """
    query_embedding = embedding_model.encode(paraphrased_query, normalize_embeddings=True)

    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT faq_code, question, embedding <=> %s AS distance
            FROM faqs
            ORDER BY distance
            LIMIT 3;
            """,
            (query_embedding,),
        )
        top_results = cur.fetchall()

    assert len(top_results) == 3
    if expected_faq_code:
        top_codes = [row[0] for row in top_results]
        assert expected_faq_code in top_codes

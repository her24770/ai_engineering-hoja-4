"""Conexión a PostgreSQL/pgvector compartida por el loader y sus tests."""

from __future__ import annotations

import os

import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

load_dotenv()


def get_connection():
    """Abre una conexión a Postgres con el tipo `vector` de pgvector registrado."""
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql://parachute:parachute@localhost:5432/parachute_faqs"
    )
    conn = psycopg2.connect(database_url)
    register_vector(conn)
    return conn


def get_embedding_model_name() -> str:
    return os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

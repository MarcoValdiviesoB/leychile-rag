"""Vector store sobre Postgres + pgvector (pensado para Neon)."""
from __future__ import annotations

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector

from .config import settings

EXTENSION = "CREATE EXTENSION IF NOT EXISTS vector;"

TABLE = """
CREATE TABLE IF NOT EXISTS articulos (
    id          TEXT PRIMARY KEY,         -- ej: codigo-trabajo:art-22
    norma       TEXT NOT NULL,            -- ej: "Código del Trabajo"
    id_norma    TEXT,                     -- idNorma en LeyChile
    articulo    TEXT NOT NULL,            -- ej: "22"
    titulo      TEXT,                     -- epígrafe / libro / título
    texto       TEXT NOT NULL,            -- texto del artículo
    url         TEXT,                     -- link a LeyChile
    embedding   VECTOR(%(dim)s)
);
CREATE INDEX IF NOT EXISTS articulos_embedding_idx
    ON articulos USING hnsw (embedding vector_cosine_ops);
"""


def _raw_connect() -> psycopg.Connection:
    """Conexión sin registrar el tipo vector (para DDL inicial)."""
    return psycopg.connect(settings.database_url)


def connect() -> psycopg.Connection:
    """Conexión con el tipo vector registrado (la extensión ya debe existir)."""
    conn = psycopg.connect(settings.database_url)
    register_vector(conn)
    return conn


def init_schema() -> None:
    with _raw_connect() as conn, conn.cursor() as cur:
        cur.execute(EXTENSION)
        conn.commit()
        cur.execute(TABLE % {"dim": settings.embedding_dim})
        conn.commit()


def upsert(rows: list[dict]) -> int:
    sql = """
        INSERT INTO articulos (id, norma, id_norma, articulo, titulo, texto, url, embedding)
        VALUES (%(id)s, %(norma)s, %(id_norma)s, %(articulo)s, %(titulo)s, %(texto)s, %(url)s, %(embedding)s)
        ON CONFLICT (id) DO UPDATE SET
            texto = EXCLUDED.texto, titulo = EXCLUDED.titulo,
            url = EXCLUDED.url, embedding = EXCLUDED.embedding;
    """
    with connect() as conn, conn.cursor() as cur:
        cur.executemany(sql, rows)
        conn.commit()
        return len(rows)


def search(embedding, k: int = 5) -> list[dict]:
    sql = """
        SELECT id, norma, articulo, titulo, texto, url,
               1 - (embedding <=> %(e)s) AS score
        FROM articulos
        ORDER BY embedding <=> %(e)s
        LIMIT %(k)s;
    """
    with connect() as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(sql, {"e": Vector(embedding), "k": k})
        return cur.fetchall()

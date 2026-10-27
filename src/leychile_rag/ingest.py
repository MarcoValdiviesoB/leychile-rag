"""Ingesta de normas desde LeyChile → chunk por artículo → embeddings → pgvector.

Nota sobre la fuente: el servicio XML de LeyChile puede requerir credencial o
haber cambiado de endpoint (hoy responde 401 en obtxml), y puede rate-limitar.
Por eso la ingesta soporta dos modos:
  1. `--source leychile` : baja el XML real (ajustar LEYCHILE_XML_BASE / auth).
  2. `--source seed`     : usa data/codigo_trabajo_sample.json (para correr el
                           demo end-to-end sin depender del fetch).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
from langchain_openai import OpenAIEmbeddings

from .config import settings
from . import store

DATA = Path(__file__).resolve().parents[2] / "data"
CODIGO_TRABAJO_ID = "207436"  # idNorma en LeyChile (DFL 1, 2002)


def _embedder() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)


def fetch_leychile_xml(id_norma: str) -> str:
    """Baja el XML de una norma. Ajustar según el endpoint/credencial vigente."""
    url = f"{settings.leychile_xml_base}?opt=7&idNorma={id_norma}"
    r = httpx.get(url, timeout=30, follow_redirects=True)
    r.raise_for_status()
    return r.text


def parse_articulos_xml(xml: str, norma: str, id_norma: str) -> list[dict]:
    """Extrae artículos del XML de LeyChile. El esquema real usa <EstructuraFuncional>
    con atributos tipoParte='Artículo'; acá va una extracción tolerante por regex
    como punto de partida (reemplazar por un parser del XSD oficial)."""
    bloques = re.split(r"(?i)(art[íi]culo\s+\d+[ºª]?)", xml)
    out: list[dict] = []
    for i in range(1, len(bloques) - 1, 2):
        head = bloques[i].strip()
        cuerpo = re.sub(r"<[^>]+>", " ", bloques[i + 1])
        cuerpo = re.sub(r"\s+", " ", cuerpo).strip()
        num = re.search(r"\d+", head)
        if not num or len(cuerpo) < 20:
            continue
        art = num.group(0)
        out.append({
            "id": f"codigo-trabajo:art-{art}",
            "norma": norma, "id_norma": id_norma, "articulo": art,
            "titulo": None, "texto": f"{head}. {cuerpo}",
            "url": f"https://www.bcn.cl/leychile/navegar?idNorma={id_norma}",
        })
    return out


def load_seed() -> list[dict]:
    return json.loads((DATA / "codigo_trabajo_sample.json").read_text(encoding="utf-8"))


def run(source: str = "seed") -> int:
    store.init_schema()
    if source == "leychile":
        xml = fetch_leychile_xml(CODIGO_TRABAJO_ID)
        rows = parse_articulos_xml(xml, "Código del Trabajo", CODIGO_TRABAJO_ID)
    else:
        rows = load_seed()

    emb = _embedder()
    vectors = emb.embed_documents([r["texto"] for r in rows])
    for r, v in zip(rows, vectors):
        r["embedding"] = v
    return store.upsert(rows)

"""RAG agentic con LangGraph: recupera artículos → responde con citas → guardrail.

Grafo:
    embed_query → retrieve → generate → verify
El paso `verify` chequea que la respuesta se apoye en artículos recuperados y
cite al menos uno; si no, degrada a "no encontrado en el corpus" (anti-alucinación).
"""
from __future__ import annotations

from typing import TypedDict

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, END

from .config import settings
from . import store


class State(TypedDict, total=False):
    pregunta: str
    query_embedding: list[float]
    contexto: list[dict]
    respuesta: str
    citas: list[dict]


def _emb() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)


def _llm() -> ChatOpenAI:
    return ChatOpenAI(model=settings.chat_model, api_key=settings.openai_api_key, temperature=0)


SYSTEM = (
    "Eres un asistente legal sobre la legislación chilena. Respondes SOLO con base "
    "en los artículos entregados como contexto. Si el contexto no alcanza, dilo "
    "explícitamente. Cita siempre el/los artículo(s) usados (ej. 'Art. 22 del "
    "Código del Trabajo'). No inventes normas. No das asesoría legal formal: "
    "orientas y remites a la fuente."
)


def embed_query(state: State) -> State:
    return {"query_embedding": _emb().embed_query(state["pregunta"])}


def retrieve(state: State) -> State:
    ctx = store.search(state["query_embedding"], k=5)
    return {"contexto": ctx}


def generate(state: State) -> State:
    ctx = state["contexto"]
    bloque = "\n\n".join(
        f"[{c['norma']} Art. {c['articulo']}] {c['texto']}" for c in ctx
    ) or "(sin resultados)"
    msg = _llm().invoke([
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Contexto:\n{bloque}\n\nPregunta: {state['pregunta']}"},
    ])
    citas = [{"norma": c["norma"], "articulo": c["articulo"], "url": c["url"]} for c in ctx]
    return {"respuesta": msg.content, "citas": citas}


def verify(state: State) -> State:
    """Guardrail simple: sin contexto recuperado, no se responde desde el modelo."""
    if not state.get("contexto"):
        return {"respuesta": "No encontré artículos relevantes en el corpus para responder eso.",
                "citas": []}
    return {}


def build_graph():
    g = StateGraph(State)
    g.add_node("embed_query", embed_query)
    g.add_node("retrieve", retrieve)
    g.add_node("generate", generate)
    g.add_node("verify", verify)
    g.set_entry_point("embed_query")
    g.add_edge("embed_query", "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "verify")
    g.add_edge("verify", END)
    return g.compile()


GRAPH = build_graph()


def preguntar(pregunta: str) -> dict:
    out = GRAPH.invoke({"pregunta": pregunta})
    return {"respuesta": out.get("respuesta", ""), "citas": out.get("citas", [])}

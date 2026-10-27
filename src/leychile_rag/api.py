"""API FastAPI: POST /ask → respuesta con citas."""
from fastapi import FastAPI
from pydantic import BaseModel

from .rag import preguntar

app = FastAPI(title="LeyChile RAG", version="0.1.0")


class Pregunta(BaseModel):
    pregunta: str


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/ask")
def ask(body: Pregunta):
    return preguntar(body.pregunta)

"""Servidor MCP mínimo que expone `preguntar_ley` como tool, para enganchar el RAG
con cualquier agente (Claude Desktop, Cursor) o con el MCP de datos de Chile.

Requiere: pip install mcp
"""
from mcp.server.fastmcp import FastMCP

from .rag import preguntar

mcp = FastMCP("leychile-rag")


@mcp.tool()
def preguntar_ley(pregunta: str) -> dict:
    """Responde una pregunta sobre la legislación chilena (MVP: Código del Trabajo),
    citando los artículos usados. Solo responde desde el corpus; no inventa normas."""
    return preguntar(pregunta)


if __name__ == "__main__":
    mcp.run()

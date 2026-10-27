#!/usr/bin/env python3
"""Uso: python scripts/run_ingest.py [seed|leychile]"""
import sys
from leychile_rag.ingest import run

source = sys.argv[1] if len(sys.argv) > 1 else "seed"
n = run(source)
print(f"Ingestados {n} artículos (fuente: {source}).")

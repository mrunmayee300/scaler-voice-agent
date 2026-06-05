"""Shared utilities for ingestion pipeline."""

import asyncio
import os
import sys
from pathlib import Path
from typing import List

# Add backend to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


async def embed_and_store(
    collection: str,
    chunks: List[dict],
) -> int:
    from app.rag.embeddings import embed_texts
    from app.rag.qdrant_store import upsert_chunks
    from app.rag.retrieval import invalidate_bm25_cache

    if not chunks:
        return 0
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    embeddings = await embed_texts(texts)
    count = upsert_chunks(collection, texts, embeddings, metadatas)
    invalidate_bm25_cache()
    return count

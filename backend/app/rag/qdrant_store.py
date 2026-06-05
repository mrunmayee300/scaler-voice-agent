"""Qdrant vector store operations."""

import time
from typing import Any, Dict, List, Optional
from uuid import NAMESPACE_DNS, uuid4, uuid5

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import RetrievalChunk

logger = get_logger(__name__)

_client: QdrantClient | None = None
VECTOR_SIZE = 3072  # text-embedding-3-large
# 3072-dim vectors are large; small batches + long timeout for Qdrant Cloud
UPSERT_BATCH_SIZE = 10
UPSERT_MAX_RETRIES = 5
QDRANT_TIMEOUT_SEC = 120


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=QDRANT_TIMEOUT_SEC,
        )
    return _client


def ensure_collection(collection_name: str) -> None:
    client = get_qdrant_client()
    collections = [c.name for c in client.get_collections().collections]
    if collection_name not in collections:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(
                size=VECTOR_SIZE,
                distance=qmodels.Distance.COSINE,
            ),
        )
        logger.info("collection_created", collection=collection_name)


def upsert_chunks(
    collection_name: str,
    texts: List[str],
    embeddings: List[List[float]],
    metadatas: List[Dict[str, Any]],
) -> int:
    """Upsert document chunks into Qdrant."""
    ensure_collection(collection_name)
    client = get_qdrant_client()
    points = []
    for text, embedding, meta in zip(texts, embeddings, metadatas):
        # Qdrant accepts only UUID or unsigned integer point IDs
        chunk_id = meta.get("chunk_id")
        point_id = str(uuid5(NAMESPACE_DNS, chunk_id)) if chunk_id else str(uuid4())
        payload = {**meta, "text": text}
        points.append(
            qmodels.PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
            )
        )
    # Batch upsert with retries (Qdrant Cloud can timeout on large payloads)
    for i in range(0, len(points), UPSERT_BATCH_SIZE):
        batch = points[i : i + UPSERT_BATCH_SIZE]
        for attempt in range(UPSERT_MAX_RETRIES):
            try:
                client.upsert(
                    collection_name=collection_name,
                    points=batch,
                    wait=True,
                )
                logger.info(
                    "upsert_batch_ok",
                    collection=collection_name,
                    batch_start=i,
                    batch_size=len(batch),
                )
                break
            except Exception as e:
                if attempt == UPSERT_MAX_RETRIES - 1:
                    logger.error(
                        "upsert_failed",
                        collection=collection_name,
                        batch_start=i,
                        error=str(e),
                    )
                    raise
                delay = 2**attempt
                logger.warning(
                    "upsert_retry",
                    collection=collection_name,
                    attempt=attempt + 1,
                    delay_sec=delay,
                    error=str(e),
                )
                time.sleep(delay)
    return len(points)


def vector_search(
    collection_name: str,
    query_vector: List[float],
    top_k: int = 10,
    filter_conditions: Optional[qmodels.Filter] = None,
) -> List[RetrievalChunk]:
    """Perform vector similarity search."""
    client = get_qdrant_client()
    try:
        results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=filter_conditions,
            with_payload=True,
        )
    except Exception as e:
        logger.error("vector_search_failed", collection=collection_name, error=str(e))
        return []

    chunks: List[RetrievalChunk] = []
    for hit in results:
        payload = hit.payload or {}
        chunks.append(
            RetrievalChunk(
                id=str(hit.id),
                text=payload.get("text", ""),
                score=float(hit.score),
                metadata={k: v for k, v in payload.items() if k != "text"},
                collection=collection_name,
            )
        )
    return chunks


def get_all_texts_for_bm25(collection_name: str, limit: int = 10000) -> List[RetrievalChunk]:
    """Scroll collection to get documents for BM25 indexing."""
    client = get_qdrant_client()
    chunks: List[RetrievalChunk] = []
    try:
        offset = None
        while len(chunks) < limit:
            records, offset = client.scroll(
                collection_name=collection_name,
                limit=min(100, limit - len(chunks)),
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if not records:
                break
            for record in records:
                payload = record.payload or {}
                chunks.append(
                    RetrievalChunk(
                        id=str(record.id),
                        text=payload.get("text", ""),
                        score=0.0,
                        metadata={k: v for k, v in payload.items() if k != "text"},
                        collection=collection_name,
                    )
                )
            if offset is None:
                break
    except Exception as e:
        logger.warning("scroll_failed", collection=collection_name, error=str(e))
    return chunks


def health_check() -> str:
    try:
        client = get_qdrant_client()
        client.get_collections()
        return "healthy"
    except Exception as e:
        return f"unhealthy: {e}"

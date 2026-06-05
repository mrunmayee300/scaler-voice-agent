"""Hybrid retrieval with vector search, BM25, and RRF fusion."""

from collections import defaultdict
from typing import Dict, List, Tuple

from rank_bm25 import BM25Okapi

from app.config import get_settings
from app.core.logging import get_logger
from app.core.observability import get_metrics
from app.models.schemas import RetrievalChunk
from app.rag.embeddings import embed_query
from app.rag.qdrant_store import get_all_texts_for_bm25, vector_search

logger = get_logger(__name__)

# In-memory BM25 index cache per collection
_bm25_cache: Dict[str, Tuple[BM25Okapi, List[RetrievalChunk]]] = {}


def _tokenize(text: str) -> List[str]:
    return text.lower().split()


def _build_bm25_index(collection_name: str) -> Tuple[BM25Okapi, List[RetrievalChunk]]:
    if collection_name in _bm25_cache:
        return _bm25_cache[collection_name]
    chunks = get_all_texts_for_bm25(collection_name)
    if not chunks:
        empty = BM25Okapi([["placeholder"]])
        _bm25_cache[collection_name] = (empty, [])
        return empty, []
    tokenized = [_tokenize(c.text) for c in chunks]
    bm25 = BM25Okapi(tokenized)
    _bm25_cache[collection_name] = (bm25, chunks)
    return bm25, chunks


def reciprocal_rank_fusion(
    ranked_lists: List[List[Tuple[str, float]]],
    k: int = 60,
) -> List[Tuple[str, float]]:
    """Combine multiple ranked lists using RRF."""
    scores: Dict[str, float] = defaultdict(float)
    for ranked in ranked_lists:
        for rank, (doc_id, _) in enumerate(ranked):
            scores[doc_id] += 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def bm25_search(collection_name: str, query: str, top_k: int = 10) -> List[RetrievalChunk]:
    bm25, chunks = _build_bm25_index(collection_name)
    if not chunks:
        return []
    tokenized_query = _tokenize(query)
    scores = bm25.get_scores(tokenized_query)
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    results = []
    for idx in ranked_indices:
        if scores[idx] <= 0:
            continue
        chunk = chunks[idx]
        results.append(
            RetrievalChunk(
                id=chunk.id,
                text=chunk.text,
                score=float(scores[idx]),
                metadata=chunk.metadata,
                collection=collection_name,
            )
        )
    return results


async def hybrid_search(
    query: str,
    collections: List[str] | None = None,
    top_k: int | None = None,
) -> List[RetrievalChunk]:
    """
    Hybrid search across collections using vector + BM25 with RRF.
    """
    settings = get_settings()
    top_k = top_k or settings.retrieval_top_k
    collections = collections or list(settings.collections.values())

    query_vector = await embed_query(query)
    if not query_vector:
        get_metrics().record_failure("retrieval", "Failed to embed query")
        return []

    all_chunks: Dict[str, RetrievalChunk] = {}
    rrf_inputs: List[List[Tuple[str, float]]] = []

    for collection in collections:
        # Vector search
        vector_results = vector_search(collection, query_vector, top_k=top_k)
        vector_ranked = [(r.id, r.score) for r in vector_results]
        if vector_ranked:
            rrf_inputs.append(vector_ranked)
        for r in vector_results:
            all_chunks[r.id] = r

        # BM25 search
        bm25_results = bm25_search(collection, query, top_k=top_k)
        bm25_ranked = [(r.id, r.score) for r in bm25_results]
        if bm25_ranked:
            rrf_inputs.append(bm25_ranked)
        for r in bm25_results:
            if r.id not in all_chunks:
                all_chunks[r.id] = r

    if not rrf_inputs:
        get_metrics().record_failure("retrieval", "No results from any collection")
        return []

    fused = reciprocal_rank_fusion(rrf_inputs)
    results: List[RetrievalChunk] = []
    for doc_id, rrf_score in fused[:top_k]:
        if doc_id in all_chunks:
            chunk = all_chunks[doc_id]
            chunk.score = rrf_score
            results.append(chunk)

    logger.info(
        "hybrid_search_complete",
        query_preview=query[:80],
        results=len(results),
        collections=len(collections),
    )
    return results


def invalidate_bm25_cache() -> None:
    """Clear BM25 cache after re-ingestion."""
    global _bm25_cache
    _bm25_cache = {}

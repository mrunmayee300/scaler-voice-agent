"""Cross-encoder reranking with bge-reranker-large."""

from typing import List, Optional

from app.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import RetrievalChunk

logger = get_logger(__name__)

_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder

            settings = get_settings()
            _reranker = CrossEncoder(settings.reranker_model, max_length=512)
            logger.info("reranker_loaded", model=settings.reranker_model)
        except Exception as e:
            logger.info(
                "reranker_unavailable_using_rrf_scores",
                error=str(e),
                hint="pip install -r requirements-ml.txt for cross-encoder reranking",
            )
            _reranker = False  # type: ignore
    return _reranker if _reranker is not False else None


def rerank_chunks(
    query: str,
    chunks: List[RetrievalChunk],
    top_k: Optional[int] = None,
) -> List[RetrievalChunk]:
    """Rerank retrieved chunks using cross-encoder."""
    settings = get_settings()
    top_k = top_k or settings.rerank_top_k

    if not chunks:
        return []

    model = _get_reranker()
    if model is None:
        # Fallback: return by existing score
        return sorted(chunks, key=lambda c: c.score, reverse=True)[:top_k]

    pairs = [[query, chunk.text] for chunk in chunks]
    try:
        scores = model.predict(pairs)
        scored = list(zip(chunks, scores))
        scored.sort(key=lambda x: float(x[1]), reverse=True)
        results = []
        for chunk, score in scored[:top_k]:
            chunk.score = float(score)
            results.append(chunk)
        return results
    except Exception as e:
        logger.error("rerank_failed", error=str(e))
        return sorted(chunks, key=lambda c: c.score, reverse=True)[:top_k]

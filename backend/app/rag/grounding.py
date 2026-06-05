"""Anti-hallucination grounding layer with confidence scoring."""

import re
from typing import List, Tuple

from app.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import Citation, RetrievalChunk, SourceType
from app.rag.embeddings import embed_query, embed_texts

logger = get_logger(__name__)

REFUSAL_MESSAGE = (
    "I don't have enough information in my knowledge base to answer that accurately. "
    "I'd be happy to discuss topics covered in my resume, projects, or GitHub repositories."
)

LOW_CONFIDENCE_MESSAGE = (
    "Based on the available information, I'm not fully confident in a precise answer. "
    "Here's what I can share from my records, with the caveat that details may be incomplete."
)


def chunks_to_citations(chunks: List[RetrievalChunk]) -> List[Citation]:
    citations = []
    for chunk in chunks:
        meta = chunk.metadata
        source_type_str = meta.get("source_type", "resume")
        try:
            source_type = SourceType(source_type_str)
        except ValueError:
            if "commit" in source_type_str:
                source_type = SourceType.COMMIT
            elif "readme" in source_type_str or "github" in source_type_str:
                source_type = SourceType.GITHUB_README
            elif "project" in source_type_str:
                source_type = SourceType.PROJECT
            else:
                source_type = SourceType.RESUME

        citations.append(
            Citation(
                source=meta.get("source", "unknown"),
                source_type=source_type,
                repo=meta.get("repo"),
                commit_hash=meta.get("commit_hash"),
                date=meta.get("date"),
                file=meta.get("file"),
                chunk_id=meta.get("chunk_id"),
                excerpt=chunk.text[:300],
                relevance_score=chunk.score,
            )
        )
    return citations


async def compute_confidence(
    query: str,
    chunks: List[RetrievalChunk],
) -> float:
    """
    Compute grounding confidence based on:
    - Reranker scores (normalized)
    - Semantic similarity between query and top chunk
    - Number of supporting chunks
    """
    if not chunks:
        return 0.0

    settings = get_settings()

    # Score component: RRF/BM25 scores are ~0.01-0.05; cross-encoder scores are ~-10 to +10
    top_score = max(c.score for c in chunks)
    if top_score <= 1.0:
        # Reciprocal rank fusion scores (no cross-encoder reranker installed)
        rerank_component = min(1.0, max(0.0, top_score / 0.035))
    else:
        rerank_component = min(1.0, max(0.0, (top_score + 5) / 10))

    # Semantic similarity component
    query_emb = await embed_query(query)
    top_texts = [c.text[:2000] for c in chunks[:3]]
    chunk_embs = await embed_texts(top_texts)

    similarity_component = 0.0
    if query_emb and chunk_embs:
        import numpy as np

        q = np.array(query_emb)
        similarities = []
        for ce in chunk_embs:
            c = np.array(ce)
            sim = float(np.dot(q, c) / (np.linalg.norm(q) * np.linalg.norm(c) + 1e-9))
            similarities.append(sim)
        similarity_component = max(similarities) if similarities else 0.0

    # Coverage component
    coverage = min(1.0, len(chunks) / settings.rerank_top_k)

    confidence = (
        0.45 * rerank_component
        + 0.40 * similarity_component
        + 0.15 * coverage
    )
    return round(min(1.0, max(0.0, confidence)), 3)


def should_refuse(confidence: float, chunks: List[RetrievalChunk]) -> Tuple[bool, str | None]:
    settings = get_settings()
    if not chunks:
        return True, REFUSAL_MESSAGE
    if confidence < settings.confidence_threshold:
        return True, REFUSAL_MESSAGE
    return False, None


def verify_answer_grounding(
    answer: str,
    chunks: List[RetrievalChunk],
) -> Tuple[bool, List[str]]:
    """
    Post-generation check: flag potential hallucinations.
    Returns (is_grounded, warnings).
    """
    warnings: List[str] = []
    if not chunks:
        return False, ["No evidence chunks available"]

    # Extract key factual claims (numbers, dates, proper nouns)
    claim_patterns = [
        r"\b\d{4}\b",  # years
        r"\b\d+%\b",  # percentages
        r"\b\d+\+?\s*years?\b",
    ]
    evidence_text = " ".join(c.text.lower() for c in chunks)

    for pattern in claim_patterns:
        claims = re.findall(pattern, answer, re.IGNORECASE)
        for claim in claims:
            if claim.lower() not in evidence_text:
                warnings.append(f"Unverified claim in answer: {claim}")

    # Check for definitive statements without evidence keywords
    definitive_phrases = [
        "i led",
        "i built",
        "i designed",
        "i implemented",
        "i managed",
        "i created",
    ]
    answer_lower = answer.lower()
    for phrase in definitive_phrases:
        if phrase in answer_lower:
            # Verify some overlap with evidence
            phrase_context = answer_lower[answer_lower.find(phrase) : answer_lower.find(phrase) + 100]
            if not any(word in evidence_text for word in phrase_context.split() if len(word) > 4):
                warnings.append(f"Potentially ungrounded statement near: {phrase}")

    is_grounded = len(warnings) == 0
    return is_grounded, warnings

"""Tests for grounding layer."""

import pytest

from app.rag.grounding import (
    REFUSAL_MESSAGE,
    chunks_to_citations,
    should_refuse,
    verify_answer_grounding,
)


class TestGrounding:
    def test_should_refuse_no_chunks(self):
        refused, reason = should_refuse(0.9, [])
        assert refused
        assert REFUSAL_MESSAGE in (reason or "")

    def test_should_refuse_low_confidence(self):
        from app.models.schemas import RetrievalChunk

        chunks = [
            RetrievalChunk(
                id="1", text="test", score=0.1, metadata={}, collection="c"
            )
        ]
        refused, _ = should_refuse(0.1, chunks)
        assert refused

    def test_should_not_refuse_high_confidence(self, sample_chunks):
        refused, _ = should_refuse(0.9, sample_chunks)
        assert not refused

    def test_chunks_to_citations(self, sample_chunks):
        citations = chunks_to_citations(sample_chunks)
        assert len(citations) == 2
        assert citations[0].repo == "voice-assistant"

    def test_verify_grounding(self, sample_chunks):
        answer = "I built a voice assistant using FastAPI and Qdrant."
        grounded, warnings = verify_answer_grounding(answer, sample_chunks)
        assert grounded or len(warnings) == 0

    def test_verify_ungrounded_year(self, sample_chunks):
        answer = "In 1842 I started working on quantum computing."
        grounded, warnings = verify_answer_grounding(answer, sample_chunks)
        assert not grounded or len(warnings) > 0

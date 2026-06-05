"""Tests for retrieval and reranking."""

import pytest

from app.rag.retrieval import reciprocal_rank_fusion


class TestRRF:
    def test_fusion_combines_lists(self):
        list1 = [("a", 0.9), ("b", 0.8), ("c", 0.7)]
        list2 = [("b", 0.95), ("d", 0.6), ("a", 0.5)]
        fused = reciprocal_rank_fusion([list1, list2])
        ids = [doc_id for doc_id, _ in fused]
        assert "b" in ids[:2]
        assert len(fused) == 4

    def test_single_list(self):
        ranked = [("x", 1.0), ("y", 0.5)]
        fused = reciprocal_rank_fusion([ranked])
        assert fused[0][0] == "x"

    def test_empty_lists(self):
        fused = reciprocal_rank_fusion([])
        assert fused == []


class TestReranker:
    def test_rerank_empty(self):
        from app.rag.reranker import rerank_chunks

        result = rerank_chunks("test query", [])
        assert result == []

    def test_rerank_with_chunks(self, sample_chunks):
        from app.rag.reranker import rerank_chunks

        result = rerank_chunks("voice assistant RAG", sample_chunks, top_k=2)
        assert len(result) <= 2

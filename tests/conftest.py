"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


@pytest.fixture
def sample_chunks():
    from app.models.schemas import RetrievalChunk

    return [
        RetrievalChunk(
            id="1",
            text="Built a voice assistant using FastAPI and Qdrant for RAG retrieval.",
            score=0.8,
            metadata={
                "source": "github_readme_voice-assistant",
                "source_type": "github_readme",
                "repo": "voice-assistant",
            },
            collection="test",
        ),
        RetrievalChunk(
            id="2",
            text="Implemented hybrid search with BM25 and vector search using RRF fusion.",
            score=0.7,
            metadata={
                "source": "github_readme_voice-assistant",
                "source_type": "github_readme",
                "repo": "voice-assistant",
            },
            collection="test",
        ),
    ]

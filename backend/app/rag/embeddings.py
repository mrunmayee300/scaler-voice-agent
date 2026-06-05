"""OpenAI embedding generation."""

from typing import List

from openai import AsyncOpenAI

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a batch of texts."""
    if not texts:
        return []
    settings = get_settings()
    client = get_openai_client()
    # OpenAI allows up to 2048 inputs per request; batch in chunks of 100
    all_embeddings: List[List[float]] = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = await client.embeddings.create(
            model=settings.openai_embedding_model,
            input=batch,
        )
        sorted_data = sorted(response.data, key=lambda x: x.index)
        all_embeddings.extend([d.embedding for d in sorted_data])
    return all_embeddings


async def embed_query(query: str) -> List[float]:
    """Generate embedding for a single query."""
    result = await embed_texts([query])
    return result[0] if result else []

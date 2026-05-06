"""OpenAI embeddings helpers."""
from __future__ import annotations

import openai

from app.config import get_settings

settings = get_settings()
_client: openai.AsyncOpenAI | None = None


def _get_client() -> openai.AsyncOpenAI:
    global _client
    if _client is None:
        _client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return embeddings for a list of texts (batched)."""
    client = _get_client()
    # OpenAI supports up to 2048 inputs per call; batch in groups of 100
    all_embeddings: list[list[float]] = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = await client.embeddings.create(
            input=batch, model=settings.openai_embedding_model
        )
        all_embeddings.extend([item.embedding for item in response.data])
    return all_embeddings


async def embed_query(query: str) -> list[float]:
    """Return a single embedding for a query string."""
    result = await embed_texts([query])
    return result[0]

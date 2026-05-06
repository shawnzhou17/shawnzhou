"""pgvector cosine-similarity retrieval."""
from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.document import Document, DocumentChunk
from app.services.embeddings import embed_query

settings = get_settings()


async def retrieve_chunks(
    query: str, db: AsyncSession, top_k: int | None = None
) -> list[dict]:
    """Return the top-k most similar chunks for *query*."""
    k = top_k or settings.top_k
    q_embedding = await embed_query(query)

    # pgvector cosine distance operator: <=>
    stmt = (
        select(
            DocumentChunk.id,
            DocumentChunk.content,
            DocumentChunk.document_id,
            DocumentChunk.chunk_index,
            Document.filename,
            (
                text("1 - (document_chunks.embedding <=> cast(:emb AS vector))")
            ).label("similarity"),
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.embedding.isnot(None))
        .order_by(text("document_chunks.embedding <=> cast(:emb AS vector)"))
        .limit(k)
    )

    result = await db.execute(stmt, {"emb": str(q_embedding)})
    rows = result.mappings().all()

    return [
        {
            "chunk_id": str(row["id"]),
            "document_id": str(row["document_id"]),
            "filename": row["filename"],
            "chunk_index": row["chunk_index"],
            "content": row["content"],
            "similarity": float(row["similarity"]),
        }
        for row in rows
        if float(row["similarity"]) >= settings.similarity_threshold
    ]

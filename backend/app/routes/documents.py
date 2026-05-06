"""Document upload and listing routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.document import Document, DocumentChunk
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts
from app.utils.pdf_parser import extract_text_from_pdf

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {"application/pdf", "text/markdown", "text/plain"}
ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt"}


class DocumentOut(BaseModel):
    id: str
    filename: str
    file_type: str
    chunk_count: int

    class Config:
        from_attributes = True


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF or Markdown file, chunk it, embed, and store in DB."""
    suffix = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    raw = await file.read()

    if suffix == ".pdf":
        text = extract_text_from_pdf(raw)
        file_type = "pdf"
    else:
        text = raw.decode("utf-8", errors="replace")
        file_type = "md"

    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract text from the uploaded file.",
        )

    # Create document record
    doc = Document(filename=file.filename or "unknown", file_type=file_type)
    db.add(doc)
    await db.flush()  # get doc.id without committing

    # Chunk and embed
    chunks = chunk_text(text)
    embeddings = await embed_texts(chunks)

    for idx, (chunk_text_val, embedding) in enumerate(zip(chunks, embeddings)):
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=idx,
            content=chunk_text_val,
            embedding=embedding,
        )
        db.add(chunk)

    return DocumentOut(
        id=str(doc.id),
        filename=doc.filename,
        file_type=doc.file_type,
        chunk_count=len(chunks),
    )


@router.get("/", response_model=list[DocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all uploaded documents."""
    stmt = select(Document)
    result = await db.execute(stmt)
    docs = result.scalars().all()

    out = []
    for doc in docs:
        chunk_stmt = select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        chunk_result = await db.execute(chunk_stmt)
        chunks = chunk_result.scalars().all()
        out.append(
            DocumentOut(
                id=str(doc.id),
                filename=doc.filename,
                file_type=doc.file_type,
                chunk_count=len(chunks),
            )
        )
    return out


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a document and all its chunks."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID.")

    result = await db.execute(select(Document).where(Document.id == doc_uuid))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    await db.delete(doc)

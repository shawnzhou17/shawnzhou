"""Chat routes – streaming RAG responses with conversation memory."""
from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

import openai
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.document import Conversation, Message
from app.services.retrieval import retrieve_chunks

settings = get_settings()
router = APIRouter(prefix="/chat", tags=["chat"])

_openai_client: openai.AsyncOpenAI | None = None


def _get_openai() -> openai.AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


SYSTEM_PROMPT = """You are AskShawn-AI, a helpful knowledge assistant.
Answer questions based on the provided context snippets.
If the context does not contain enough information, say so honestly.
Always cite your sources by referencing the [Source N] tags in the context.
Be concise and precise."""


class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class ConversationOut(BaseModel):
    id: str
    message_count: int


@router.post("/")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Streaming RAG chat endpoint.
    Returns Server-Sent Events with delta text, then a final citations event.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # --- Conversation memory ---
    if req.conversation_id:
        try:
            conv_uuid = uuid.UUID(req.conversation_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid conversation_id.")
        result = await db.execute(
            select(Conversation).where(Conversation.id == conv_uuid)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")
    else:
        conversation = Conversation()
        db.add(conversation)
        await db.flush()

    # Load previous messages (last 10 turns = 20 messages)
    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(20)
    )
    history = list(reversed(msg_result.scalars().all()))

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=req.question,
    )
    db.add(user_msg)
    await db.flush()

    # --- RAG retrieval ---
    chunks = await retrieve_chunks(req.question, db)
    context_parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i}] ({chunk['filename']}, chunk {chunk['chunk_index']})\n"
            f"{chunk['content']}"
        )
    context_str = "\n\n---\n\n".join(context_parts)

    # --- Build messages for OpenAI ---
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context_str:
        messages.append(
            {
                "role": "system",
                "content": f"Context from knowledge base:\n\n{context_str}",
            }
        )
    for m in history:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": req.question})

    conversation_id_str = str(conversation.id)
    await db.commit()

    citations = [
        {
            "source_num": i + 1,
            "filename": c["filename"],
            "chunk_index": c["chunk_index"],
            "similarity": round(c["similarity"], 3),
            "excerpt": c["content"][:200] + ("…" if len(c["content"]) > 200 else ""),
        }
        for i, c in enumerate(chunks)
    ]

    async def event_stream() -> AsyncIterator[str]:
        client = _get_openai()
        full_response = ""
        try:
            stream = await client.chat.completions.create(
                model=settings.openai_chat_model,
                messages=messages,  # type: ignore[arg-type]
                stream=True,
                temperature=0.2,
                max_tokens=1024,
            )
            async for chunk_obj in stream:
                delta = chunk_obj.choices[0].delta.content or ""
                if delta:
                    full_response += delta
                    yield f"data: {json.dumps({'type': 'delta', 'content': delta})}\n\n"

            # Persist assistant message
            async with AsyncSession(db.bind) as save_session:  # type: ignore[attr-defined]
                asst_msg = Message(
                    conversation_id=uuid.UUID(conversation_id_str),
                    role="assistant",
                    content=full_response,
                )
                save_session.add(asst_msg)
                await save_session.commit()

        except openai.OpenAIError:
            yield f"data: {json.dumps({'type': 'error', 'content': 'An error occurred while generating the response. Please try again.'})}\n\n"
            return

        yield (
            f"data: {json.dumps({'type': 'citations', 'citations': citations, 'conversation_id': conversation_id_str})}\n\n"
        )
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Conversation-Id": conversation_id_str,
        },
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    """List all conversations."""
    result = await db.execute(select(Conversation))
    convs = result.scalars().all()
    out = []
    for conv in convs:
        msg_result = await db.execute(
            select(Message).where(Message.conversation_id == conv.id)
        )
        count = len(msg_result.scalars().all())
        out.append(ConversationOut(id=str(conv.id), message_count=count))
    return out


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get all messages in a conversation."""
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation_id.")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_uuid)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    return [
        {"id": str(m.id), "role": m.role, "content": m.content}
        for m in messages
    ]

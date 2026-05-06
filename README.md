# AskShawn-AI 🧠

A production-style AI knowledge assistant built with **FastAPI**, **React**, **PostgreSQL + pgvector**, and **OpenAI**. Upload PDFs or Markdown files and ask questions — the assistant retrieves the most relevant passages, streams an answer, and cites every source.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Browser                                 │
│   React + Tailwind  ←──── SSE stream ────→  Vite dev / Nginx   │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / SSE
┌────────────────────────────▼────────────────────────────────────┐
│                        FastAPI Backend                           │
│                                                                  │
│   POST /api/documents/upload                                     │
│     └─ PDF / MD text extraction                                  │
│     └─ Token-based chunking (tiktoken)                           │
│     └─ OpenAI text-embedding-3-small  →  pgvector store         │
│                                                                  │
│   POST /api/chat/          (streaming SSE)                       │
│     └─ Embed query → pgvector cosine search                      │
│     └─ Build context from top-K chunks                           │
│     └─ OpenAI GPT-4o-mini (streaming)                            │
│     └─ Persist conversation + messages                           │
│     └─ Emit [delta | citations | DONE] events                    │
└────────────────────────────┬────────────────────────────────────┘
                             │ asyncpg
┌────────────────────────────▼────────────────────────────────────┐
│              PostgreSQL 16 + pgvector extension                  │
│                                                                  │
│   documents          document_chunks (embedding vector(1536))    │
│   conversations      messages                                    │
└─────────────────────────────────────────────────────────────────┘
```

### RAG Pipeline

1. **Ingest** — PDF bytes → `PyPDF2` text extraction OR raw Markdown decode
2. **Chunk** — Sliding window of 512 tokens with 64-token overlap (`tiktoken`)
3. **Embed** — `text-embedding-3-small` (1 536 dims) via OpenAI Embeddings API
4. **Store** — `pgvector` `vector(1536)` column in `document_chunks`
5. **Retrieve** — cosine distance `<=>` operator, top-5 chunks above similarity threshold
6. **Generate** — GPT-4o-mini with injected context + conversation history (last 10 turns), streamed over SSE
7. **Cite** — Citations emitted as a final SSE event containing filename, chunk index, similarity score, and excerpt

---

## Project Structure

```
askshawn-ai/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, lifespan
│   │   ├── config.py          # pydantic-settings environment config
│   │   ├── database.py        # SQLAlchemy async engine + session
│   │   ├── models/
│   │   │   └── document.py    # Document, DocumentChunk, Conversation, Message ORM
│   │   ├── routes/
│   │   │   ├── documents.py   # Upload, list, delete endpoints
│   │   │   └── chat.py        # Streaming chat + conversation history endpoints
│   │   ├── services/
│   │   │   ├── chunking.py    # tiktoken sliding-window chunker
│   │   │   ├── embeddings.py  # OpenAI embeddings (batched)
│   │   │   └── retrieval.py   # pgvector cosine similarity search
│   │   └── utils/
│   │       └── pdf_parser.py  # PyPDF2 text extraction
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Root layout (sidebar + chat)
│   │   ├── index.css          # Tailwind CSS entry
│   │   ├── main.jsx           # React DOM render
│   │   └── components/
│   │       ├── ChatInterface.jsx   # SSE streaming chat + message list
│   │       ├── DocumentUpload.jsx  # Drag-and-drop file uploader
│   │       ├── MessageBubble.jsx   # Markdown messages + citations
│   │       └── Sidebar.jsx         # Document list + upload + new chat
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── package.json
│   ├── nginx.conf             # Production nginx proxy config
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Quick Start

### 1 — Copy environment variables

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...
```

### 2 — Start with Docker Compose

```bash
docker compose up --build
```

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:3000        |
| Backend  | http://localhost:8000        |
| API Docs | http://localhost:8000/docs   |
| DB       | localhost:5432               |

### 3 — Use the app

1. Open **http://localhost:3000**
2. Upload a PDF or Markdown file via the sidebar
3. Ask a question in the chat box
4. Expand the **Sources** badge to see citations

---

## API Reference

### Documents

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/documents/upload` | Upload PDF or Markdown (multipart/form-data `file`) |
| `GET`  | `/api/documents/` | List all documents |
| `DELETE` | `/api/documents/{id}` | Delete a document and its chunks |

### Chat

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat/` | Streaming SSE chat (JSON body: `question`, optional `conversation_id`) |
| `GET`  | `/api/chat/conversations` | List conversations |
| `GET`  | `/api/chat/conversations/{id}/messages` | Get messages in a conversation |

### SSE Event Types

```jsonc
{ "type": "delta",     "content": "Hello" }          // text chunk
{ "type": "citations", "citations": [...], "conversation_id": "..." }
{ "type": "error",     "content": "..." }
"[DONE]"
```

---

## Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # set DATABASE_URL to local Postgres + OPENAI_API_KEY
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000, proxies /api → localhost:8000
```

---

## Configuration

All settings are in `.env` (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(required)* | Your OpenAI secret key |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | Chat completion model |
| `CHUNK_SIZE` | `512` | Max tokens per chunk |
| `CHUNK_OVERLAP` | `64` | Overlap tokens between chunks |
| `TOP_K` | `5` | Max chunks to retrieve |
| `SIMILARITY_THRESHOLD` | `0.3` | Minimum cosine similarity to include a chunk |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + Uvicorn |
| LLM / Embeddings | OpenAI GPT-4o-mini / text-embedding-3-small |
| Vector DB | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2 (async) |
| PDF Parsing | PyPDF2 |
| Tokenization | tiktoken (cl100k_base) |
| Frontend | React 18 + Vite + Tailwind CSS |
| Streaming | Server-Sent Events (SSE) |
| Container | Docker + Docker Compose |

# Lenny Growth Assistant — powered by Lenny GrowthOS

> **From podcast wisdom to evidence-backed execution.**

A production-minded, full-stack AI application that turns Lenny's Podcast and Newsletter transcripts into grounded growth recommendations, structured decision briefs, ~1,250-word essays, and interactive HTML/CSS artifacts.

---

## Table of Contents

1. [Architecture Overview](#architecture)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Running Locally](#running-locally)
6. [Using the Application](#using-the-application)
7. [API Reference](#api-reference)
8. [Testing](#testing)
9. [Ingestion Pipeline](#ingestion-pipeline)
10. [AI Provider Setup](#ai-provider-setup)
11. [Security Model](#security-model)
12. [Project Structure](#project-structure)
13. [Design Decisions](#design-decisions)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Lenny Growth Assistant                       │
│                                                                 │
│  React/Vite Frontend          FastAPI Backend                   │
│  ─────────────────────        ─────────────────────────────     │
│  ChatView                     /api/sessions (CRUD)              │
│  EvidencePanel         ◄──►   /api/sessions/{id}/messages       │
│  ArtifactViewer               /api/sources (knowledge base)     │
│  WritingStudio                /api/ingestion/jobs               │
│  KnowledgeBase                /api/artifacts                    │
│  Settings                     /api/skills/ship-30-essay         │
│                               /api/models                       │
│                               /api/health, /api/ready           │
│                                                                 │
│  Backend Modules:                                               │
│  ─────────────────────────────────────────────────────────      │
│  GrowthAgent           ←  Intent classification + routing       │
│  RetrievalService      ←  Embedding/keyword retrieval           │
│  IngestionService      ←  GitHub fetch + chunk + embed          │
│  EssaySkill            ←  Ship 30 for 30 essay generation       │
│  ArtifactGenerator     ←  HTML/Markdown artifacts               │
│  LLM Providers         ←  OllamaProvider | AnthropicProvider    │
│  EmbeddingProviders    ←  SimpleTFIDF | OllamaEmbedder          │
│                                                                 │
│  Persistence: PostgreSQL                                        │
│  ─────────────────────────────────────────────────────────      │
│  conversations → messages → sources → transcript_chunks         │
│  artifacts, ingestion_jobs, evaluation_records                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | ≥ 3.8 | Tested on 3.8.0 |
| Node.js | ≥ 18 | For frontend dev server |
| PostgreSQL | ≥ 13 | Primary persistence layer |
| Ollama | Latest | Optional — for local LLM inference |

**Optional:**
- Anthropic API key (for Claude as the LLM provider)

---

## Quick Start

```powershell
# 1. Clone / navigate to project
cd "The Lenny Growth Assistant"

# 2. Copy environment template
copy .env.example .env
# Edit .env — set DATABASE_URL, ANTHROPIC_API_KEY (if using Claude)

# 3. Create the PostgreSQL database
psql -U postgres -c "CREATE DATABASE lenny_growth;"

# 4. Install backend dependencies
cd backend
pip install fastapi uvicorn[standard] sqlalchemy alembic pydantic-settings
pip install httpx anthropic aiofiles numpy python-dotenv psycopg2-binary

# 5. Run database migrations
python -m alembic upgrade head

# 6. Start backend
python -m uvicorn app.main:app --reload --port 8000

# 7. In another terminal, start frontend
cd ../frontend
npm install
npm run dev

# 8. Open http://localhost:5173
# 9. Go to Knowledge Base → click "Ingest Transcripts"
# 10. Wait for ingestion, then start chatting!
```

Or use the one-command starter:
```powershell
python start.py --frontend
```

---

## Configuration

All configuration via environment variables (`.env` file):

```env
# ── Database ──────────────────────────────────────────────────────
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/lenny_growth

# ── LLM Provider ─────────────────────────────────────────────────
LLM_PROVIDER=ollama                   # "ollama" or "anthropic"

# ── Ollama (Local, default) ───────────────────────────────────────
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b                # Any model you've pulled

# ── Anthropic (Cloud) ─────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...          # Only needed if LLM_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-sonnet-4-5     # Or claude-3-5-haiku-20241022

# ── Embeddings ────────────────────────────────────────────────────
EMBEDDING_PROVIDER=simple             # "simple" (TF-IDF) or "ollama"
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# ── Retrieval ─────────────────────────────────────────────────────
RETRIEVAL_TOP_K=5
RETRIEVAL_MIN_SCORE=0.1
```

**Provider switching rule:** Change `LLM_PROVIDER` in `.env` and restart — never silently falls through to cloud providers.

---

## Running Locally

### Backend

```powershell
cd backend

# Development (auto-reload)
python -m uvicorn app.main:app --reload --port 8000

# Production
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

API docs available at: `http://localhost:8000/api/docs`

### Frontend

```powershell
cd frontend
npm run dev          # Dev server on http://localhost:5173
npm run build        # Production build → frontend/dist/
```

---

## Using the Application

### 1. Ingest Transcripts

**First-time setup:** Go to **Knowledge Base** → click **Ingest Transcripts**.

This fetches all transcripts from the official [LennysNewsletter GitHub repository](https://github.com/LennysNewsletter/lennys-newsletterpodcastdata), chunks them, embeds them using your configured embedding provider, and indexes them into PostgreSQL.

Progress is shown in real-time. The process takes 3–10 minutes depending on network speed.

### 2. Chat Modes

Select a mode from the dropdown in the chat header:

| Mode | What It Does |
|------|-------------|
| **Standard Answer** | Grounded Q&A with evidence retrieval and source citations |
| **Decision Brief** | Structured brief: Question → Evidence → Recommendation → Experiment → Metrics → Risks |
| **Ship 30 Essay** | ~1,250-word essay in Ship 30 for 30 style, evidence-backed |
| **HTML Artifact** | Generates a static HTML/CSS page or component |

### 3. Evidence Trail

Every assistant response shows a grounding badge:
- ✓ **Grounded** — directly supported by retrieved transcripts
- ~ **Partially Grounded** — some claims from transcripts, some general knowledge
- ○ **General Knowledge** — no relevant transcripts found
- ✗ **Declined** — insufficient evidence to answer responsibly

Click **"X sources"** on any message to open the Evidence Trail panel showing retrieved chunks with scores and excerpts.

### 4. Writing Studio

Navigate to **Writing Studio** to generate standalone essays. Enter a thesis, specify the audience, and click Generate. The result is ~1,250 words following Ship 30 for 30 structure.

### 5. Artifacts

All generated HTML pages and markdown artifacts appear in the **Artifact Library**. HTML artifacts render in a sandboxed iframe (no JavaScript). You can edit, copy, and download artifacts.

---

## API Reference

Full interactive docs: `http://localhost:8000/api/docs`

### Key endpoints

```
GET  /api/health                        Liveness check
GET  /api/ready                         Readiness check with component statuses

POST /api/sessions                      Create conversation
GET  /api/sessions                      List conversations
GET  /api/sessions/{id}                 Get conversation
DELETE /api/sessions/{id}               Delete conversation

POST /api/sessions/{id}/messages        Send message → get response
GET  /api/sessions/{id}/messages        Get message history

GET  /api/sources                       List indexed transcript sources
POST /api/ingestion/jobs                Start ingestion job
GET  /api/ingestion/jobs/{id}           Poll job status

POST /api/artifacts                     Generate artifact
GET  /api/artifacts/{id}                Get artifact
PATCH /api/artifacts/{id}               Update artifact title/content

POST /api/skills/ship-30-essay          Generate Ship 30 essay
GET  /api/models                        List available LLM providers
```

### Message request body

```json
{
  "content": "What do transcripts say about user retention?",
  "mode": "standard",       // or "decision_brief", "essay", "html_artifact"
  "provider": null          // null = use configured default
}
```

---

## Testing

### Unit tests (no database required)

```powershell
cd backend
python -m pytest tests/test_backend.py -m "not integration" -v
```

**Expected:** 24 passing, 3 skipped (integration)

### Integration tests (requires PostgreSQL)

```powershell
cd backend
python -m pytest tests/test_backend.py -v
```

### What's tested

- Configuration loading and validation
- TF-IDF embedding and cosine similarity
- Transcript chunking (basic + speaker-aware)
- Intent classification (standard/essay/brief/artifact)
- Citation extraction and validation
- Essay word count and title extraction
- Artifact type allowlist enforcement
- HTML sandboxing logic
- Artifact size limits
- Ollama provider connection error handling
- Anthropic provider unavailability
- Provider factory defaults
- Session isolation (integration)
- Conversation CRUD (integration)

---

## Ingestion Pipeline

```
GitHub API → file list
     ↓
Raw markdown download (each transcript)
     ↓
Metadata extraction (from index.json + frontmatter)
     ↓
Content parsing (heading-aware, speaker-turn-aware chunking)
     ↓
Embedding generation (TF-IDF or Ollama neural)
     ↓
Deduplication (SHA-256 content hash)
     ↓
PostgreSQL persistence (sources + transcript_chunks)
```

**Chunk strategy:** Chunks split on:
1. Markdown section headings (`##`, `###`)
2. Speaker turns (`**Name**:`)
3. Soft size limit (800 chars) with 100-char overlap

**Re-ingestion:** Content-hash based — unchanged files are skipped automatically.

---

## AI Provider Setup

### Ollama (default, local)

```powershell
# Install Ollama from https://ollama.com
ollama serve                           # Start server
ollama pull gemma3:4b                  # Pull LLM
ollama pull nomic-embed-text           # Pull embedding model (optional)
```

In `.env`:
```
LLM_PROVIDER=ollama
OLLAMA_MODEL=gemma3:4b
EMBEDDING_PROVIDER=simple              # Use simple TF-IDF if no Ollama embeddings
```

### Anthropic / Claude

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-sonnet-4-5
```

> **Note:** `ANTHROPIC_API_KEY` is never sent to the frontend or logged.

---

## Security Model

| Concern | Mitigation |
|---------|-----------|
| Prompt injection | User input and transcript evidence are labeled as untrusted in every system prompt |
| Fabricated citations | Citations are validated against retrieved chunk IDs before display |
| HTML artifact XSS | Rendered in `<iframe sandbox="allow-same-origin">` — no scripts, no parent DOM access |
| API key exposure | Keys are environment-only; never returned in API responses or logged |
| Transcript integrity | Content-hash deduplication; never modifies source content |
| Session isolation | Each conversation only sees its own messages; no cross-session leakage |

---

## Project Structure

```
The Lenny Growth Assistant/
├── .env.example                    # Template — copy to .env
├── start.py                        # One-command startup helper
├── README.md                       # This file
│
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, middleware, router registration
│   │   ├── core/
│   │   │   ├── config.py           # Pydantic settings (all config from env)
│   │   │   └── logging.py          # Structured logging setup
│   │   ├── db/
│   │   │   └── session.py          # SQLAlchemy engine (lazy init)
│   │   ├── models/
│   │   │   └── models.py           # ORM models (all tables)
│   │   ├── schemas/
│   │   │   └── schemas.py          # Pydantic request/response schemas
│   │   ├── api/
│   │   │   ├── sessions.py         # Conversation CRUD
│   │   │   ├── messages.py         # Message handling (calls GrowthAgent)
│   │   │   ├── sources.py          # Knowledge base listing
│   │   │   ├── ingestion.py        # Ingestion job management
│   │   │   ├── artifacts.py        # Artifact CRUD
│   │   │   ├── skills.py           # Ship 30 essay endpoint
│   │   │   └── models.py           # Provider availability
│   │   ├── agents/
│   │   │   └── growth_agent.py     # Core agent: intent, retrieval, generation
│   │   ├── ingestion/
│   │   │   └── ingestion_service.py # Transcript pipeline
│   │   ├── retrieval/
│   │   │   └── retrieval_service.py # Embedding + keyword search
│   │   ├── providers/
│   │   │   ├── llm_providers.py    # Ollama + Anthropic adapters
│   │   │   └── embedding_providers.py # TF-IDF + Ollama embedders
│   │   ├── skills/
│   │   │   └── essay_skill.py      # Ship 30 for 30 essay writer
│   │   └── artifacts/
│   │       └── artifact_generator.py # HTML/Markdown artifact generator
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_initial.py     # Initial schema migration
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_backend.py         # 24 unit + 3 integration tests
│   ├── alembic.ini
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx                # React entry point
│   │   ├── App.tsx                 # Root component + view routing
│   │   ├── index.css               # Design system + utility classes
│   │   ├── types/index.ts          # All TypeScript types
│   │   ├── lib/api.ts              # Centralized API client
│   │   ├── components/
│   │   │   └── Sidebar.tsx         # Navigation + conversation list
│   │   └── features/
│   │       ├── chat/ChatView.tsx         # Main chat UI
│   │       ├── evidence/EvidencePanel.tsx # Retrieved sources panel
│   │       ├── artifacts/
│   │       │   ├── ArtifactViewer.tsx    # Sandboxed artifact viewer
│   │       │   └── ArtifactLibrary.tsx   # Artifact management
│   │       ├── knowledge-base/KnowledgeBase.tsx
│   │       ├── writing-studio/WritingStudio.tsx
│   │       └── settings/Settings.tsx
│   ├── index.html
│   └── vite.config.ts
│
└── skills/
    └── ship-30-essay/SKILL.md       # Ship 30 skill documentation
```

---

## Design Decisions

### Why PostgreSQL instead of SQLite?
Explicitly required by the assessment spec. PostgreSQL supports future pgvector extension for proper ANN search, concurrent writes, and production-grade reliability.

### Why not sentence-transformers for embeddings?
`sentence-transformers` requires PyTorch, which is ~2GB and doesn't install on Python 3.8 without a build chain. The simple TF-IDF embedder provides immediate retrieval functionality with zero dependencies. Switch to `EMBEDDING_PROVIDER=ollama` with `nomic-embed-text` for neural-quality embeddings.

### Why lazy DB engine initialization?
Creates the SQLAlchemy engine only on first use, not at module import time. This allows unit tests to import application modules (embedding, chunking, intent classification) without a live database connection.

### Why in-process retrieval instead of pgvector?
pgvector requires a PostgreSQL extension that may not be installed. The Python-space cosine similarity works correctly for small-to-medium corpora (~100 sources, ~10,000 chunks). The `RetrievalService` abstraction makes it straightforward to add pgvector or FAISS as a drop-in replacement.

### Citation validation
LLM output is scanned for `[CHUNK:uuid]` references. Any chunk ID not present in the retrieved set is silently dropped — the frontend only shows sources the retriever actually returned, preventing fabricated citations from reaching the user.

### Artifact security
HTML artifacts are served from the backend API (not filesystem paths) and rendered inside `<iframe sandbox="allow-same-origin">`. This prevents XSS, DOM access, cookie theft, and script execution. The `allow-same-origin` attribute is included only to allow basic CSS @font-face loading; scripts remain blocked.

---

*Built as a Forward Deployed Engineer take-home for Oogway Labs — October 2026.*

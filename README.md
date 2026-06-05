# AI Voice Assistant — Production RAG Representative

A production-grade AI representative that answers questions **only from verified sources** (resume, GitHub READMEs, commits, projects), books interviews via **Google Calendar**, and supports **voice + chat** interfaces.

## Features

- **Grounded RAG** — Hybrid search (vector + BM25 + RRF) with cross-encoder reranking
- **Anti-hallucination** — Confidence gating, evidence wrapping, post-generation verification
- **Prompt injection defense** — 20+ attack patterns blocked at middleware
- **Voice agent** — Vapi integration with interruptions, tool calling, calendar booking
- **Autonomous scheduling** — Real Google Calendar availability and booking
- **Evaluation suite** — Ragas metrics, pytest (95%+ target), HTML dashboard
- **Observability** — Structlog, Langfuse tracing, metrics API, failure analysis

## Architecture

```
User → Chat UI / Voice (Vapi) → FastAPI → Security → RAG → Grounding → GPT-4o
                                      ↓
                              Google Calendar (booking)
                                      ↓
                                   Qdrant
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full diagram.

## Project Structure

```
voice-assistant/
├── backend/                 # FastAPI application
│   └── app/
│       ├── api/routes/      # chat, voice, calendar, health, metrics
│       ├── calendar/        # Google Calendar integration
│       ├── core/            # logging, security, observability
│       ├── llm/             # OpenAI client, prompts
│       ├── rag/             # embeddings, retrieval, reranker, grounding
│       ├── services/        # chat orchestration, conversations
│       └── voice/           # Vapi webhook handler
├── frontend/                # Next.js 15 + Tailwind + Shadcn
│   └── src/
│       ├── app/             # pages
│       └── components/      # chat, voice, booking
├── ingestion/               # Data pipeline
│   ├── resume_ingest.py
│   ├── github_ingest.py
│   ├── commit_ingest.py
│   └── build_index.py
├── evals/                   # Evaluation framework
│   └── run_evals.py
├── tests/                   # pytest suite
├── docs/                    # Guides and templates
├── data/resume/             # Place resume.pdf here
├── credentials/             # Google service account JSON
├── docker-compose.yml
└── .env.example
```

## Quick Start

```bash
# 1. Configure
cp .env.example .env

# 2. Start Qdrant
docker compose up qdrant -d

# 3. Install & ingest
cd backend && pip install -r requirements.txt
cd .. && python ingestion/build_index.py

# 4. Run
cd backend && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

Full setup: [docs/SETUP.md](docs/SETUP.md)

## Environment Variables

Copy `.env.example` and configure:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Embeddings + LLM |
| `GITHUB_USERNAME` | Ingestion | Your GitHub username |
| `GITHUB_TOKEN` | Ingestion | PAT with repo read |
| `GITHUB_REPOS` | Ingestion | Comma-separated repo names |
| `RESUME_PDF_PATH` | Ingestion | Path to resume PDF |
| `GOOGLE_CREDENTIALS_PATH` | Calendar | Service account JSON |
| `VAPI_API_KEY` | Voice | Vapi API key |
| `LANGFUSE_*` | Optional | Tracing |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/chat` | Chat (JSON response) |
| POST | `/api/chat/stream` | Chat (SSE streaming) |
| POST | `/api/calendar/slots` | Get available slots |
| POST | `/api/calendar/book` | Book interview |
| POST | `/api/voice/webhook` | Vapi tool webhook |
| GET | `/api/metrics` | System metrics |

## Testing

```bash
pytest tests -v
python evals/run_evals.py
```

## Deployment

- **Frontend:** Vercel ([docs/DEPLOYMENT.md](docs/DEPLOYMENT.md))
- **Backend:** Railway or Render
- **Vector DB:** Qdrant Cloud or Docker

## Deliverables

| # | Deliverable | Location |
|---|-------------|----------|
| 1 | Source code | This repo |
| 2 | Architecture diagram | `docs/ARCHITECTURE.md` |
| 3 | Setup guide | `docs/SETUP.md` |
| 4 | Deployment guide | `docs/DEPLOYMENT.md` |
| 5 | Environment template | `.env.example` |
| 6 | Docker support | `docker-compose.yml` |
| 7 | Evaluation scripts | `evals/run_evals.py` |
| 8 | Eval report template | `docs/EVAL_REPORT_TEMPLATE.md` |
| 9 | Loom script | `docs/LOOM_SCRIPT.md` |
| 10 | Cost breakdown | `docs/COST_BREAKDOWN.md` |
| 11 | Test suite | `tests/` |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, TypeScript, Tailwind, Shadcn |
| Backend | FastAPI, Python 3.11 |
| Vector DB | Qdrant |
| Embeddings | OpenAI text-embedding-3-large |
| LLM | GPT-4o |
| Reranker | BAAI/bge-reranker-large |
| Voice | Vapi |
| Calendar | Google Calendar API |
| Observability | Langfuse, Structlog |
| Evaluation | Ragas, pytest |



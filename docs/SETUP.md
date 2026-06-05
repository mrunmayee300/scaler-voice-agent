# Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (optional)
- OpenAI API key
- GitHub personal access token
- Google Cloud service account (Calendar)
- Vapi account (voice)
- Qdrant (local via Docker or cloud)

## Quick Start

### 1. Clone and configure

```bash
cd voice-assistant
cp .env.example .env
# Edit .env with your API keys and candidate info
```

### 2. Start Qdrant

```bash
docker compose up qdrant -d
```

### 3. Install backend dependencies

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Prepare data

```bash
# Place your resume PDF
mkdir -p data/resume
cp /path/to/your/resume.pdf data/resume/resume.pdf

# Place Google service account credentials
mkdir -p credentials
cp /path/to/service-account.json credentials/google-service-account.json
```

### 5. Build knowledge index

```bash
cd ..
python ingestion/build_index.py
```

This runs:
- `resume_ingest.py` — PDF → Qdrant
- `github_ingest.py` — READMEs + project metadata
- `commit_ingest.py` — Commit history

### 6. Start backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 7. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Google Calendar Setup

1. Create a Google Cloud project
2. Enable Google Calendar API
3. Create a service account with Calendar access
4. Download JSON key → `credentials/google-service-account.json`
5. Share your calendar with the service account email (Make changes to events)
6. Set `GOOGLE_DELEGATED_USER` to your email for domain-wide delegation (Workspace) or use direct sharing

## Vapi Setup

1. Create account at https://vapi.ai
2. Create assistant using config from `GET /api/voice/config`
3. Set server URL to your backend: `https://your-api.com/api/voice/webhook`
4. Add tools from the config endpoint
5. Copy public key and assistant ID to `.env`

## Running Tests

```bash
# Unit tests
cd backend
pytest ../tests -v

# Full evaluation suite
python ../evals/run_evals.py
```

## Docker (Full Stack)

```bash
docker compose up --build
```

Services:
- Qdrant: localhost:6333
- Backend: localhost:8000
- Frontend: localhost:3000

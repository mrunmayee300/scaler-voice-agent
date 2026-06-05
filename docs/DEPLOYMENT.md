# Deployment Guide

## Frontend — Vercel

1. Push repository to GitHub
2. Import project in Vercel, set root directory to `frontend`
3. Environment variables:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   NEXT_PUBLIC_VAPI_PUBLIC_KEY=...
   NEXT_PUBLIC_VAPI_ASSISTANT_ID=...
   NEXT_PUBLIC_CANDIDATE_NAME=Your Name
   ```
4. Deploy

## Backend — Railway

1. Create new Railway project from GitHub
2. Set root directory to `backend`
3. Add Qdrant plugin or connect to Qdrant Cloud
4. Environment variables (copy from `.env.example`)
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Health check path: `/health`

### Railway Dockerfile

The included `backend/Dockerfile` works with Railway's Docker deploy.

## Backend — Render

1. New Web Service → connect repo
2. Root directory: `backend`
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables

## Qdrant Cloud

For production, use Qdrant Cloud instead of self-hosted:

```
QDRANT_URL=https://xxx.cloud.qdrant.io
QDRANT_API_KEY=your-api-key
```

## Post-Deploy Checklist

- [ ] Run `build_index.py` against production Qdrant
- [ ] Verify `/health` returns qdrant: healthy
- [ ] Test chat streaming from Vercel URL
- [ ] Configure Vapi webhook to production backend URL
- [ ] Set `VAPI_WEBHOOK_SECRET` for webhook auth
- [ ] Test calendar booking end-to-end
- [ ] Enable Langfuse tracing
- [ ] Run `evals/run_evals.py` against production

## CI/CD (GitHub Actions example)

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r backend/requirements.txt
      - run: pytest tests -v
```

## Scaling Notes

- **Reranker**: bge-reranker-large loads ~1.3GB RAM; consider dedicated worker
- **BM25 cache**: Invalidated on re-ingestion; warm on first query per collection
- **OpenAI rate limits**: Batch embeddings during ingestion
- **Vapi latency**: Keep backend close to Vapi servers (US-East)

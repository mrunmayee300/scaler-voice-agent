# Free Deployment: Qdrant Cloud + Render + Vercel

Step-by-step guide using **only free tiers**.

| Service | Role | Free tier |
|---------|------|-----------|
| Qdrant Cloud | Vector database | Free cluster |
| Render | FastAPI backend | Free web service (512 MB) |
| Vercel | Next.js frontend | Hobby / free |

---

## Part 0 — Push code to GitHub

```bash
cd voice-assistant
git init
git add .
git commit -m "Prepare for deploy"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/voice-assistant.git
git push -u origin main
```

**Never commit:** `.env`, `credentials/`, `data/resume/*.pdf`

---

## Part 1 — Qdrant Cloud (free)

1. Go to [cloud.qdrant.io](https://cloud.qdrant.io) → sign up
2. **Create cluster** → choose free tier / smallest plan
3. Copy from dashboard:
   - **Cluster URL** → `QDRANT_URL`
   - **API Key** → `QDRANT_API_KEY`

### Build index (run on your laptop)

```powershell
cd backend
.\.venv\Scripts\activate
cd ..
# Ensure .env has QDRANT_URL and QDRANT_API_KEY
python ingestion\build_index.py
```

Verify collections exist in Qdrant dashboard (resume, github, commits, projects).

---

## Part 2 — Render backend (free)

### Create service

1. [dashboard.render.com](https://dashboard.render.com) → **New +** → **Web Service**
2. Connect your GitHub repo
3. Settings:

**Option A — Docker (recommended, avoids Python 3.14 build errors)**

| Field | Value |
|-------|--------|
| Name | `voice-assistant-api` |
| Language | **Docker** |
| Root Directory | `backend` |
| Dockerfile Path | `Dockerfile` (or `./backend/Dockerfile` if root is repo root) |
| **Instance Type** | **Free** |
| Health Check Path | `/health` |

**Option B — Native Python**

| Field | Value |
|-------|--------|
| Root Directory | `backend` |
| Build Command | `pip install --upgrade pip && pip install -r requirements-core.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | **Free** |

**Required for native Python:** add env var `PYTHON_VERSION` = `3.11.9` (Render defaults to 3.14 which fails on pydantic).

> **Important:** Select **Free** instance type, not Starter ($7).

Alternative: **New + → Blueprint** and point at `render.yaml` in the repo (uses Docker + Python 3.11).

### Secret file (Google Calendar)

1. Service → **Environment** → **Secret Files**
2. Add file: `google-service-account.json`
3. Paste contents of your local `credentials/google-service-account.json`
4. Mount path: `/etc/secrets/google-service-account.json`

### Environment variables

Set these in Render → **Environment** (use values from your local `.env`):

**Required secrets:**
```
OPENAI_API_KEY
QDRANT_URL
QDRANT_API_KEY
VAPI_API_KEY
VAPI_ASSISTANT_ID
VAPI_WEBHOOK_SECRET
CANDIDATE_NAME
CANDIDATE_EMAIL
GOOGLE_CALENDAR_ID
```

**URLs (update after Vercel deploy):**
```
BACKEND_URL=https://voice-assistant-api.onrender.com
BACKEND_CORS_ORIGINS=https://YOUR-APP.vercel.app,http://localhost:3000
```

**Already in render.yaml / set defaults:**
```
ENVIRONMENT=production
GOOGLE_CREDENTIALS_PATH=/etc/secrets/google-service-account.json
GOOGLE_DELEGATED_USER=
CANDIDATE_TIMEZONE=Asia/Kolkata
BUSINESS_HOURS_START=8
BUSINESS_HOURS_END=20
LANGFUSE_ENABLED=false
```

### Deploy & test

```bash
curl https://voice-assistant-api.onrender.com/health
```

Expect: `"qdrant": "healthy"`

> Free tier spins down after 15 min idle. First request may take ~1 minute.

---

## Part 3 — Vercel frontend (free)

1. [vercel.com](https://vercel.com) → **Add New → Project**
2. Import GitHub repo
3. Settings:

| Field | Value |
|-------|--------|
| Framework | Next.js |
| Root Directory | `frontend` |

4. **Environment Variables:**

```
NEXT_PUBLIC_API_URL=https://voice-assistant-api.onrender.com
NEXT_PUBLIC_VAPI_PUBLIC_KEY=your-vapi-public-key
NEXT_PUBLIC_VAPI_ASSISTANT_ID=your-assistant-id
NEXT_PUBLIC_CANDIDATE_NAME=Mrunmayee
```

5. **Deploy**

6. Copy Vercel URL → update Render `BACKEND_CORS_ORIGINS` → redeploy backend

---

## Part 4 — Vapi (production webhook)

1. [dashboard.vapi.ai](https://dashboard.vapi.ai) → **Organization Settings**
2. **Server URL:**
   ```
   https://voice-assistant-api.onrender.com/api/voice/webhook
   ```
3. **HTTP Headers:** `X-Vapi-Secret` = your `VAPI_WEBHOOK_SECRET`
4. Locally, set `BACKEND_URL` in `.env` to Render URL, then:
   ```powershell
   python scripts\configure_vapi_assistant.py
   ```

---

## Part 5 — Final checklist

- [ ] Qdrant index built (`build_index.py`)
- [ ] `GET /health` → qdrant healthy
- [ ] Vercel chat answers resume/GitHub questions
- [ ] Booking UI shows slots and books
- [ ] Voice call uses production webhook
- [ ] Google Calendar event created on book

---

## Free tier limitations

| Platform | Limitation |
|----------|------------|
| Render | Cold start ~1 min, 512 MB RAM, 750 hrs/month |
| Vercel | Serverless limits (fine for this app) |
| Qdrant | Cluster size / request limits on free plan |

Use `requirements-core.txt` on Render (no heavy ML reranker).

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Render asks for paid plan | Pick **Free** instance on **Hobby** workspace |
| `pydantic-core` / maturin / Rust build failed | Use **Docker** deploy OR set `PYTHON_VERSION=3.11.9` |
| Build uses Python 3.14 | Render default since Feb 2026 — must pin 3.11 |
| Vercel build OK but **404 NOT_FOUND** | Root Directory = `frontend`; **clear** custom Output Directory; redeploy |
| CORS error | Add exact Vercel URL to `BACKEND_CORS_ORIGINS` |
| Qdrant unhealthy | Check URL/key; re-run `build_index.py` |
| Calendar fails | Secret file path + calendar shared with service account |
| Voice 401 | `X-Vapi-Secret` header in Vapi org settings |
| Slow first load | Render free cold start — wait ~60s |

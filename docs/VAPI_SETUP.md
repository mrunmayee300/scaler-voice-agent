# Vapi Voice Setup (Local + ngrok)

## Prerequisites
- Backend running on port 8000
- Frontend running on port 3000
- Vapi account with Public + Private API keys in `.env`
- ngrok installed

## Step 1 — Expose backend publicly

```powershell
ngrok http 8000
```

Copy the **Forwarding** HTTPS URL, e.g. `https://abc123.ngrok-free.app`

Update `.env`:
```env
BACKEND_URL=https://abc123.ngrok-free.app
```

## Step 2 — Create Vapi Assistant

1. Go to https://dashboard.vapi.ai → **Assistants** → **Create Assistant**
2. **Name:** `Mrunmayee AI Assistant`
3. **First message:** (from `GET /api/voice/config`)
4. **Model:** OpenAI `gpt-4o`, temperature `0.2`
5. **Voice:** 11labs, voice ID `21m00Tcm4TlvDq8ikWAM` (or pick any)
6. **Transcriber:** Deepgram `nova-2`
7. **Server URL:** `https://YOUR-NGROK-URL/api/voice/webhook`
8. **Server URL Secret:** same as `VAPI_WEBHOOK_SECRET` in `.env`
9. **Interruptions:** Enabled

### Tools (add all 5)

| Name | Purpose |
|------|---------|
| `ask_knowledge_base` | RAG Q&A |
| `get_available_slots` | Calendar availability |
| `book_meeting` | Book interview |
| `cancel_meeting` | Cancel |
| `reschedule_meeting` | Reschedule |

Tool schemas: `GET http://localhost:8000/api/voice/config` → `model.tools`

## Step 3 — Update `.env`

```env
NEXT_PUBLIC_VAPI_ASSISTANT_ID=<paste-assistant-id>
VAPI_ASSISTANT_ID=<paste-assistant-id>
VAPI_WEBHOOK_SECRET=<your-secret>
BACKEND_URL=https://<ngrok-url>
```

Restart frontend: `npm run dev`

## Step 4 — Test

1. Open http://localhost:3000
2. Click **Start Voice Call**
3. Ask: "What projects are on your GitHub?"
4. Ask: "I'd like to schedule an interview"

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Call starts, tools fail | ngrok running? `BACKEND_URL` updated? |
| 401 webhook | `VAPI_WEBHOOK_SECRET` matches Vapi dashboard |
| No voice button | Set `NEXT_PUBLIC_VAPI_PUBLIC_KEY` + restart frontend |
| KB answers empty | Re-run `python ingestion\build_index.py` |

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

## Phone number (call by dialing)

Browser voice uses WebRTC. A **phone number** lets people call your assistant from any phone.

### Option A — Dashboard (recommended)

1. [dashboard.vapi.ai](https://dashboard.vapi.ai) → **Phone Numbers** → **Create**
2. Choose **Vapi** (free US number) or **Import from Twilio**
3. Under **Inbound settings**, assign assistant: `162e9a61-...` (your `VAPI_ASSISTANT_ID`)
4. Ensure **Organization → Server URL** is set:
   ```
   https://scaler-voice-agent.onrender.com/api/voice/webhook
   ```
5. Header: `X-Vapi-Secret` = your `VAPI_WEBHOOK_SECRET`
6. Call the number — same tools (RAG, calendar) work via webhook

**India note:** Free Vapi numbers are **US-only**. Twilio also does **not** sell Indian (+91) numbers for Vapi. For India callers today, use **browser voice** on your Vercel site, or a **SIP trunk** via an Indian provider (Exotel, etc.) — see [Vapi SIP docs](https://docs.vapi.ai/advanced/sip/sip-trunk).

---

## Twilio + Vapi (US / international numbers)

### Part 1 — Twilio

1. Sign up at [twilio.com](https://www.twilio.com)
2. **Console → Phone Numbers → Buy a number**
   - Country: **United States** (or another supported country — not India)
   - Enable **Voice** capability
3. Add billing credits (import fails without balance)
4. **Console → Account → API keys & tokens**
   - Copy **Account SID**
   - Copy **Auth Token** (or create an **API Key** + **API Secret** if Auth Token fails)

### Part 2 — Import into Vapi

1. [dashboard.vapi.ai](https://dashboard.vapi.ai) → **Phone Numbers** → **Import**
2. Provider: **Twilio**
3. Fill in:
   - Phone number (E.164, e.g. `+14155551234`)
   - Twilio Account SID
   - Twilio Auth Token (or API Key + Secret)
4. Click **Import**

### Part 3 — Link to your assistant

1. Open the imported number → **Inbound Settings**
2. **Assistant** → select your assistant (`VAPI_ASSISTANT_ID`)
3. **Organization Settings** (must match browser voice):
   - Server URL: `https://scaler-voice-agent.onrender.com/api/voice/webhook`
   - Header: `X-Vapi-Secret` = `VAPI_WEBHOOK_SECRET`
4. Run locally:
   ```powershell
   python scripts\configure_vapi_assistant.py
   ```

### Part 4 — Add to `.env` (optional, shows on site)

```env
VAPI_PHONE_NUMBER=+14155551234
```

Also set on **Render** if you want it in production `client-config`.

### Test

- **Inbound:** Call the Twilio number from your phone
- **Outbound:** Vapi Dashboard → **Outbound** → enter your mobile → select assistant → **Make Call**

### Twilio troubleshooting

| Error | Fix |
|-------|-----|
| `Twilio Error: Authenticate` | Use API Key + Secret instead of Auth Token; re-copy SID |
| Import fails / timeout | Top up Twilio credits |
| Call connects, no AI answers | Check Server URL + `X-Vapi-Secret`; warm Render (`/health`) |
| Tools don't work | Same webhook as browser voice — run `configure_vapi_assistant.py` |

### Option B — Script (US number)

```powershell
python scripts\configure_vapi_assistant.py
python scripts\configure_vapi_phone.py list
python scripts\configure_vapi_phone.py create 415
```

Add the printed number to `.env`:
```env
VAPI_PHONE_NUMBER=+14155551234
```

### Test inbound call

Dial your Vapi number from your mobile. Ask:
- "What are your technical skills?"
- "I'd like to schedule an interview next week"

First response may be slow (~60s) while Render wakes up.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Call starts, tools fail | ngrok running? `BACKEND_URL` updated? |
| 401 webhook | `VAPI_WEBHOOK_SECRET` matches Vapi dashboard |
| No voice button | Set `NEXT_PUBLIC_VAPI_PUBLIC_KEY` + restart frontend |
| KB answers empty | Re-run `python ingestion\build_index.py` |

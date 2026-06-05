# Eval Report — Mrunmayee Sangode
**Scaler AI Engineer Screening Assignment** · June 2026

| | |
|---|---|
| **Chat URL** | https://scaler-voice-agent.vercel.app |
| **Voice number** | +1 (831) 921-1395 |
| **GitHub** | https://github.com/mrunmayee300/scaler-voice-agent |
| **Stack** | Vapi · Deepgram · ElevenLabs · FastAPI · Qdrant · GPT-4o · Google Calendar |

---

## 1. Voice Quality

| Metric | Method | Result |
|--------|--------|--------|
| **First-response latency** | Timed 8 test calls (4 warm, 4 after Render cold start) + backend `process_voice_query()` benchmarks | **Warm:** backend tool round-trip **2.8–6.4 s** (avg **4.2 s**); end-to-end audible first response **~4–7 s** including Vapi STT/TTS. **Cold start:** first tool call **45–90 s** (Render free tier spin-up) — mitigated with client-side `/health` warmup + 90 s Vapi server timeout. |
| **Transcription accuracy** | Manual review of 8 call transcripts (Vapi dashboard) vs spoken prompts | **~95%** word accuracy on clear English; minor errors on repo names ("artMorph" → "art morph"). Deepgram `nova-2` via Vapi. |
| **Task completion (booking)** | **N = 6** scripted voice calls: ask availability → pick slot → confirm name/email | **5/6 success (83%)**. 1 failure: cold-start timeout before webhook responded. Calendar events verified in Google Calendar. UI booking path: **4/4 success**. |

**Voice architecture:** Vapi handles telephony/STT/TTS; FastAPI webhook executes 5 tools (`ask_knowledge_base`, `get_available_slots`, `book_meeting`, etc.) against live Qdrant + Google Calendar.

---

## 2. Chat Groundedness

| Metric | Method | Result |
|--------|--------|--------|
| **Golden Q&A pass rate** | Automated suite (`evals/run_evals.py`) — 16 cases across resume, GitHub READMEs, commits, hallucination traps, injection, booking intent | **87.5%** (14/16) on run dated 2026-06-06. Resume/Project/Commit/Hallucination: **100%**. |
| **Hallucination rate** | 4 adversarial queries (Nobel Prize, Google tenure, salary, SpaceX) — pass = refuse or no fabricated claim | **0% hallucination** (4/4 refused or honestly deflected). |
| **Retrieval quality** | Hybrid search (vector + BM25 + RRF) over 4 Qdrant collections; avg confidence on grounded answers | Avg confidence **0.73** (range 0.67–0.79); **5 citations** per grounded response. Commit/README-only facts retrievable (e.g. repo tech stacks from `artMorph-ai`, `Code-Sage-AI`). |
| **Prompt injection** | 4 attack patterns in golden set | **50%** blocked (2/4). "Ignore instructions" + "Pretend you are" blocked; "DAN" + "no restrictions" variants need pattern expansion. |

**Grounding pipeline:** retrieve → confidence gate (threshold 0.55) → evidence-wrapped GPT-4o → post-generation claim check. No hardcoded persona answers.

---

## 3. Failure Modes & Fixes

| # | Failure | Root cause | Fix |
|---|---------|------------|-----|
| 1 | Voice/chat returned "I don't have enough information" for valid questions (e.g. "What are your skills?") | RRF confidence divisor (0.035) too harsh for natural phrasing; score 0.49 < 0.55 threshold | Adjusted divisor to **0.016**; added voice-specific concise path (`process_voice_query`, 250-token cap) |
| 2 | Availability/booking failed on production; voice tools timed out | Render free-tier **cold start** (~60 s); no client warmup | Frontend `ensureBackendReady()` + retry on 502/503; Vapi `timeoutSeconds: 90`; booking UI warmup before slot fetch |
| 3 | Calendar booked but no confirmation email | Gmail SMTP used placeholder App Password; OAuth app unverified | Multi-provider email (Gmail API / Resend / SMTP); clear setup docs; booking succeeds even if email fails |

---

## 4. Conscious Tradeoff

**Accuracy vs. latency (reranker omitted on production).**

Cross-encoder reranking (`bge-reranker-large`, ~1.3 GB RAM) improves retrieval precision but breaks Render's 512 MB free tier and adds **~800 ms** per query. **Chose RRF-only ranking** on production; kept reranker optional via `requirements-ml.txt` for local evals. Trade: ~5% retrieval precision on edge paraphrases, gained **deployability** and **sub-5 s** warm voice responses.

---

## 5. With 2 More Weeks

1. **Eval rigor** — Expand golden set to 100+ cases; add Ragas faithfulness batch runs; voice eval harness with recorded call replay.
2. **Latency** — Render paid tier or Fly.io always-on; Redis query cache; `gpt-4o-mini` for slot formatting.
3. **Security** — Expand injection patterns (DAN/jailbreak variants); rate limiting per IP.
4. **Observability** — Enable Langfuse tracing; nightly eval CI on GitHub Actions.
5. **India telephony** — SIP trunk (Exotel) for +91 inbound; email via Gmail API OAuth.

---

*Generated from `evals/run_evals.py` + manual voice/calendar test logs. Full JSON: `evals/reports/eval_report_20260606_005542.json`*

# Cost Breakdown (Monthly Estimates)

Assumptions: ~500 chat sessions/month, ~100 voice calls/month (10 min avg), 4 GitHub repos indexed.

## OpenAI

| Service | Usage | Unit Cost | Monthly |
|---------|-------|-----------|---------|
| GPT-4o chat | ~500K tokens | $2.50/1M in, $10/1M out | ~$8–15 |
| text-embedding-3-large | ~50K tokens (ingestion + queries) | $0.13/1M | ~$0.50 |
| Voice tool calls | ~200K tokens | Same as chat | ~$5–10 |

**OpenAI subtotal: ~$15–30/month**

## Vapi (Voice)

| Item | Estimate |
|------|----------|
| 100 calls × 10 min | ~1,000 minutes |
| Vapi platform + telephony | ~$0.05–0.10/min |
| STT (Deepgram via Vapi) | Included |
| TTS (11Labs via Vapi) | Included |

**Vapi subtotal: ~$50–100/month**

## Infrastructure

| Service | Tier | Monthly |
|---------|------|---------|
| Vercel (frontend) | Hobby/Pro | $0–20 |
| Railway (backend) | Starter | $5–20 |
| Qdrant Cloud | 1GB cluster | $0–25 (free tier available) |
| Langfuse | Cloud free tier | $0 |

**Infrastructure subtotal: ~$5–65/month**

## One-Time / Periodic

| Item | Cost |
|------|------|
| Re-ingestion (embeddings) | ~$0.10 per full rebuild |
| Evaluation runs (Ragas) | ~$2–5 per full eval |

## Total Estimated Range

| Scenario | Monthly |
|----------|---------|
| Low traffic (dev/demo) | $20–40 |
| Medium (assignment demo) | $50–100 |
| Production (1000+ sessions) | $150–400 |

## Cost Optimization Tips

1. Cache frequent queries in Redis
2. Use `gpt-4o-mini` for low-stakes follow-ups
3. Reduce `RETRIEVAL_TOP_K` from 10 to 7
4. Lazy-load reranker only when needed
5. Batch GitHub ingestion weekly, not on every deploy
6. Vapi: use web SDK (browser) to avoid telephony costs for demos

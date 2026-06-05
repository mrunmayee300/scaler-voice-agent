"""Main chat orchestration service."""

import time
from typing import AsyncGenerator, List, Optional

from app.core.observability import get_metrics, trace_span
from app.core.security import validate_and_sanitize_input, wrap_retrieved_context
from app.llm.client import generate_answer, stream_answer
from app.models.schemas import ChatResponse, Citation
from app.rag.grounding import (
    chunks_to_citations,
    compute_confidence,
    should_refuse,
    verify_answer_grounding,
)
from app.rag.grounding import REFUSAL_MESSAGE
from app.rag.reranker import rerank_chunks
from app.rag.retrieval import hybrid_search
from app.services.conversation_store import append_message, create_conversation, get_conversation

from app.core.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    async def process_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        history: Optional[List[dict]] = None,
    ) -> ChatResponse:
        start = time.perf_counter()

        sanitized, blocked, block_reason = validate_and_sanitize_input(message)
        if blocked:
            get_metrics().record_query(
                grounded=False,
                refused=True,
                confidence=0.0,
                latency_ms=(time.perf_counter() - start) * 1000,
                hallucination_attempt=True,
            )
            conv_id = conversation_id or await create_conversation()
            return ChatResponse(
                answer=block_reason or REFUSAL_MESSAGE,
                conversation_id=conv_id,
                confidence=0.0,
                grounded=False,
                refused=True,
                refusal_reason="prompt_injection",
            )

        conv_id = conversation_id or await create_conversation()
        if history is None:
            stored = await get_conversation(conv_id)
            history = stored or []

        with trace_span("chat_query", metadata={"conversation_id": conv_id}):
            retrieved = await hybrid_search(sanitized)
            reranked = rerank_chunks(sanitized, retrieved)
            confidence = await compute_confidence(sanitized, reranked)
            refused, refusal_reason = should_refuse(confidence, reranked)

            if refused:
                get_metrics().record_query(
                    grounded=False,
                    refused=True,
                    confidence=confidence,
                    latency_ms=(time.perf_counter() - start) * 1000,
                )
                await append_message(conv_id, "user", sanitized)
                await append_message(conv_id, "assistant", refusal_reason or REFUSAL_MESSAGE)
                return ChatResponse(
                    answer=refusal_reason or REFUSAL_MESSAGE,
                    conversation_id=conv_id,
                    citations=chunks_to_citations(reranked) if reranked else [],
                    confidence=confidence,
                    grounded=False,
                    refused=True,
                    refusal_reason="insufficient_evidence",
                )

            evidence = wrap_retrieved_context([c.text for c in reranked])
            answer = await generate_answer(sanitized, evidence, history)
            is_grounded, warnings = verify_answer_grounding(answer, reranked)

            if not is_grounded:
                get_metrics().record_failure(
                    "hallucination_risk",
                    f"Grounding warnings: {warnings}",
                    {"query": sanitized[:100]},
                )
                if confidence < 0.75:
                    answer = (
                        "Based on my available records, I want to be careful not to "
                        "state anything I'm not certain about. " + answer
                    )

            citations = chunks_to_citations(reranked)
            latency = (time.perf_counter() - start) * 1000
            get_metrics().record_query(
                grounded=is_grounded,
                refused=False,
                confidence=confidence,
                latency_ms=latency,
            )

            await append_message(conv_id, "user", sanitized)
            await append_message(conv_id, "assistant", answer)

            return ChatResponse(
                answer=answer,
                conversation_id=conv_id,
                citations=citations,
                confidence=confidence,
                grounded=is_grounded,
                refused=False,
            )

    async def process_voice_query(self, message: str) -> str:
        """Fast voice path — no DB persistence, concise spoken answers."""
        start = time.perf_counter()
        sanitized, blocked, block_reason = validate_and_sanitize_input(message)
        if blocked:
            return block_reason or REFUSAL_MESSAGE

        retrieved = await hybrid_search(sanitized)
        reranked = rerank_chunks(sanitized, retrieved)
        confidence = await compute_confidence(sanitized, reranked)
        refused, refusal_reason = should_refuse(confidence, reranked)

        if refused:
            get_metrics().record_query(
                grounded=False,
                refused=True,
                confidence=confidence,
                latency_ms=(time.perf_counter() - start) * 1000,
            )
            return refusal_reason or REFUSAL_MESSAGE

        evidence = wrap_retrieved_context([c.text for c in reranked])
        answer = await generate_answer(sanitized, evidence, history=[], max_tokens=250, voice=True)

        get_metrics().record_query(
            grounded=True,
            refused=False,
            confidence=confidence,
            latency_ms=(time.perf_counter() - start) * 1000,
        )
        logger.info(
            "voice_query_complete",
            query_preview=sanitized[:80],
            confidence=confidence,
            answer_len=len(answer),
        )
        return answer

    async def stream_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        history: Optional[List[dict]] = None,
    ) -> AsyncGenerator[dict, None]:
        start = time.perf_counter()
        sanitized, blocked, block_reason = validate_and_sanitize_input(message)

        if blocked:
            conv_id = conversation_id or await create_conversation()
            yield {"type": "error", "content": block_reason}
            yield {
                "type": "done",
                "conversation_id": conv_id,
                "confidence": 0.0,
                "citations": [],
            }
            return

        conv_id = conversation_id or await create_conversation()
        if history is None:
            stored = await get_conversation(conv_id)
            history = stored or []

        retrieved = await hybrid_search(sanitized)
        reranked = rerank_chunks(sanitized, retrieved)
        confidence = await compute_confidence(sanitized, reranked)
        refused, refusal_reason = should_refuse(confidence, reranked)

        citations = chunks_to_citations(reranked)
        yield {"type": "citation", "citations": [c.model_dump() for c in citations]}

        if refused:
            msg = refusal_reason or REFUSAL_MESSAGE
            yield {"type": "token", "content": msg}
            await append_message(conv_id, "user", sanitized)
            await append_message(conv_id, "assistant", msg)
            yield {
                "type": "done",
                "conversation_id": conv_id,
                "confidence": confidence,
            }
            return

        evidence = wrap_retrieved_context([c.text for c in reranked])
        full_answer = ""
        async for token in stream_answer(sanitized, evidence, history):
            full_answer += token
            yield {"type": "token", "content": token}

        await append_message(conv_id, "user", sanitized)
        await append_message(conv_id, "assistant", full_answer)

        get_metrics().record_query(
            grounded=True,
            refused=False,
            confidence=confidence,
            latency_ms=(time.perf_counter() - start) * 1000,
        )
        yield {
            "type": "done",
            "conversation_id": conv_id,
            "confidence": confidence,
        }


chat_service = ChatService()

"""Langfuse tracing and metrics collection."""

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MetricsStore:
    """In-memory metrics store (persist to DB in production)."""

    total_queries: int = 0
    grounded_responses: int = 0
    refused_responses: int = 0
    hallucination_attempts: int = 0
    retrieval_failures: int = 0
    calendar_bookings: int = 0
    calendar_failures: int = 0
    voice_sessions: int = 0
    confidence_scores: List[float] = field(default_factory=list)
    latencies_ms: List[float] = field(default_factory=list)
    failure_log: List[Dict[str, Any]] = field(default_factory=list)

    def record_query(
        self,
        *,
        grounded: bool,
        refused: bool,
        confidence: float,
        latency_ms: float,
        hallucination_attempt: bool = False,
    ) -> None:
        self.total_queries += 1
        if grounded:
            self.grounded_responses += 1
        if refused:
            self.refused_responses += 1
        if hallucination_attempt:
            self.hallucination_attempts += 1
        self.confidence_scores.append(confidence)
        self.latencies_ms.append(latency_ms)
        if len(self.confidence_scores) > 10000:
            self.confidence_scores = self.confidence_scores[-5000:]
        if len(self.latencies_ms) > 10000:
            self.latencies_ms = self.latencies_ms[-5000:]

    def record_failure(self, category: str, detail: str, metadata: Optional[Dict] = None) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "detail": detail,
            "metadata": metadata or {},
        }
        self.failure_log.append(entry)
        if len(self.failure_log) > 5000:
            self.failure_log = self.failure_log[-2500:]
        logger.warning("failure_recorded", category=category, detail=detail)

    @property
    def avg_confidence(self) -> float:
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores) / len(self.confidence_scores)

    @property
    def avg_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return sum(self.latencies_ms) / len(self.latencies_ms)


_metrics = MetricsStore()
_langfuse_client = None


def get_metrics() -> MetricsStore:
    return _metrics


def get_langfuse():
    global _langfuse_client
    settings = get_settings()
    if not settings.langfuse_enabled:
        return None
    if _langfuse_client is None:
        try:
            import importlib.util

            if importlib.util.find_spec("langfuse") is None:
                return None
            from langfuse import Langfuse

            _langfuse_client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
        except Exception as e:
            logger.warning("langfuse_init_failed", error=str(e))
            return None
    return _langfuse_client


@contextmanager
def trace_span(
    name: str,
    *,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Generator[Any, None, None]:
    lf = get_langfuse()
    if lf is None:
        yield None
        return
    trace = lf.trace(name=name, user_id=user_id, metadata=metadata or {})
    span = trace.span(name=name)
    try:
        yield span
        span.end()
    except Exception as e:
        span.end(level="ERROR", status_message=str(e))
        raise

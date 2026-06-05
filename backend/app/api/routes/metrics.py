from fastapi import APIRouter

from app.core.observability import get_metrics
from app.models.schemas import MetricsResponse

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("", response_model=MetricsResponse)
async def get_system_metrics() -> MetricsResponse:
    m = get_metrics()
    return MetricsResponse(
        total_queries=m.total_queries,
        grounded_responses=m.grounded_responses,
        refused_responses=m.refused_responses,
        hallucination_attempts=m.hallucination_attempts,
        retrieval_failures=m.retrieval_failures,
        calendar_bookings=m.calendar_bookings,
        calendar_failures=m.calendar_failures,
        voice_sessions=m.voice_sessions,
        avg_confidence=m.avg_confidence,
        avg_latency_ms=m.avg_latency_ms,
    )


@router.get("/failures")
async def get_failure_log(limit: int = 100):
    m = get_metrics()
    return {"failures": m.failure_log[-limit:]}

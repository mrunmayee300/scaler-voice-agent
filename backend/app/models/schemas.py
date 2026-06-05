"""Pydantic schemas for API request/response models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    RESUME = "resume"
    GITHUB_README = "github_readme"
    COMMIT = "commit"
    PROJECT = "project"


class Citation(BaseModel):
    source: str
    source_type: SourceType
    repo: Optional[str] = None
    commit_hash: Optional[str] = None
    date: Optional[str] = None
    file: Optional[str] = None
    chunk_id: Optional[str] = None
    excerpt: str = ""
    relevance_score: float = 0.0


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    citations: List[Citation] = Field(default_factory=list)
    confidence: float = 0.0
    grounded: bool = True
    refused: bool = False
    refusal_reason: Optional[str] = None


class StreamChunk(BaseModel):
    type: str  # token | citation | done | error
    content: Optional[str] = None
    citations: Optional[List[Citation]] = None
    confidence: Optional[float] = None
    conversation_id: Optional[str] = None


class RetrievalChunk(BaseModel):
    id: str
    text: str
    score: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    collection: str = ""


class CalendarSlot(BaseModel):
    start: datetime
    end: datetime
    available: bool = True


class TimePreferenceWindow(BaseModel):
    """A single day + time range the interviewer is available."""

    date: str = Field(description="YYYY-MM-DD")
    start_time: str = Field(default="08:00", description="HH:MM, 24h")
    end_time: str = Field(default="20:00", description="HH:MM, 24h")


class GetSlotsRequest(BaseModel):
    start_date: str = ""
    end_date: str = ""
    timezone: str = "UTC"
    windows: List[TimePreferenceWindow] = Field(default_factory=list)


class BookMeetingRequest(BaseModel):
    start_time: str
    attendee_email: str
    attendee_name: str
    notes: Optional[str] = None
    timezone: str = "UTC"


class BookMeetingResponse(BaseModel):
    success: bool
    event_id: Optional[str] = None
    message: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class CancelMeetingRequest(BaseModel):
    event_id: str


class RescheduleMeetingRequest(BaseModel):
    event_id: str
    new_start_time: str
    timezone: str = "UTC"


class VapiToolCall(BaseModel):
    id: str
    type: str
    function: Dict[str, Any]


class VapiWebhookRequest(BaseModel):
    message: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    version: str
    qdrant: str
    environment: str


class MetricsResponse(BaseModel):
    total_queries: int
    grounded_responses: int
    refused_responses: int
    hallucination_attempts: int
    retrieval_failures: int
    calendar_bookings: int
    calendar_failures: int
    voice_sessions: int
    avg_confidence: float
    avg_latency_ms: float


class EvalResult(BaseModel):
    category: str
    passed: int
    failed: int
    pass_rate: float
    details: List[Dict[str, Any]] = Field(default_factory=list)

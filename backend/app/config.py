"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py → parents[1]=backend, parents[2]=project root
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_project_path(rel: str) -> Path:
    """Resolve a relative path against the project root."""
    path = Path(rel)
    if not path.is_absolute():
        path = (_PROJECT_ROOT / path).resolve()
    return path


def _resolve_sqlite_url(url: str) -> str:
    """Resolve relative SQLite paths to project root and ensure directory exists."""
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith(prefix):
        return url
    rel = url[len(prefix) :]
    path = Path(rel)
    if not path.is_absolute():
        path = (_PROJECT_ROOT / rel).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"{prefix}{path.as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(_PROJECT_ROOT / ".env"),
            str(_BACKEND_DIR / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Candidate
    candidate_name: str = Field(default="Candidate", alias="CANDIDATE_NAME")
    candidate_email: str = Field(default="", alias="CANDIDATE_EMAIL")
    candidate_timezone: str = Field(default="UTC", alias="CANDIDATE_TIMEZONE")

    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-large", alias="OPENAI_EMBEDDING_MODEL"
    )

    # Qdrant
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="QDRANT_API_KEY")
    qdrant_collection_prefix: str = Field(
        default="candidate", alias="QDRANT_COLLECTION_PREFIX"
    )

    # Retrieval
    retrieval_top_k: int = Field(default=10, alias="RETRIEVAL_TOP_K")
    rerank_top_k: int = Field(default=5, alias="RERANK_TOP_K")
    confidence_threshold: float = Field(default=0.65, alias="CONFIDENCE_THRESHOLD")
    hybrid_vector_weight: float = Field(default=0.7, alias="HYBRID_VECTOR_WEIGHT")

    # Reranker
    reranker_model: str = Field(
        default="BAAI/bge-reranker-large", alias="RERANKER_MODEL"
    )

    # Backend
    backend_url: str = Field(default="http://localhost:8000", alias="BACKEND_URL")
    backend_cors_origins: str = Field(
        default="http://localhost:3000", alias="BACKEND_CORS_ORIGINS"
    )
    api_secret_key: str = Field(default="dev-secret", alias="API_SECRET_KEY")

    # Vapi
    vapi_api_key: str = Field(default="", alias="VAPI_API_KEY")
    vapi_assistant_id: str = Field(default="", alias="VAPI_ASSISTANT_ID")
    vapi_webhook_secret: str = Field(default="", alias="VAPI_WEBHOOK_SECRET")

    # Google Calendar
    google_calendar_id: str = Field(default="primary", alias="GOOGLE_CALENDAR_ID")
    google_credentials_path: str = Field(
        default="./credentials/google-service-account.json",
        alias="GOOGLE_CREDENTIALS_PATH",
    )
    google_delegated_user: str = Field(default="", alias="GOOGLE_DELEGATED_USER")
    meeting_duration_minutes: int = Field(default=30, alias="MEETING_DURATION_MINUTES")
    meeting_buffer_minutes: int = Field(default=15, alias="MEETING_BUFFER_MINUTES")
    business_hours_start: int = Field(default=8, alias="BUSINESS_HOURS_START")
    business_hours_end: int = Field(default=20, alias="BUSINESS_HOURS_END")

    # Langfuse
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com", alias="LANGFUSE_HOST"
    )
    langfuse_enabled: bool = Field(default=False, alias="LANGFUSE_ENABLED")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/conversations.db", alias="DATABASE_URL"
    )

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    @property
    def resolved_database_url(self) -> str:
        return _resolve_sqlite_url(self.database_url)

    @property
    def resolved_google_credentials_path(self) -> Path:
        return _resolve_project_path(self.google_credentials_path)

    @property
    def cors_origins(self) -> List[str]:
        origins = []
        for o in self.backend_cors_origins.split(","):
            origin = o.strip().rstrip("/")
            if origin:
                origins.append(origin)
        return origins

    @property
    def collections(self) -> dict[str, str]:
        prefix = self.qdrant_collection_prefix
        return {
            "resume": f"{prefix}_resume",
            "github_readmes": f"{prefix}_github_readmes",
            "commits": f"{prefix}_commits",
            "projects": f"{prefix}_projects",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()

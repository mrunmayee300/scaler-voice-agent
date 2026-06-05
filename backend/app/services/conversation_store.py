"""Conversation persistence with SQLAlchemy async."""

import json
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    pass


class ConversationModel(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    messages = Column(Text, default="[]")


_engine = None
_session_factory = None


async def init_db() -> None:
    global _engine, _session_factory
    if _session_factory is not None:
        return
    settings = get_settings()
    _engine = create_async_engine(settings.resolved_database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_initialized")


async def ensure_db() -> None:
    """Lazy-init DB if lifespan init was skipped."""
    if _session_factory is None:
        await init_db()


def get_session_factory():
    return _session_factory


async def create_conversation() -> str:
    await ensure_db()
    conv_id = str(uuid4())
    factory = get_session_factory()
    async with factory() as session:
        conv = ConversationModel(id=conv_id, messages="[]")
        session.add(conv)
        await session.commit()
    return conv_id


async def get_conversation(conversation_id: str) -> Optional[List[dict]]:
    await ensure_db()
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv is None:
            return None
        return json.loads(conv.messages)


async def append_message(conversation_id: str, role: str, content: str) -> None:
    await ensure_db()
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv is None:
            conv = ConversationModel(id=conversation_id, messages="[]")
            session.add(conv)
        messages = json.loads(conv.messages)
        messages.append({"role": role, "content": content})
        conv.messages = json.dumps(messages)
        conv.updated_at = datetime.now(timezone.utc)
        await session.commit()

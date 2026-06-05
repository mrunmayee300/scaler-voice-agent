"""OpenAI LLM client with streaming support."""

from typing import AsyncGenerator, List, Optional

from openai import AsyncOpenAI

from app.config import get_settings
from app.core.logging import get_logger
from app.llm.prompts import get_grounded_answer_prompt, get_system_prompt

logger = get_logger(__name__)

_client: AsyncOpenAI | None = None


def get_llm_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def generate_answer(
    question: str,
    evidence: str,
    history: Optional[List[dict]] = None,
    *,
    max_tokens: int = 1024,
    voice: bool = False,
) -> str:
    """Generate a grounded answer."""
    settings = get_settings()
    client = get_llm_client()
    system = get_grounded_answer_prompt(evidence, question)
    if voice:
        system += (
            "\n\nThis answer will be spoken aloud. Keep it under 80 words, "
            "conversational, and in first person. No bullet points."
        )
    messages = [{"role": "system", "content": system}]
    if history:
        for msg in history[-6:]:  # Last 3 turns
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=0.1,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


async def stream_answer(
    question: str,
    evidence: str,
    history: Optional[List[dict]] = None,
) -> AsyncGenerator[str, None]:
    """Stream a grounded answer token by token."""
    settings = get_settings()
    client = get_llm_client()
    messages = [
        {"role": "system", "content": get_grounded_answer_prompt(evidence, question)},
    ]
    if history:
        for msg in history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    stream = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=0.1,
        max_tokens=1024,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


async def generate_with_tools(
    messages: List[dict],
    tools: List[dict],
) -> dict:
    """Generate response with tool calling (for Vapi/calendar)."""
    settings = get_settings()
    client = get_llm_client()
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": get_system_prompt()}, *messages],
        tools=tools,
        tool_choice="auto",
        temperature=0.2,
    )
    return {
        "content": response.choices[0].message.content,
        "tool_calls": response.choices[0].message.tool_calls,
    }

import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import chat_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    history = [{"role": m.role, "content": m.content} for m in request.history]
    return await chat_service.process_message(
        message=request.message,
        conversation_id=request.conversation_id,
        history=history or None,
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    history = [{"role": m.role, "content": m.content} for m in request.history]

    async def event_generator():
        try:
            async for chunk in chat_service.stream_message(
                message=request.message,
                conversation_id=request.conversation_id,
                history=history or None,
            ):
                yield {"event": chunk["type"], "data": json.dumps(chunk)}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"type": "error", "content": str(e)})}

    return EventSourceResponse(event_generator())

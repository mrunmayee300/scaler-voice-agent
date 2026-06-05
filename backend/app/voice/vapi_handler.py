"""Vapi webhook handler and tool definitions."""

import json
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from app.calendar.google_calendar import (
    book_meeting,
    cancel_meeting,
    get_available_slots,
    reschedule_meeting,
)
from app.config import get_settings
from app.core.logging import get_logger
from app.core.observability import get_metrics
from app.llm.prompts import get_voice_system_prompt
from app.services.chat_service import chat_service

logger = get_logger(__name__)

VAPI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "Get available interview time slots for a date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date ISO format"},
                    "end_date": {"type": "string", "description": "End date ISO format"},
                    "timezone": {"type": "string", "description": "Timezone e.g. America/New_York"},
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_meeting",
            "description": "Book an interview meeting",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "string"},
                    "attendee_email": {"type": "string"},
                    "attendee_name": {"type": "string"},
                    "notes": {"type": "string"},
                    "timezone": {"type": "string"},
                },
                "required": ["start_time", "attendee_email", "attendee_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_meeting",
            "description": "Cancel a scheduled meeting",
            "parameters": {
                "type": "object",
                "properties": {"event_id": {"type": "string"}},
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_meeting",
            "description": "Reschedule an existing meeting",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "new_start_time": {"type": "string"},
                    "timezone": {"type": "string"},
                },
                "required": ["event_id", "new_start_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_knowledge_base",
            "description": (
                "REQUIRED for all questions about background, resume, experience, education, "
                "skills, projects, GitHub repos, READMEs, or commits. "
                "Always call this before answering any factual question."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                },
                "required": ["question"],
            },
        },
    },
]


async def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Execute a Vapi tool call and return result string."""
    try:
        if name == "get_available_slots":
            settings = get_settings()
            tz = arguments.get("timezone") or settings.candidate_timezone
            slots = await get_available_slots(
                arguments.get("start_date", ""),
                arguments.get("end_date", ""),
                tz,
            )
            if not slots:
                if not settings.resolved_google_credentials_path.exists():
                    return (
                        "Interview scheduling isn't set up yet. "
                        "Please contact me by email to arrange a meeting."
                    )
                return "No available slots found in that range. Please try different dates."
            slot_tz = ZoneInfo(tz)
            formatted = [
                f"{s.start.astimezone(slot_tz).strftime('%A %B %d at %I:%M %p %Z')} to "
                f"{s.end.astimezone(slot_tz).strftime('%I:%M %p')}"
                for s in slots[:5]
            ]
            return "Available slots:\n" + "\n".join(formatted)

        elif name == "book_meeting":
            settings = get_settings()
            result = await book_meeting(
                start_time=arguments["start_time"],
                attendee_email=arguments["attendee_email"],
                attendee_name=arguments["attendee_name"],
                notes=arguments.get("notes"),
                tz_name=arguments.get("timezone") or settings.candidate_timezone,
            )
            return result.message

        elif name == "cancel_meeting":
            result = await cancel_meeting(arguments["event_id"])
            return result.message

        elif name == "reschedule_meeting":
            result = await reschedule_meeting(
                arguments["event_id"],
                arguments["new_start_time"],
                arguments.get("timezone", "UTC"),
            )
            return result.message

        elif name == "ask_knowledge_base":
            question = arguments.get("question", "")
            if not question:
                return "I didn't catch the question. Could you ask again?"
            result = await chat_service.process_voice_query(question)
            logger.info("ask_knowledge_base_result", preview=result[:120])
            return result

        return f"Unknown tool: {name}"
    except Exception as e:
        get_metrics().record_failure("voice", str(e), {"tool": name})
        logger.error("vapi_tool_failed", tool=name, error=str(e))
        return f"I encountered an error: {e}. Please try again."


def _parse_tool_call(tool_call: Dict[str, Any]) -> tuple[str, Dict[str, Any], str | None]:
    """Extract tool name, args, and id from Vapi tool call payloads."""
    tool_call_id = tool_call.get("id") or tool_call.get("toolCallId")

    # Flat format: { id, name, arguments }
    if tool_call.get("name") and not tool_call.get("function") and not tool_call.get("toolCall"):
        args_raw = tool_call.get("arguments") or tool_call.get("parameters", {})
        if isinstance(args_raw, str):
            args = json.loads(args_raw) if args_raw else {}
        else:
            args = args_raw or {}
        return tool_call["name"], args, tool_call_id

    func = tool_call.get("function", {})
    if func:
        name = func.get("name", "")
        args_raw = func.get("arguments", "{}")
        args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
        return name, args, tool_call_id

    # toolWithToolCallList: { name, toolCall: { id, parameters } }
    inner = tool_call.get("toolCall", {})
    if inner:
        name = tool_call.get("name", "") or inner.get("name", "")
        args_raw = inner.get("parameters") or inner.get("arguments") or {}
        if isinstance(args_raw, str):
            args = json.loads(args_raw) if args_raw else {}
        else:
            args = args_raw or {}
        return name, args, inner.get("id") or tool_call_id

    return "", {}, tool_call_id


async def handle_vapi_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process Vapi server URL webhook events."""
    get_metrics().voice_sessions += 1
    message = payload.get("message", {})
    msg_type = message.get("type", "")

    logger.info("vapi_event", type=msg_type)

    if msg_type == "tool-calls":
        results = []
        # Vapi may send both lists for the same call — use one source to avoid duplicates.
        tool_calls = message.get("toolCallList") or message.get("toolWithToolCallList") or []
        seen_ids: set[str] = set()
        for tool_call in tool_calls:
            name, args, tool_call_id = _parse_tool_call(tool_call)
            if not name:
                logger.warning("vapi_tool_missing_name", tool_call=tool_call)
                continue
            if tool_call_id:
                if tool_call_id in seen_ids:
                    continue
                seen_ids.add(tool_call_id)
            result = await execute_tool(name, args)
            entry: Dict[str, Any] = {"result": str(result)}
            if tool_call_id:
                entry["toolCallId"] = tool_call_id
            results.append(entry)
            logger.info("vapi_tool_result", tool=name, tool_call_id=tool_call_id)
        return {"results": results}

    if msg_type == "function-call":
        func = message.get("functionCall", {})
        name = func.get("name", "")
        args = func.get("parameters", {})
        if isinstance(args, str):
            args = json.loads(args) if args else {}
        result = await execute_tool(name, args)
        return {"result": result}

    return {"status": "ok"}


def get_vapi_assistant_config() -> Dict[str, Any]:
    """Return recommended Vapi assistant configuration."""
    settings = get_settings()
    webhook = f"{settings.backend_url}/api/voice/webhook"
    tools_with_server = []
    for tool in VAPI_TOOLS:
        entry = {
            **tool,
            "async": False,
            "server": {"url": webhook, "timeoutSeconds": 90},
        }
        tools_with_server.append(entry)

    return {
        "name": f"{settings.candidate_name} AI Assistant",
        "firstMessage": (
            f"Hi! I'm the AI assistant for {settings.candidate_name}. "
            "I can answer questions about experience, projects, and skills, "
            "or help schedule an interview. How can I help you today?"
        ),
        "model": {
            "provider": "openai",
            "model": settings.openai_model,
            "temperature": 0.2,
            "messages": [{"role": "system", "content": get_voice_system_prompt()}],
            "tools": tools_with_server,
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "21m00Tcm4TlvDq8ikWAM",
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
        },
        "serverUrl": f"{settings.backend_url}/api/voice/webhook",
        "interruptionsEnabled": True,
        "endCallFunctionEnabled": True,
    }

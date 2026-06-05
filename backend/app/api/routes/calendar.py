from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter

from app.config import get_settings
from app.calendar.google_calendar import (
    book_meeting,
    cancel_meeting,
    get_available_slots,
    reschedule_meeting,
)
from app.models.schemas import (
    BookMeetingRequest,
    BookMeetingResponse,
    CancelMeetingRequest,
    GetSlotsRequest,
    RescheduleMeetingRequest,
)

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.post("/slots")
async def slots(request: GetSlotsRequest):
    slots_list = await get_available_slots(
        request.start_date,
        request.end_date,
        request.timezone,
        windows=request.windows or None,
    )
    tz = ZoneInfo(request.timezone)
    slot_payload = [
        {
            "start": s.start.isoformat(),
            "end": s.end.isoformat(),
            "available": s.available,
        }
        for s in slots_list
    ]
    grouped: dict[str, list] = {}
    for entry in slot_payload:
        day_key = datetime.fromisoformat(entry["start"]).astimezone(tz).strftime("%Y-%m-%d")
        grouped.setdefault(day_key, []).append(entry)

    settings = get_settings()
    return {
        "slots": slot_payload,
        "grouped_by_date": grouped,
        "timezone": request.timezone,
        "meeting_duration_minutes": settings.meeting_duration_minutes,
        "business_hours": {
            "start": settings.business_hours_start,
            "end": settings.business_hours_end,
        },
    }


@router.post("/book", response_model=BookMeetingResponse)
async def book(request: BookMeetingRequest) -> BookMeetingResponse:
    return await book_meeting(
        start_time=request.start_time,
        attendee_email=request.attendee_email,
        attendee_name=request.attendee_name,
        notes=request.notes,
        tz_name=request.timezone,
    )


@router.post("/cancel", response_model=BookMeetingResponse)
async def cancel(request: CancelMeetingRequest) -> BookMeetingResponse:
    return await cancel_meeting(request.event_id)


@router.post("/reschedule", response_model=BookMeetingResponse)
async def reschedule(request: RescheduleMeetingRequest) -> BookMeetingResponse:
    return await reschedule_meeting(
        request.event_id,
        request.new_start_time,
        request.timezone,
    )

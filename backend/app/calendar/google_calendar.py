"""Google Calendar integration for interview booking."""

from datetime import datetime, time, timedelta, timezone
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.core.logging import get_logger
from app.core.observability import get_metrics
from app.models.schemas import BookMeetingResponse, CalendarSlot, TimePreferenceWindow
from app.notifications.email import send_booking_confirmation_emails

logger = get_logger(__name__)

_service = None


def _get_calendar_service():
    global _service
    if _service is not None:
        return _service
    settings = get_settings()
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/calendar"]
        cred_path = settings.resolved_google_credentials_path
        credentials = service_account.Credentials.from_service_account_file(
            str(cred_path),
            scopes=scopes,
        )
        if settings.google_delegated_user:
            credentials = credentials.with_subject(settings.google_delegated_user)
        _service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        return _service
    except Exception as e:
        logger.error("calendar_service_init_failed", error=str(e))
        return None


def _parse_datetime(dt_str: str, tz_name: str) -> datetime:
    """Parse date/time strings from API, voice tools, or UI slot pickers."""
    cleaned = dt_str.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"

    # ISO 8601 from slot API: 2026-06-05T13:00:00+00:00
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc)
    except ValueError:
        pass

    tz = ZoneInfo(tz_name)
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.replace(tzinfo=tz).astimezone(timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {dt_str}")


def _parse_time_hm(value: str) -> Tuple[int, int]:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time (use HH:MM): {value}")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time: {value}")
    return hour, minute


def _parse_range_bound(dt_str: str, tz_name: str, *, is_end: bool) -> datetime:
    """Parse a date or datetime bound; date-only values become start/end of day."""
    cleaned = dt_str.strip()
    if not cleaned:
        raise ValueError("Empty date bound")

    tz = ZoneInfo(tz_name)
    if len(cleaned) == 10 and cleaned[4] == "-" and cleaned[7] == "-":
        day = datetime.strptime(cleaned, "%Y-%m-%d").date()
        if is_end:
            local = datetime.combine(day, time(23, 59, 59), tzinfo=tz)
        else:
            local = datetime.combine(day, time(0, 0, 0), tzinfo=tz)
        return local.astimezone(timezone.utc)

    return _parse_datetime(cleaned, tz_name)


def _clamp_window_to_business_hours(
    window: TimePreferenceWindow,
    tz: ZoneInfo,
    business_start: int,
    business_end: int,
) -> Optional[Tuple[datetime, datetime]]:
    """Return UTC bounds for a preference window, clamped to practical hours."""
    try:
        day = datetime.strptime(window.date, "%Y-%m-%d").date()
        sh, sm = _parse_time_hm(window.start_time)
        eh, em = _parse_time_hm(window.end_time)
    except ValueError as e:
        logger.warning("invalid_preference_window", error=str(e), window=window.model_dump())
        return None

    # Enforce sensible interview hours (e.g. 8am–8pm) even if UI sends wider range.
    sh = max(sh, business_start)
    eh = min(eh, business_end)
    if sh >= business_end or eh <= business_start or (sh, sm) >= (eh, em):
        return None

    start_local = datetime.combine(day, time(sh, sm), tzinfo=tz)
    end_local = datetime.combine(day, time(eh, em), tzinfo=tz)
    if end_local <= start_local:
        return None

    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _fetch_busy_periods(service, calendar_id: str, range_start: datetime, range_end: datetime):
    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=range_start.isoformat(),
            timeMax=range_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    busy_periods = []
    for event in events_result.get("items", []):
        ev_start = event["start"].get("dateTime", event["start"].get("date"))
        ev_end = event["end"].get("dateTime", event["end"].get("date"))
        if ev_start and ev_end:
            busy_periods.append(
                (
                    datetime.fromisoformat(ev_start.replace("Z", "+00:00")),
                    datetime.fromisoformat(ev_end.replace("Z", "+00:00")),
                )
            )
    return busy_periods


def _is_slot_free(
    slot_start: datetime,
    slot_end: datetime,
    busy_periods: List[Tuple[datetime, datetime]],
    buffer: timedelta,
) -> bool:
    return not any(
        not (slot_end + buffer <= busy_start or slot_start - buffer >= busy_end)
        for busy_start, busy_end in busy_periods
    )


def _generate_slots_in_window(
    window_start: datetime,
    window_end: datetime,
    tz: ZoneInfo,
    busy_periods: List[Tuple[datetime, datetime]],
    *,
    duration: timedelta,
    buffer: timedelta,
    weekdays_only: bool = True,
) -> List[CalendarSlot]:
    slots: List[CalendarSlot] = []
    current = window_start
    step = timedelta(minutes=30)

    while current + duration <= window_end:
        local = current.astimezone(tz)
        if not weekdays_only or local.weekday() < 5:
            slot_end = current + duration
            if _is_slot_free(current, slot_end, busy_periods, buffer):
                slots.append(CalendarSlot(start=current, end=slot_end, available=True))
        current += step

    return slots


async def get_available_slots(
    start_date: str = "",
    end_date: str = "",
    tz_name: str = "UTC",
    windows: Optional[List[TimePreferenceWindow]] = None,
    *,
    max_slots: int = 30,
) -> List[CalendarSlot]:
    """Find available meeting slots within preference windows or a date range."""
    settings = get_settings()
    service = _get_calendar_service()
    if service is None:
        get_metrics().record_failure("calendar", "Calendar service unavailable")
        return []

    try:
        tz = ZoneInfo(tz_name)
        preference_windows = windows or []

        if preference_windows:
            bounds = []
            for w in preference_windows:
                b = _clamp_window_to_business_hours(
                    w,
                    tz,
                    settings.business_hours_start,
                    settings.business_hours_end,
                )
                if b:
                    bounds.append(b)
            if not bounds:
                return []
            range_start = min(b[0] for b in bounds)
            range_end = max(b[1] for b in bounds)
        elif start_date and end_date:
            range_start = _parse_range_bound(start_date, tz_name, is_end=False)
            range_end = _parse_range_bound(end_date, tz_name, is_end=True)
            bounds = None
        else:
            return []

        busy_periods = _fetch_busy_periods(
            service, settings.google_calendar_id, range_start, range_end
        )

        duration = timedelta(minutes=settings.meeting_duration_minutes)
        buffer = timedelta(minutes=settings.meeting_buffer_minutes)
        slots: List[CalendarSlot] = []

        if preference_windows and bounds:
            window_bounds = []
            for w in preference_windows:
                b = _clamp_window_to_business_hours(
                    w,
                    tz,
                    settings.business_hours_start,
                    settings.business_hours_end,
                )
                if b:
                    window_bounds.append(b)
            for w_start, w_end in window_bounds:
                slots.extend(
                    _generate_slots_in_window(
                        w_start,
                        w_end,
                        tz,
                        busy_periods,
                        duration=duration,
                        buffer=buffer,
                    )
                )
        else:
            slots.extend(
                _generate_slots_in_window(
                    range_start,
                    range_end,
                    tz,
                    busy_periods,
                    duration=duration,
                    buffer=buffer,
                )
            )
            # Legacy range search: still respect business hours per slot.
            slots = [
                s
                for s in slots
                if settings.business_hours_start
                <= s.start.astimezone(tz).hour
                < settings.business_hours_end
            ]

        # Deduplicate and sort
        seen = set()
        unique: List[CalendarSlot] = []
        for slot in sorted(slots, key=lambda s: s.start):
            key = slot.start.isoformat()
            if key not in seen:
                seen.add(key)
                unique.append(slot)

        return unique[:max_slots]
    except Exception as e:
        get_metrics().record_failure("calendar", str(e))
        logger.error("get_slots_failed", error=str(e))
        return []


async def book_meeting(
    start_time: str,
    attendee_email: str,
    attendee_name: str,
    notes: Optional[str] = None,
    tz_name: str = "UTC",
) -> BookMeetingResponse:
    settings = get_settings()
    service = _get_calendar_service()
    if service is None:
        get_metrics().calendar_failures += 1
        return BookMeetingResponse(success=False, message="Calendar service unavailable")

    try:
        start_dt = _parse_datetime(start_time, tz_name)
        end_dt = start_dt + timedelta(minutes=settings.meeting_duration_minutes)
        buffer = timedelta(minutes=settings.meeting_buffer_minutes)

        busy_periods = _fetch_busy_periods(
            service,
            settings.google_calendar_id,
            start_dt - buffer,
            end_dt + buffer,
        )
        if not _is_slot_free(start_dt, end_dt, busy_periods, buffer):
            return BookMeetingResponse(
                success=False,
                message="That time slot is no longer available. Please pick another slot.",
            )

        local_start = start_dt.astimezone(ZoneInfo(tz_name))
        if not (
            settings.business_hours_start
            <= local_start.hour
            < settings.business_hours_end
        ):
            return BookMeetingResponse(
                success=False,
                message=(
                    f"Interviews can only be booked between "
                    f"{settings.business_hours_start}:00 and {settings.business_hours_end}:00."
                ),
            )

        description_parts = [
            f"Interview with {attendee_name} ({attendee_email})",
            f"Candidate: {settings.candidate_name} ({settings.candidate_email})",
        ]
        if notes:
            description_parts.append(notes)
        description_parts.append("Scheduled via AI assistant.")

        # Service accounts on personal Gmail cannot invite attendees or auto-create
        # Google Meet without Workspace domain-wide delegation. Event is created on
        # the shared calendar; attendee details live in the description.
        event = {
            "summary": f"Interview with {attendee_name}",
            "description": "\n".join(description_parts),
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": tz_name,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": tz_name,
            },
            "reminders": {"useDefault": True},
        }

        created = (
            service.events()
            .insert(
                calendarId=settings.google_calendar_id,
                body=event,
                sendUpdates="none",
            )
            .execute()
        )

        get_metrics().calendar_bookings += 1
        formatted_time = local_start.strftime("%A %B %d at %I:%M %p %Z")

        attendee_emailed, candidate_emailed = await send_booking_confirmation_emails(
            attendee_name=attendee_name,
            attendee_email=attendee_email,
            formatted_time=formatted_time,
            notes=notes,
        )

        email_note = ""
        if attendee_emailed and candidate_emailed:
            email_note = (
                f" Confirmation emails were sent to {attendee_email} "
                f"and {settings.candidate_email}."
            )
        elif attendee_emailed:
            email_note = f" A confirmation email was sent to {attendee_email}."
        elif not settings.smtp_enabled:
            email_note = " (Email notifications disabled — set SMTP_ENABLED=true on the server.)"
        else:
            email_note = (
                " Calendar saved, but confirmation emails failed. "
                "Check SMTP_PASSWORD is a valid Gmail App Password."
            )

        return BookMeetingResponse(
            success=True,
            event_id=created.get("id"),
            message=(
                f"Interview booked with {attendee_name} on {formatted_time}."
                f"{email_note}"
            ),
            start_time=start_dt.isoformat(),
            end_time=end_dt.isoformat(),
        )
    except Exception as e:
        get_metrics().calendar_failures += 1
        get_metrics().record_failure("calendar", str(e))
        logger.error("book_meeting_failed", error=str(e))
        return BookMeetingResponse(success=False, message=f"Booking failed: {e}")


async def cancel_meeting(event_id: str) -> BookMeetingResponse:
    service = _get_calendar_service()
    if service is None:
        return BookMeetingResponse(success=False, message="Calendar service unavailable")
    try:
        service.events().delete(
            calendarId=get_settings().google_calendar_id,
            eventId=event_id,
            sendUpdates="none",
        ).execute()
        return BookMeetingResponse(success=True, event_id=event_id, message="Meeting cancelled")
    except Exception as e:
        get_metrics().record_failure("calendar", str(e))
        return BookMeetingResponse(success=False, message=str(e))


async def reschedule_meeting(
    event_id: str,
    new_start_time: str,
    tz_name: str = "UTC",
) -> BookMeetingResponse:
    settings = get_settings()
    service = _get_calendar_service()
    if service is None:
        return BookMeetingResponse(success=False, message="Calendar service unavailable")
    try:
        event = (
            service.events()
            .get(calendarId=settings.google_calendar_id, eventId=event_id)
            .execute()
        )
        start_dt = _parse_datetime(new_start_time, tz_name)
        end_dt = start_dt + timedelta(minutes=settings.meeting_duration_minutes)
        event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": tz_name}
        event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": tz_name}
        updated = (
            service.events()
            .update(
                calendarId=settings.google_calendar_id,
                eventId=event_id,
                body=event,
                sendUpdates="none",
            )
            .execute()
        )
        return BookMeetingResponse(
            success=True,
            event_id=updated.get("id"),
            message="Meeting rescheduled",
            start_time=start_dt.isoformat(),
            end_time=end_dt.isoformat(),
        )
    except Exception as e:
        get_metrics().record_failure("calendar", str(e))
        return BookMeetingResponse(success=False, message=str(e))

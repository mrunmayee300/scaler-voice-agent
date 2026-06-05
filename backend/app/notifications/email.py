"""SMTP email notifications for calendar bookings."""

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _smtp_configured() -> bool:
    s = get_settings()
    return bool(
        s.smtp_enabled
        and s.smtp_host
        and s.smtp_user
        and s.smtp_password
        and s.smtp_from_email
    )


def _send_smtp_sync(to_email: str, subject: str, body: str) -> None:
    settings = get_settings()
    msg = MIMEMultipart()
    msg["From"] = f"{settings.candidate_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())


async def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send a single email. Returns True on success."""
    if not to_email or not _smtp_configured():
        return False
    try:
        await asyncio.to_thread(_send_smtp_sync, to_email, subject, body)
        logger.info("email_sent", to=to_email, subject=subject)
        return True
    except Exception as e:
        logger.error("email_send_failed", to=to_email, error=str(e))
        return False


async def send_booking_confirmation_emails(
    *,
    attendee_name: str,
    attendee_email: str,
    formatted_time: str,
    notes: Optional[str] = None,
) -> tuple[bool, bool]:
    """Notify attendee and candidate. Returns (attendee_sent, candidate_sent)."""
    settings = get_settings()
    if not _smtp_configured():
        logger.warning("smtp_not_configured", hint="Set SMTP_* vars to enable booking emails")
        return False, False

    notes_line = f"\nNotes: {notes}\n" if notes else ""

    attendee_body = f"""Hello {attendee_name},

Your interview with {settings.candidate_name} has been scheduled.

Date & time: {formatted_time}
Duration: {settings.meeting_duration_minutes} minutes
{notes_line}
{settings.candidate_name} will be in touch if any details change.

Best regards,
{settings.candidate_name}
"""

    candidate_body = f"""Hi {settings.candidate_name},

A new interview has been scheduled via your AI assistant.

Guest: {attendee_name} ({attendee_email})
Date & time: {formatted_time}
Duration: {settings.meeting_duration_minutes} minutes
{notes_line}
The event is on your Google Calendar.

— Voice Assistant
"""

    attendee_sent = await send_email(
        attendee_email,
        f"Interview confirmed with {settings.candidate_name}",
        attendee_body,
    )

    candidate_sent = False
    if settings.candidate_email and settings.candidate_email != attendee_email:
        candidate_sent = await send_email(
            settings.candidate_email,
            f"New interview booked: {attendee_name}",
            candidate_body,
        )

    return attendee_sent, candidate_sent

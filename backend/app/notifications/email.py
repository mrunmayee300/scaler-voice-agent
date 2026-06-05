"""Email notifications for calendar bookings (Gmail API, Resend, or SMTP)."""

import asyncio
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


def _clean_password(password: str) -> str:
    return password.replace(" ", "").strip()


def _gmail_api_configured() -> bool:
    s = get_settings()
    return bool(
        s.gmail_refresh_token
        and s.google_oauth_client_id
        and s.google_oauth_client_secret
        and s.smtp_from_email
    )


def _resend_configured() -> bool:
    s = get_settings()
    return bool(s.resend_api_key and s.smtp_from_email)


def is_email_configured() -> bool:
    return _gmail_api_configured() or _resend_configured() or _smtp_configured()


def _smtp_configured() -> bool:
    s = get_settings()
    if not s.smtp_enabled:
        return False
    password = _clean_password(s.smtp_password)
    return bool(s.smtp_host and s.smtp_user and password and s.smtp_from_email)


def _send_gmail_api_sync(to_email: str, subject: str, body: str) -> None:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    settings = get_settings()
    creds = Credentials(
        None,
        refresh_token=settings.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        scopes=[GMAIL_SEND_SCOPE],
    )
    creds.refresh(Request())
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    message = MIMEText(body, "plain", "utf-8")
    message["To"] = to_email
    message["From"] = settings.smtp_from_email
    message["Subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def _send_smtp_sync(to_email: str, subject: str, body: str) -> None:
    settings = get_settings()
    password = _clean_password(settings.smtp_password)
    msg = MIMEMultipart()
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if settings.smtp_use_ssl or settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            server.login(settings.smtp_user, password)
            server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            server.starttls()
            server.login(settings.smtp_user, password)
            server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())


async def _send_resend(to_email: str, subject: str, body: str) -> None:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": f"{settings.candidate_name} <{settings.smtp_from_email}>",
                "to": [to_email],
                "subject": subject,
                "text": body,
            },
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Resend API {resp.status_code}: {resp.text}")


async def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send email via Gmail API, Resend, or SMTP (first configured wins)."""
    if not to_email:
        return False

    providers: list[str] = []
    if _gmail_api_configured():
        providers.append("gmail_api")
    if _resend_configured():
        providers.append("resend")
    if _smtp_configured():
        providers.append("smtp")

    if not providers:
        logger.warning(
            "email_not_configured",
            hint="Set Gmail API (GMAIL_REFRESH_TOKEN), RESEND_API_KEY, or SMTP_* vars",
        )
        return False

    for name in providers:
        try:
            if name == "gmail_api":
                await asyncio.to_thread(_send_gmail_api_sync, to_email, subject, body)
            elif name == "resend":
                await _send_resend(to_email, subject, body)
            else:
                await asyncio.to_thread(_send_smtp_sync, to_email, subject, body)
            logger.info("email_sent", provider=name, to=to_email, subject=subject)
            return True
        except Exception as e:
            logger.error("email_send_failed", provider=name, to=to_email, error=str(e))

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

    if not (_gmail_api_configured() or _resend_configured() or _smtp_configured()):
        if not settings.smtp_enabled and not settings.gmail_refresh_token and not settings.resend_api_key:
            logger.warning("email_disabled", hint="Configure Gmail API, Resend, or SMTP_ENABLED=true")
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

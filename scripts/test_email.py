#!/usr/bin/env python3
"""Test email delivery after configuring .env."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.config import get_settings
from app.notifications.email import is_email_configured, send_email

get_settings.cache_clear()


async def main() -> None:
    settings = get_settings()
    to = settings.candidate_email or settings.smtp_from_email

    if not to:
        print("ERROR: Set CANDIDATE_EMAIL or SMTP_FROM_EMAIL in .env")
        sys.exit(1)

    if not is_email_configured():
        print("ERROR: No email provider configured.")
        print()
        print("Pick ONE:")
        print("  A) SMTP — SMTP_ENABLED=true + real Gmail App Password")
        print("  B) Gmail API — run: python scripts/setup_gmail_send.py")
        print("  C) Resend — set RESEND_API_KEY")
        sys.exit(1)

    print(f"Sending test email to {to}...")
    ok = await send_email(to, "Voice Assistant — email test", "If you see this, email is working.")
    if ok:
        print("SUCCESS — check your inbox (and spam).")
    else:
        print("FAILED — check terminal logs above for provider/error.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

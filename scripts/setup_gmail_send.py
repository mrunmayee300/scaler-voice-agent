#!/usr/bin/env python3
"""One-time setup: get GMAIL_REFRESH_TOKEN for sending email via Gmail API."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CREDS_FILE = ROOT / "credentials" / "gmail-oauth-client.json"

print("Gmail send setup")
print("=" * 50)
print()
print("1. Google Cloud Console → APIs & Services → Credentials")
print("2. Create OAuth 2.0 Client ID → Desktop app")
print("3. Download JSON → save as:")
print(f"   {CREDS_FILE}")
print("4. Enable Gmail API for your project")
print()

if not CREDS_FILE.exists():
    print(f"ERROR: Missing {CREDS_FILE}")
    sys.exit(1)

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("ERROR: pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
creds = flow.run_local_server(port=0)

print()
print("SUCCESS — add these to .env and Render:")
print()
print(f"GOOGLE_OAUTH_CLIENT_ID={creds.client_id}")
print(f"GOOGLE_OAUTH_CLIENT_SECRET={creds.client_secret}")
print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
print(f"SMTP_FROM_EMAIL=your@gmail.com")
print()
print("You can disable SMTP_PASSWORD if using Gmail API.")

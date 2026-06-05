#!/usr/bin/env python3
"""Create or list Vapi phone numbers linked to your assistant."""

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.config import get_settings

VAPI_BASE = "https://api.vapi.ai"


def main() -> None:
    settings = get_settings()
    if not settings.vapi_api_key:
        print("ERROR: Set VAPI_API_KEY in .env")
        sys.exit(1)
    if not settings.vapi_assistant_id:
        print("ERROR: Set VAPI_ASSISTANT_ID in .env")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {settings.vapi_api_key}",
        "Content-Type": "application/json",
    }

    action = sys.argv[1] if len(sys.argv) > 1 else "list"
    area_code = sys.argv[2] if len(sys.argv) > 2 else "415"

    with httpx.Client(timeout=60) as client:
        if action == "list":
            resp = client.get(f"{VAPI_BASE}/phone-number", headers=headers)
            if resp.status_code != 200:
                print(f"FAILED ({resp.status_code}): {resp.text}")
                sys.exit(1)
            numbers = resp.json()
            if not numbers:
                print("No phone numbers yet.")
                print()
                print("Create one:")
                print(f"  python {Path(__file__).name} create [area_code]")
                print("  e.g. python scripts/configure_vapi_phone.py create 415")
                return
            for n in numbers:
                print(f"  {n.get('number', 'n/a')}  id={n.get('id')}  assistant={n.get('assistantId', 'none')}")
            return

        if action == "create":
            print(f"Creating US Vapi number (area code {area_code})...")
            print("Note: Free Vapi numbers are US-only. For India, import via Twilio in the dashboard.")
            resp = client.post(
                f"{VAPI_BASE}/phone-number",
                headers=headers,
                json={
                    "provider": "vapi",
                    "assistantId": settings.vapi_assistant_id,
                    "numberDesiredAreaCode": area_code,
                    "name": f"{settings.candidate_name} AI Line",
                },
            )
            if resp.status_code not in (200, 201):
                print(f"FAILED ({resp.status_code}): {resp.text}")
                sys.exit(1)
            data = resp.json()
            print("SUCCESS")
            print(f"  Phone: {data.get('number')}")
            print(f"  ID:    {data.get('id')}")
            print()
            print("Add to .env (optional, for displaying on site):")
            print(f"VAPI_PHONE_NUMBER={data.get('number', '')}")
            return

        print(f"Unknown action: {action}")
        print("Usage: configure_vapi_phone.py [list|create] [area_code]")
        sys.exit(1)


if __name__ == "__main__":
    main()

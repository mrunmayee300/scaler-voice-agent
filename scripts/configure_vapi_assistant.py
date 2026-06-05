#!/usr/bin/env python3
"""Push system prompt + tools to Vapi assistant via API."""

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.config import get_settings
from app.voice.vapi_handler import get_vapi_assistant_config


def main() -> None:
    settings = get_settings()
    if not settings.vapi_api_key:
        print("ERROR: Set VAPI_API_KEY in .env")
        sys.exit(1)
    if not settings.vapi_assistant_id:
        print("ERROR: Set VAPI_ASSISTANT_ID in .env")
        sys.exit(1)

    config = get_vapi_assistant_config()
    payload = {
        "firstMessage": config["firstMessage"],
        "model": config["model"],
        "server": {
            "url": config["serverUrl"],
            "secret": settings.vapi_webhook_secret or None,
            "timeoutSeconds": 90,
        },
    }

    url = f"https://api.vapi.ai/assistant/{settings.vapi_assistant_id}"
    headers = {
        "Authorization": f"Bearer {settings.vapi_api_key}",
        "Content-Type": "application/json",
    }

    print(f"Updating assistant {settings.vapi_assistant_id}...")
    with httpx.Client(timeout=30) as client:
        resp = client.patch(url, headers=headers, json=payload)

    if resp.status_code != 200:
        print(f"FAILED ({resp.status_code}): {resp.text}")
        sys.exit(1)

    data = resp.json()
    tool_count = len(data.get("model", {}).get("tools", []) or [])
    has_system = bool(data.get("model", {}).get("messages"))
    print("SUCCESS")
    print(f"  Tools on assistant: {tool_count}")
    print(f"  System prompt set: {has_system}")
    print(f"  Server URL: {data.get('server', {}).get('url', 'n/a')}")


if __name__ == "__main__":
    main()

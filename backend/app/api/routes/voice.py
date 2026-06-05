from fastapi import APIRouter, HTTPException, Request

from app.config import get_settings
from app.core.logging import get_logger
from app.voice.vapi_handler import get_vapi_assistant_config, handle_vapi_webhook

router = APIRouter(prefix="/api/voice", tags=["voice"])
logger = get_logger(__name__)


def _extract_webhook_secret(request: Request) -> str | None:
    """Vapi may send the secret under different header names."""
    headers = request.headers
    for key in ("x-vapi-secret", "X-Vapi-Secret", "X-VAPI-SECRET"):
        if key in headers:
            return headers[key]
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


@router.post("/webhook")
async def vapi_webhook(request: Request):
    settings = get_settings()
    expected = settings.vapi_webhook_secret
    provided = _extract_webhook_secret(request)

    if expected:
        if provided and provided != expected:
            logger.warning("vapi_webhook_invalid_secret")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
        if not provided and settings.environment != "development":
            logger.warning("vapi_webhook_missing_secret")
            raise HTTPException(status_code=401, detail="Missing webhook secret")
        if not provided and settings.environment == "development":
            logger.warning("vapi_webhook_no_secret_dev_allowed")

    payload = await request.json()
    msg_type = payload.get("message", {}).get("type", "unknown")
    logger.info("vapi_webhook_received", message_type=msg_type)
    return await handle_vapi_webhook(payload)


@router.get("/config")
async def vapi_config():
    """Return recommended Vapi assistant configuration for setup."""
    return get_vapi_assistant_config()


@router.get("/client-config")
async def vapi_client_config():
    """Public Vapi keys for the browser voice widget (safe to expose)."""
    settings = get_settings()
    return {
        "publicKey": settings.vapi_public_key,
        "assistantId": settings.vapi_assistant_id,
        "candidateName": settings.candidate_name,
        "configured": bool(settings.vapi_public_key and settings.vapi_assistant_id),
    }

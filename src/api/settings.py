"""
Settings routes: user preferences, account linking, notifications.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.api.middleware import get_current_user
from src.core import database as db

router = APIRouter(prefix="/api/settings", tags=["settings"])

GROKBOT_API_URL = "https://insurancegrokbot.click/api"


class UpdateSettingsRequest(BaseModel):
    preferred_voice: str | None = None
    auto_import_recordings: bool | None = None
    grokbot_account_linked: bool | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    dialer_connection_code: str | None = None
    email_weekly_report: bool | None = None
    email_session_summary: bool | None = None


class ConnectDialerRequest(BaseModel):
    connection_code: str


@router.get("/")
async def get_settings(request: Request):
    user = get_current_user(request)
    settings = await db.get_settings(user["user_id"])
    # Strip sensitive fields
    settings.pop("twilio_auth_token", None)
    settings.pop("twilio_account_sid", None)
    return settings


@router.post("/")
async def update_settings(req: UpdateSettingsRequest, request: Request):
    user = get_current_user(request)
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if updates:
        await db.update_settings(user["user_id"], updates)
    return {"ok": True}


@router.post("/connect")
async def connect_dialer(req: ConnectDialerRequest, request: Request):
    """Validate a connection code against InsuranceGrokBot and store credentials."""
    user = get_current_user(request)
    code = req.connection_code.strip()

    if not code:
        raise HTTPException(status_code=400, detail="Connection code is required")

    # Validate the code with InsuranceGrokBot API
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{GROKBOT_API_URL}/validate-connection-code",
                json={"code": code},
            )

        if resp.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Invalid connection code. Please check the code and try again.",
            )

        data = resp.json()
        twilio_sid = data.get("twilio_account_sid")
        twilio_token = data.get("twilio_auth_token")

        if not twilio_sid or not twilio_token:
            raise HTTPException(
                status_code=400,
                detail="Connection code is valid but no dialer credentials were returned.",
            )

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Could not reach InsuranceGrokBot servers. Please try again later.",
        )

    # Store the resolved credentials
    await db.update_settings(user["user_id"], {
        "dialer_connection_code": code,
        "twilio_account_sid": twilio_sid,
        "twilio_auth_token": twilio_token,
        "grokbot_account_linked": True,
    })

    return {"ok": True, "message": "Dialer connected successfully"}


@router.post("/disconnect")
async def disconnect_dialer(request: Request):
    """Remove dialer connection and clear stored credentials."""
    user = get_current_user(request)

    await db.update_settings(user["user_id"], {
        "dialer_connection_code": None,
        "twilio_account_sid": None,
        "twilio_auth_token": None,
        "grokbot_account_linked": False,
    })

    return {"ok": True, "message": "Dialer disconnected"}

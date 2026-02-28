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

GROKBOT_API_URL = "https://insurancegrokbot.click/api/v1/training"


class UpdateSettingsRequest(BaseModel):
    preferred_voice: str | None = None
    auto_import_recordings: bool | None = None
    email_weekly_report: bool | None = None
    email_session_summary: bool | None = None


class ConnectDialerRequest(BaseModel):
    connection_code: str


@router.get("/")
async def get_settings(request: Request):
    user = get_current_user(request)
    settings = await db.get_settings(user["user_id"])
    # Strip sensitive fields — only expose what the frontend needs
    settings.pop("grokbot_api_key", None)
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
    """Validate a training token against InsuranceGrokBot and link the account."""
    user = get_current_user(request)
    token = req.connection_code.strip()

    if not token:
        raise HTTPException(status_code=400, detail="Connection code is required")

    # Validate the token with InsuranceGrokBot API
    validated = False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{GROKBOT_API_URL}/validate",
                headers={"Authorization": f"Bearer {token}"},
            )

        if resp.status_code == 401 or resp.status_code == 403:
            raise HTTPException(
                status_code=400,
                detail="Invalid connection code. Please check the code and try again.",
            )

        if resp.status_code == 200:
            validated = True

    except httpx.RequestError:
        # GrokBot API unreachable — save code anyway so it persists,
        # we'll re-validate on next sync or recording import.
        pass

    # Store the connection code and mark as linked
    await db.update_settings(user["user_id"], {
        "dialer_connection_code": token,
        "grokbot_account_linked": True,
    })

    msg = "Dialer connected successfully"
    if not validated:
        msg = "Connection code saved. Will verify when InsuranceGrokBot servers are reachable."
    return {"ok": True, "message": msg}


@router.post("/disconnect")
async def disconnect_dialer(request: Request):
    """Remove dialer connection and clear stored token."""
    user = get_current_user(request)

    await db.update_settings(user["user_id"], {
        "dialer_connection_code": None,
        "grokbot_account_linked": False,
    })

    return {"ok": True, "message": "Dialer disconnected"}

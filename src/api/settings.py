"""
Settings routes: user preferences, account linking, notifications.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.api.middleware import get_current_user
from src.core import database as db

router = APIRouter(prefix="/api/settings", tags=["settings"])


class UpdateSettingsRequest(BaseModel):
    preferred_voice: str | None = None
    auto_import_recordings: bool | None = None
    grokbot_account_linked: bool | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    email_weekly_report: bool | None = None
    email_session_summary: bool | None = None


@router.get("/")
async def get_settings(request: Request):
    user = get_current_user(request)
    settings = await db.get_settings(user["user_id"])
    # Strip sensitive fields
    settings.pop("twilio_auth_token", None)
    return settings


@router.post("/")
async def update_settings(req: UpdateSettingsRequest, request: Request):
    user = get_current_user(request)
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if updates:
        await db.update_settings(user["user_id"], updates)
    return {"ok": True}

"""
Call recording import routes.
Integrates with Twilio to fetch and analyze real call recordings.
"""

from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.api.middleware import get_current_user
from src.core import database as db

router = APIRouter(prefix="/api/recordings", tags=["recordings"])


class ImportRecordingRequest(BaseModel):
    recording_sid: str | None = None
    call_sid: str | None = None
    recording_url: str | None = None
    duration: int | None = None
    call_date: str | None = None
    caller_number: str | None = None
    agent_name: str | None = None


@router.get("/")
async def list_recordings(request: Request, limit: int = 50):
    user = get_current_user(request)
    return await db.get_call_recordings(user["user_id"], limit)


@router.post("/import")
async def import_recording(req: ImportRecordingRequest, request: Request):
    """Import a single call recording for analysis."""
    user = get_current_user(request)

    recording_data = {
        "recording_sid": req.recording_sid,
        "call_sid": req.call_sid,
        "recording_url": req.recording_url,
        "duration": req.duration,
        "call_date": datetime.fromisoformat(req.call_date) if req.call_date else None,
        "caller_number": req.caller_number,
        "agent_name": req.agent_name,
    }

    rec_id = await db.save_call_recording(user["user_id"], recording_data)

    # TODO: Queue background analysis job
    # For now, return the recording ID
    return {"recording_id": rec_id, "status": "pending"}


@router.post("/sync")
async def sync_twilio_recordings(request: Request):
    """Sync recent call recordings from Twilio."""
    user = get_current_user(request)
    settings = await db.get_settings(user["user_id"])

    if not settings.get("grokbot_account_linked"):
        raise HTTPException(status_code=400, detail="InsuranceGrokBot account not linked")

    account_sid = settings.get("twilio_account_sid")
    auth_token = settings.get("twilio_auth_token")

    if not account_sid or not auth_token:
        raise HTTPException(status_code=400, detail="Twilio credentials not configured")

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)

        # Fetch recent recordings
        recordings = client.recordings.list(limit=20)
        imported = []

        for rec in recordings:
            recording_data = {
                "recording_sid": rec.sid,
                "call_sid": rec.call_sid,
                "recording_url": f"https://api.twilio.com{rec.uri.replace('.json', '.mp3')}",
                "duration": int(rec.duration) if rec.duration else None,
                "call_date": rec.date_created,
                "caller_number": None,
                "agent_name": None,
            }
            rec_id = await db.save_call_recording(user["user_id"], recording_data)
            imported.append(rec_id)

        return {"imported_count": len(imported), "recording_ids": imported}

    except ImportError:
        raise HTTPException(status_code=500, detail="Twilio SDK not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Twilio sync failed: {str(e)}")


@router.get("/{recording_id}")
async def get_recording(recording_id: str, request: Request):
    user = get_current_user(request)
    pool = await db.get_pool()
    import uuid
    row = await pool.fetchrow(
        "SELECT * FROM call_recordings WHERE id = $1",
        uuid.UUID(recording_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Recording not found")
    rec = dict(row)
    if str(rec["user_id"]) != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return rec

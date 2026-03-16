"""
Call recording import routes.
Integrates with InsuranceGrokBot Dialer to fetch and analyze real call recordings.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import os

import httpx
from fastapi import APIRouter, HTTPException, Request

from src.api.middleware import get_current_user
from src.core import database as db

router = APIRouter(prefix="/api/recordings", tags=["recordings"])

GROKBOT_API_URL = os.environ.get("GROKBOT_API_URL", "https://insurancegrokbot.com/api/v1/training")


@router.get("/")
async def list_recordings(request: Request, limit: int = 50):
    user = get_current_user(request)
    return await db.get_call_recordings(user["user_id"], limit)


@router.post("/sync")
async def sync_dialer_recordings(request: Request):
    """Sync call recordings from InsuranceGrokBot Dialer API."""
    user = get_current_user(request)
    settings = await db.get_settings(user["user_id"])

    if not settings.get("grokbot_account_linked"):
        raise HTTPException(
            status_code=400,
            detail="InsuranceGrokBot Dialer not connected. Go to Settings to connect.",
        )

    token = settings.get("dialer_connection_code")
    if not token:
        raise HTTPException(
            status_code=400,
            detail="Dialer connection code missing. Please reconnect in Settings.",
        )

    headers = {"Authorization": f"Bearer {token}"}

    try:
        imported = []
        offset = 0
        limit = 200

        async with httpx.AsyncClient(timeout=30) as client:
            # Get the latest recording we already have for incremental sync
            existing = await db.get_call_recordings(user["user_id"], limit=1)
            since = None
            if existing and existing[0].get("call_date"):
                since = existing[0]["call_date"]
                if isinstance(since, datetime):
                    since = since.isoformat()

            # Paginate through all recordings
            while True:
                params = {"limit": limit, "offset": offset}
                if since:
                    params["since"] = since

                resp = await client.get(
                    f"{GROKBOT_API_URL}/recordings",
                    headers=headers,
                    params=params,
                )

                if resp.status_code == 401:
                    raise HTTPException(
                        status_code=400,
                        detail="Connection code expired or revoked. Please reconnect in Settings.",
                    )
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=502,
                        detail="Failed to fetch recordings from InsuranceGrokBot.",
                    )

                data = resp.json()
                recordings = data if isinstance(data, list) else (data.get("recordings") or data.get("data") or [])

                if not recordings:
                    break

                for rec in recordings:
                    recording_data = {
                        "call_sid": rec.get("call_sid"),
                        "recording_url": rec.get("audio_url") or rec.get("recording_url"),
                        "duration": rec.get("duration"),
                        "call_date": rec.get("call_date") or rec.get("created_at"),
                        "caller_number": rec.get("phone"),
                        "agent_name": rec.get("contact_name"),
                        "direction": rec.get("direction"),
                        "disposition": rec.get("disposition"),
                        "transcript": rec.get("transcript"),
                    }
                    rec_id = await db.save_call_recording(user["user_id"], recording_data)
                    if rec_id:
                        imported.append(rec_id)

                # Use API's has_more flag when available, fall back to count check
                has_more = data.get("has_more", len(recordings) >= limit) if isinstance(data, dict) else len(recordings) >= limit
                if not has_more:
                    break
                offset += limit

        return {"imported_count": len(imported), "recording_ids": imported}

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Could not reach InsuranceGrokBot servers. Please try again later.",
        )


@router.get("/stats")
async def recording_stats(request: Request):
    """Get summary stats for imported recordings."""
    user = get_current_user(request)
    settings = await db.get_settings(user["user_id"])

    if not settings.get("grokbot_account_linked") or not settings.get("dialer_connection_code"):
        return {"connected": False}

    token = settings["dialer_connection_code"]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{GROKBOT_API_URL}/stats",
                headers={"Authorization": f"Bearer {token}"},
            )
        if resp.status_code == 200:
            stats = resp.json()
            stats["connected"] = True
            return stats
        return {"connected": True}
    except httpx.RequestError:
        return {"connected": True, "error": "Could not fetch stats"}


@router.get("/{recording_id}")
async def get_recording(recording_id: str, request: Request):
    user = get_current_user(request)
    pool = await db.get_pool()
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

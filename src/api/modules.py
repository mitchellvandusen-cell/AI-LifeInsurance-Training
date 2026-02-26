"""
Training Modules & Homework API routes.
Handles module session creation, voice streaming, and homework generation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from src.api.middleware import get_current_user, get_ws_user
from src.core import database as db
from src.engine.homework_engine import HomeworkEngine
from src.knowledge.sales_mastery import TRAINING_MODULES
from src.prompts.module_prompts import build_module_prompt
from src.services.voice import VoiceSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/modules", tags=["modules"])

# Active module sessions in memory
_active_module_sessions: dict[str, dict] = {}

AVAILABLE_MODULES = {
    key: {
        "key": key,
        "name": mod["name"],
        "description": mod["description"],
        "skills_taught": mod["skills_taught"],
    }
    for key, mod in TRAINING_MODULES.items()
    if key != "full_call_simulation"  # Full sim is the existing training flow
}


# ── Module List ──────────────────────────────────────────────────

@router.get("/")
async def list_modules(request: Request):
    """List all available training modules."""
    get_current_user(request)  # Auth check
    return {"modules": list(AVAILABLE_MODULES.values())}


# ── Start Module Session ─────────────────────────────────────────

class StartModuleRequest(BaseModel):
    module_key: str
    voice: str | None = None


@router.post("/start")
async def start_module_session(req: StartModuleRequest, request: Request):
    """Start a focused training module session."""
    user = get_current_user(request)
    user_id = user["user_id"]

    if req.module_key not in AVAILABLE_MODULES:
        raise HTTPException(status_code=400, detail=f"Unknown module: {req.module_key}")

    # Check subscription / billing
    remaining = await db.get_remaining_minutes(user_id)
    total_available = (
        remaining["subscription_minutes"]
        + remaining["addon_minutes"]
        + (remaining["wallet_cents"] // 10)
    )
    if total_available <= 0:
        raise HTTPException(
            status_code=402,
            detail="No training time available. Add funds or upgrade your subscription.",
        )

    voice = req.voice or "Sal"

    # Save to database
    session_record = await db.create_module_session(
        user_id=user_id,
        module_key=req.module_key,
        voice_name=voice,
    )

    # Store in memory
    _active_module_sessions[session_record["id"]] = {
        "user_id": user_id,
        "module_key": req.module_key,
        "voice": voice,
        "voice_session": None,
        "start_time": time.time(),
        "session_state": {},
    }

    module_info = AVAILABLE_MODULES[req.module_key]
    print(f"[MODULE] Started: {session_record['id']} | {module_info['name']} | voice={voice}")

    return {
        "session_id": session_record["id"],
        "module": module_info,
        "voice": voice,
    }


# ── Module Voice WebSocket ───────────────────────────────────────

@router.websocket("/ws/{session_id}")
async def module_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for module voice training."""
    await websocket.accept()

    ws_user = await get_ws_user(websocket)
    if not ws_user:
        return

    session = _active_module_sessions.get(session_id)
    if not session:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return

    if session["user_id"] != ws_user["user_id"]:
        await websocket.send_json({"type": "error", "message": "Unauthorized"})
        await websocket.close()
        return

    # Build module-specific system prompt
    module_key = session["module_key"]
    system_prompt = build_module_prompt(module_key, session.get("session_state", {}))

    # Callbacks for transcript processing
    async def on_agent_transcript(text: str, turn: int):
        """When the student speaks — log and potentially update coach context."""
        print(f"[MODULE][{session_id}] Student said (turn {turn}): {text[:80]}...")
        try:
            await websocket.send_json({
                "type": "transcript",
                "role": "agent",
                "text": text,
                "turn": turn,
            })
        except Exception:
            pass

    async def on_client_transcript(text: str, turn: int):
        """When the AI coach speaks — log."""
        print(f"[MODULE][{session_id}] Coach said (turn {turn}): {text[:80]}...")
        try:
            await websocket.send_json({
                "type": "transcript",
                "role": "coach",
                "text": text,
                "turn": turn,
            })
        except Exception:
            pass

    # Create voice session
    voice_session = VoiceSession(
        session_id=session_id,
        system_prompt=system_prompt,
        voice=session.get("voice", "Sal"),
        on_agent_transcript=on_agent_transcript,
        on_client_transcript=on_client_transcript,
    )
    session["voice_session"] = voice_session

    # Connect to xAI
    await websocket.send_json({"type": "status", "status": "connecting_voice"})
    connected = await voice_session.connect()
    if not connected:
        await websocket.send_json({
            "type": "error",
            "message": "Failed to connect to voice service.",
        })
        await websocket.close()
        return

    await websocket.send_json({"type": "status", "status": "ready"})

    # Bridge: browser ↔ xAI
    async def browser_to_xai():
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if data.get("type") == "audio":
                    audio_data = data.get("data", "")
                    if audio_data:
                        await voice_session.send_audio(audio_data)
                elif data.get("type") == "end":
                    break
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"[MODULE][{session_id}] Browser→xAI error: {e}")

    async def xai_to_browser():
        async def send_to_browser(msg: dict):
            try:
                await websocket.send_json(msg)
            except Exception:
                pass
        await voice_session.receive_events(send_to_browser)

    try:
        browser_task = asyncio.create_task(browser_to_xai())
        xai_task = asyncio.create_task(xai_to_browser())
        done, pending = await asyncio.wait(
            [browser_task, xai_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except Exception as e:
        logger.error(f"[MODULE][{session_id}] Bridge error: {e}")
    finally:
        await voice_session.disconnect()


# ── End Module Session ───────────────────────────────────────────

@router.post("/{session_id}/end")
async def end_module_session(session_id: str, request: Request):
    """End a module training session."""
    user = get_current_user(request)

    session = _active_module_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Disconnect voice
    voice_sess = session.get("voice_session")
    if voice_sess:
        await voice_sess.disconnect()

    duration_seconds = int(time.time() - session["start_time"])
    billed_minutes = max(1, duration_seconds // 60)

    # Billing
    remaining = await db.get_remaining_minutes(user["user_id"])
    billed_from = "subscription"
    cost_cents = 0
    if remaining["subscription_minutes"] >= billed_minutes:
        await db.use_subscription_minutes(user["user_id"], billed_minutes)
    elif remaining["addon_minutes"] >= billed_minutes:
        billed_from = "add_on"
    else:
        billed_from = "wallet"
        cost_cents = billed_minutes * 10
        await db.deduct_wallet(
            user["user_id"], cost_cents, session_id,
            f"Module training: {session['module_key']} ({billed_minutes} min)"
        )

    # Save
    await db.end_module_session(
        session_id=session_id,
        duration_seconds=duration_seconds,
        session_state=session.get("session_state", {}),
        feedback_summary=f"Completed {session['module_key']} training module",
        billed_minutes=billed_minutes,
        cost_cents=cost_cents,
        billed_from=billed_from,
    )

    _active_module_sessions.pop(session_id, None)

    return {
        "session_id": session_id,
        "module_key": session["module_key"],
        "duration_seconds": duration_seconds,
        "billed_minutes": billed_minutes,
    }


# ── Module Session History ───────────────────────────────────────

@router.get("/history")
async def get_module_history(request: Request, module_key: str = None, limit: int = 50):
    """Get module session history for the current user."""
    user = get_current_user(request)
    return await db.get_module_sessions(user["user_id"], module_key, limit)


# ═══════════════════════════════════════════════════════════════
# HOMEWORK ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/homework/generate")
async def generate_homework(request: Request):
    """Analyze recent sessions and generate targeted homework."""
    user = get_current_user(request)
    user_id = user["user_id"]

    # Get all report cards for analysis
    report_cards = await db.get_user_report_cards(user_id, limit=50)

    engine = HomeworkEngine(min_sessions=5)
    result = engine.analyze(report_cards)

    if not result:
        return {
            "status": "insufficient_data",
            "message": f"Need at least 5 completed sessions for homework analysis. You have {len(report_cards)}.",
            "sessions_completed": len(report_cards),
            "sessions_needed": 5,
        }

    # Convert to serializable dict
    homework_data = {
        "sessions_analyzed": result.sessions_analyzed,
        "overall_assessment": result.overall_assessment,
        "strengths": result.strengths,
        "weaknesses": result.weaknesses,
        "assignments": [asdict(a) for a in result.assignments],
        "focus_order": result.recommended_focus_order,
    }

    # Save to database
    report_id = await db.save_homework_report(user_id, homework_data)

    return {
        "status": "generated",
        "report_id": report_id,
        **homework_data,
    }


@router.get("/homework/latest")
async def get_latest_homework(request: Request):
    """Get the most recent homework report."""
    user = get_current_user(request)
    report = await db.get_latest_homework(user["user_id"])
    if not report:
        return {"status": "none", "message": "No homework generated yet."}
    return report


@router.get("/homework/history")
async def get_homework_history(request: Request, limit: int = 10):
    """Get homework report history."""
    user = get_current_user(request)
    return await db.get_homework_history(user["user_id"], limit)

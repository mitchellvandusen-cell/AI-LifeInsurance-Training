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

# Maximum module session age before automatic cleanup (2 hours)
_MODULE_SESSION_TTL_SECONDS = 2 * 60 * 60


async def _cleanup_stale_module_sessions():
    """Background task: evict module sessions older than TTL to prevent memory leaks."""
    while True:
        await asyncio.sleep(300)  # Check every 5 minutes
        now = time.time()
        stale = [
            sid for sid, s in _active_module_sessions.items()
            if now - s.get("start_time", now) > _MODULE_SESSION_TTL_SECONDS
        ]
        for sid in stale:
            session = _active_module_sessions.pop(sid, None)
            if session:
                voice_sess = session.get("voice_session")
                if voice_sess:
                    await voice_sess.disconnect()
                logger.warning("[MODULE] Evicted stale module session %s (TTL exceeded)", sid)


def start_module_session_cleanup():
    """Call once at startup to begin the background cleanup loop."""
    asyncio.create_task(_cleanup_stale_module_sessions())


AVAILABLE_MODULES = {
    key: {
        "key": key,
        "name": mod["name"],
        "description": mod["description"],
        "skills_taught": mod["skills_taught"],
        "topics": mod.get("topics", []),
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
    script_id: str | None = None  # For script_practice module
    topic_index: int | None = None  # Index into module's topics list


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

    # Resolve topic if provided
    topic_info = None
    if req.topic_index is not None and req.module_key in AVAILABLE_MODULES:
        topics = AVAILABLE_MODULES[req.module_key].get("topics", [])
        if 0 <= req.topic_index < len(topics):
            topic_info = topics[req.topic_index]

    # Load mastery data for adaptive difficulty
    session_state = {}
    mastery_data = None
    script = None

    # Inject topic info into session state for prompt builder
    if topic_info:
        session_state["topic_name"] = topic_info["name"]
        session_state["topic_anchor"] = topic_info["anchor"]
        session_state["topic_focus"] = topic_info["focus"]
        session_state["topic_sessions"] = topic_info["sessions"]
        session_state["topic_index"] = req.topic_index

    if req.module_key == "script_practice" and req.script_id:
        # Script practice: load script content + script-specific mastery
        script = await db.get_user_script(user_id, req.script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        session_state["script_content"] = script["content"]
        session_state["script_name"] = script["name"]
        session_state["script_id"] = req.script_id

        mastery = await db.get_script_mastery(user_id, req.script_id)
        practice_count = mastery["practice_count"] if mastery else 0
        mastery_level = mastery["mastery_level"] if mastery else 0
        sessions_per_level = mastery.get("sessions_per_level", 10) if mastery else 10
        session_state["practice_count"] = practice_count
        session_state["mastery_level"] = mastery_level
        mastery_data = {
            "practice_count": practice_count,
            "mastery_level": mastery_level,
            "sessions_per_level": sessions_per_level,
        }
    else:
        # All other modules: load module-level mastery
        mastery = await db.get_module_mastery(user_id, req.module_key)
        practice_count = mastery["practice_count"] if mastery else 0
        mastery_level = mastery["mastery_level"] if mastery else 0
        session_state["practice_count"] = practice_count
        session_state["mastery_level"] = mastery_level
        mastery_data = {
            "practice_count": practice_count,
            "mastery_level": mastery_level,
        }

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
        "session_state": session_state,
    }

    module_info = AVAILABLE_MODULES[req.module_key]
    print(f"[MODULE] Started: {session_record['id']} | {module_info['name']} | voice={voice} | level={mastery_level}")

    response = {
        "session_id": session_record["id"],
        "module": module_info,
        "voice": voice,
        "mastery": mastery_data,
    }
    if topic_info:
        response["topic"] = topic_info
    if script:
        response["script_content"] = script["content"]
        response["script_name"] = script["name"]
    return response


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

    # Disconnect any existing voice session to prevent duplicate agents
    existing_voice = session.get("voice_session")
    if existing_voice:
        logger.warning("[MODULE][%s] Disconnecting previous voice session before new connection", session_id)
        await existing_voice.disconnect()
        session["voice_session"] = None

    # Build module-specific system prompt
    module_key = session["module_key"]
    system_prompt = build_module_prompt(module_key, session.get("session_state", {}))

    # Callbacks for transcript processing
    # NOTE: voice.py receive_events() already sends transcript/transcript_delta
    # to the browser via send_to_browser. These callbacks are for server-side
    # processing only — do NOT send duplicate transcripts to the browser here.
    async def on_agent_transcript(text: str, turn: int):
        """When the student speaks — log for server-side processing."""
        print(f"[MODULE][{session_id}] Student said (turn {turn}): {text[:80]}...")
        session.setdefault("student_turns", 0)
        session["student_turns"] += 1

    async def on_client_transcript(text: str, turn: int):
        """When the AI coach speaks — log and detect session closing."""
        print(f"[MODULE][{session_id}] Coach said (turn {turn}): {text[:80]}...")
        session.setdefault("coach_turns", 0)
        session["coach_turns"] += 1

        # Detect the coach's closing phrase signaling session is complete
        if not session.get("coach_concluded") and "that is a wrap for today" in text.lower():
            session["coach_concluded"] = True
            print(f"[MODULE][{session_id}] Coach concluded session naturally")
            try:
                await websocket.send_json({
                    "type": "session_complete",
                    "message": "Your coach has wrapped up the session.",
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

    async def keepalive_ping():
        """Send periodic heartbeat pings to prevent proxy/LB idle timeouts."""
        try:
            while True:
                await asyncio.sleep(15)
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
        except asyncio.CancelledError:
            pass

    try:
        # Start both listener tasks FIRST so they are ready to receive events
        browser_task = asyncio.create_task(browser_to_xai())
        xai_task = asyncio.create_task(xai_to_browser())
        ping_task = asyncio.create_task(keepalive_ping())

        # Small yield to let the xai_to_browser listener attach before triggering
        await asyncio.sleep(0.05)

        # NOW trigger AI coach to speak first — greet the student and begin the lesson.
        # This sends response.create to xAI, causing the model to generate its
        # opening greeting based on the system prompt (which says "YOU SPEAK FIRST").
        # MUST happen AFTER receive_events() is listening, otherwise greeting audio
        # could arrive before anyone is consuming events from the xAI WebSocket.
        await voice_session.trigger_greeting()

        done, pending = await asyncio.wait(
            [browser_task, xai_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        ping_task.cancel()
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

    # ── Session completion validation ──────────────────────────
    # Only qualified when the AI coach completes its full lesson arc
    # (greeting → teach → drill → practice → analysis → closing phrase).
    # No timer fallback — the coach decides when the agent is ready.
    coach_concluded = session.get("coach_concluded", False)
    session_qualified = coach_concluded

    # Billing (always bill even incomplete sessions — they used voice time)
    remaining = await db.get_remaining_minutes(user["user_id"])
    billed_from = "subscription"
    cost_cents = 0
    if remaining["subscription_minutes"] >= billed_minutes:
        await db.use_subscription_minutes(user["user_id"], billed_minutes)
    elif remaining["addon_minutes"] >= billed_minutes:
        billed_from = "add_on"
        await db.use_addon_minutes(user["user_id"], billed_minutes)
    else:
        billed_from = "wallet"
        cost_cents = billed_minutes * 10
        await db.deduct_wallet(
            user["user_id"], cost_cents, session_id,
            f"Module training: {session['module_key']} ({billed_minutes} min)"
        )

    # Determine session status
    status = "completed" if session_qualified else "cancelled"

    # Save
    await db.end_module_session(
        session_id=session_id,
        duration_seconds=duration_seconds,
        session_state=session.get("session_state", {}),
        feedback_summary=(
            f"Completed {session['module_key']} training module"
            if session_qualified
            else f"Ended early — {duration_seconds}s (coach did not complete full lesson)"
        ),
        billed_minutes=billed_minutes,
        cost_cents=cost_cents,
        billed_from=billed_from,
        status=status,
    )

    # Only increment mastery for qualified sessions
    mastery_data = None
    state = session.get("session_state", {})
    module_key = session["module_key"]

    if session_qualified:
        if module_key == "script_practice" and state.get("script_id"):
            mastery = await db.increment_script_mastery(
                user["user_id"], state["script_id"]
            )
            mastery_data = {
                "practice_count": mastery["practice_count"],
                "mastery_level": mastery["mastery_level"],
                "sessions_per_level": mastery.get("sessions_per_level", 10),
            }
        else:
            mastery = await db.increment_module_mastery(
                user["user_id"], module_key
            )
            mastery_data = {
                "practice_count": mastery["practice_count"],
                "mastery_level": mastery["mastery_level"],
            }

        # Update daily analytics for KPI dashboard
        from datetime import datetime, timezone
        await db.compute_analytics_for_date(user["user_id"], datetime.now(timezone.utc))
    else:
        # Return current mastery without incrementing
        if module_key == "script_practice" and state.get("script_id"):
            existing = await db.get_script_mastery(user["user_id"], state["script_id"])
            mastery_data = {
                "practice_count": existing["practice_count"] if existing else 0,
                "mastery_level": existing["mastery_level"] if existing else 0,
                "sessions_per_level": existing.get("sessions_per_level", 10) if existing else 10,
            }
        else:
            existing = await db.get_module_mastery(user["user_id"], module_key)
            mastery_data = {
                "practice_count": existing["practice_count"] if existing else 0,
                "mastery_level": existing["mastery_level"] if existing else 0,
            }

    _active_module_sessions.pop(session_id, None)

    response = {
        "session_id": session_id,
        "module_key": module_key,
        "duration_seconds": duration_seconds,
        "billed_minutes": billed_minutes,
        "mastery": mastery_data,
        "session_qualified": session_qualified,
    }
    if not session_qualified:
        response["message"] = (
            "Session ended before your coach completed the lesson. "
            "Finish all drills and practice to earn mastery credit."
        )
    return response


# ── Module Session History ───────────────────────────────────────

@router.get("/history")
async def get_module_history(request: Request, module_key: str = None, limit: int = 50):
    """Get module session history for the current user."""
    user = get_current_user(request)
    return await db.get_module_sessions(user["user_id"], module_key, limit)


# ── Script Mastery ────────────────────────────────────────────

@router.get("/mastery")
async def get_all_mastery(request: Request):
    """Get mastery data for all modules belonging to the current user."""
    user = get_current_user(request)
    records = await db.get_all_module_mastery(user["user_id"])
    return {r["module_key"]: r for r in records}


@router.get("/scripts/mastery")
async def get_all_script_mastery(request: Request):
    """Get mastery data for all scripts belonging to the current user."""
    user = get_current_user(request)
    records = await db.get_all_script_mastery(user["user_id"])
    # Return as a dict keyed by script_id for easy frontend lookup
    return {str(r["script_id"]): r for r in records}


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


# ═══════════════════════════════════════════════════════════════
# SCRIPT MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════

MAX_SCRIPT_CHARS = 100_000


class SaveScriptRequest(BaseModel):
    name: str
    content: str


class UpdateScriptRequest(BaseModel):
    name: str | None = None
    content: str | None = None


@router.post("/scripts")
async def save_script(req: SaveScriptRequest, request: Request):
    """Save a new script (paste). Max 100,000 characters."""
    user = get_current_user(request)
    if len(req.content) > MAX_SCRIPT_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Script too long. Max {MAX_SCRIPT_CHARS:,} characters.",
        )
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Script content is empty.")
    result = await db.save_user_script(
        user["user_id"], req.name.strip(), req.content, source="paste"
    )
    return result


@router.post("/scripts/upload")
async def upload_script(request: Request):
    """Upload a script file (txt, pdf, docx). Max 100,000 characters after extraction."""
    user = get_current_user(request)

    # Read multipart form data
    form = await request.form()
    file = form.get("file")
    name = form.get("name", "")

    if not file:
        raise HTTPException(status_code=400, detail="No file provided.")

    filename = getattr(file, "filename", "script.txt") or "script.txt"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    raw_bytes = await file.read()

    # Extract text based on file type
    if ext == "txt":
        content = raw_bytes.decode("utf-8", errors="replace")
    elif ext == "pdf":
        content = _extract_pdf_text(raw_bytes)
    elif ext in ("docx", "doc"):
        content = _extract_docx_text(raw_bytes)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Use .txt, .pdf, or .docx.",
        )

    if not content.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file.")

    if len(content) > MAX_SCRIPT_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Extracted text too long ({len(content):,} chars). Max {MAX_SCRIPT_CHARS:,}.",
        )

    script_name = name.strip() or filename.rsplit(".", 1)[0]
    result = await db.save_user_script(
        user["user_id"], script_name, content, source=f"upload:{ext}"
    )
    return result


@router.get("/scripts")
async def list_scripts(request: Request):
    """List all scripts for the current user."""
    user = get_current_user(request)
    scripts = await db.get_user_scripts(user["user_id"])
    return {"scripts": scripts}


@router.get("/scripts/{script_id}")
async def get_script(script_id: str, request: Request):
    """Get a specific script with content."""
    user = get_current_user(request)
    script = await db.get_user_script(user["user_id"], script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found.")
    return script


@router.put("/scripts/{script_id}")
async def update_script(script_id: str, req: UpdateScriptRequest, request: Request):
    """Update script name or content."""
    user = get_current_user(request)
    if req.content and len(req.content) > MAX_SCRIPT_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Script too long. Max {MAX_SCRIPT_CHARS:,} characters.",
        )
    result = await db.update_user_script(
        user["user_id"], script_id,
        name=req.name.strip() if req.name else None,
        content=req.content,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Script not found.")
    return result


@router.delete("/scripts/{script_id}")
async def delete_script(script_id: str, request: Request):
    """Delete a script."""
    user = get_current_user(request)
    deleted = await db.delete_user_script(user["user_id"], script_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Script not found.")
    return {"deleted": True}


# ── File text extraction helpers ─────────────────────────────

def _extract_pdf_text(raw_bytes: bytes) -> str:
    """Extract text from PDF bytes. Uses pypdf if available, falls back to basic."""
    try:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except ImportError:
        logger.warning("[SCRIPT] pypdf not installed — cannot extract PDF text")
        raise HTTPException(
            status_code=400,
            detail="PDF extraction not available. Please paste your script as text or upload a .txt file.",
        )
    except Exception as e:
        logger.error(f"[SCRIPT] PDF extraction error: {e}")
        raise HTTPException(status_code=400, detail="Failed to extract text from PDF.")


def _extract_docx_text(raw_bytes: bytes) -> str:
    """Extract text from DOCX bytes. Uses python-docx if available."""
    try:
        import io
        from docx import Document
        doc = Document(io.BytesIO(raw_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except ImportError:
        logger.warning("[SCRIPT] python-docx not installed — cannot extract DOCX text")
        raise HTTPException(
            status_code=400,
            detail="DOCX extraction not available. Please paste your script as text or upload a .txt file.",
        )
    except Exception as e:
        logger.error(f"[SCRIPT] DOCX extraction error: {e}")
        raise HTTPException(status_code=400, detail="Failed to extract text from DOCX.")

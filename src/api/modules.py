"""
Training Modules & Homework API routes.
Handles module session creation, voice streaming, and homework generation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from src.api.middleware import get_current_user, get_ws_user
from src.core import database as db
from src.engine.homework_engine import HomeworkEngine
from src.engine.module_report_generator import generate_module_report_card
from src.engine.persona_generator import PersonaGenerator, analyze_script_for_persona
from src.knowledge.sales_mastery import TRAINING_MODULES
from src.knowledge.mastery_curriculum import CURRICULUM, PHASES, TOTAL_DAYS, TOTAL_ACTIVITIES
from src.prompts.module_prompts import build_module_prompt
from src.services.voice import VoiceSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/modules", tags=["modules"])

# Active module sessions in memory
_active_module_sessions: dict[str, dict] = {}

# Maximum module session age before automatic cleanup (4 hours)
_MODULE_SESSION_TTL_SECONDS = 4 * 60 * 60


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
        session_state["script_type"] = script.get("script_type", "")

        mastery = await db.get_script_mastery(user_id, req.script_id)
        practice_count = mastery["practice_count"] if mastery else 0
        mastery_level = mastery["mastery_level"] if mastery else 0
        sessions_per_level = mastery.get("sessions_per_level", 10) if mastery else 10
        session_state["practice_count"] = practice_count
        session_state["mastery_level"] = mastery_level

        # Analyze script and generate a matched client persona
        # If the user set a script_type tag, use it to override auto-detection
        script_analysis = analyze_script_for_persona(
            script["content"],
            script_type_override=script.get("script_type", ""),
        )
        session_state["script_analysis"] = script_analysis

        gen = PersonaGenerator()
        matched_persona = gen.generate_for_script(
            script["content"],
            mastery_level=mastery_level,
            practice_count=practice_count,
            script_type_override=script.get("script_type", ""),
            precomputed_analysis=script_analysis,
        )

        # ── Auto-select voice to match persona gender ──
        # In script practice, the AI plays the CLIENT (prospect).
        # The voice must match the persona's gender for immersion.
        # Available xAI voices: Ara (F), Eve (F), Rex (M), Leo (M), Sal (neutral)
        if not req.voice:
            if matched_persona.gender == "female":
                voice = random.choice(["Ara", "Eve"])
            elif matched_persona.gender == "male":
                voice = random.choice(["Rex", "Leo"])
            else:
                voice = "Sal"

        # Serialize persona for prompt injection
        session_state["matched_persona"] = {
            "name": matched_persona.name,
            "age": matched_persona.age,
            "gender": matched_persona.gender,
            "occupation": matched_persona.occupation,
            "marital_status": matched_persona.marital_status,
            "dependents": matched_persona.dependents,
            "annual_income": matched_persona.annual_income,
            "health_conditions": matched_persona.health_conditions,
            "medications": matched_persona.medications,
            "tobacco_use": matched_persona.tobacco_use,
            "existing_coverage": matched_persona.existing_coverage,
            "reason_for_inquiry": matched_persona.reason_for_inquiry,
            "pain_points": matched_persona.pain_points,
            "personality_notes": matched_persona.personality_notes,
            "skepticism_level": matched_persona.skepticism_level,
            "baseline_trust": matched_persona.baseline_trust,
            "budget_sensitivity": matched_persona.budget_sensitivity,
            "talkativeness": matched_persona.talkativeness,
            "will_test_frame_control": matched_persona.will_test_frame_control,
        }
        print(f"[SCRIPT] Analyzed: product={script_analysis['product_type']}, "
              f"archetype={script_analysis['archetype_name']}, "
              f"lead={script_analysis['lead_type']}, "
              f"persona={matched_persona.name} ({matched_persona.gender}, age {matched_persona.age}), "
              f"voice={voice}")

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
        # Include matched persona info so the UI can show who they're practicing with
        if session_state.get("matched_persona"):
            persona_info = session_state["matched_persona"]
            response["matched_client"] = {
                "name": persona_info["name"],
                "age": persona_info["age"],
                "occupation": persona_info["occupation"],
                "product_type": session_state.get("script_analysis", {}).get("product_type", "general_life"),
                "lead_type": session_state.get("script_analysis", {}).get("lead_type", "unknown"),
            }
    return response


# ── Module Voice WebSocket ───────────────────────────────────────

@router.websocket("/ws/{session_id}")
async def module_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for module voice training.

    Architecture: The xAI voice session runs independently as a background task.
    This handler only bridges browser audio ↔ xAI and swaps the browser callback.
    If the browser disconnects and reconnects, the xAI session keeps running —
    we just re-bridge without losing conversation context.
    """
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

    # ── Voice session: reuse or create ──────────────────────
    existing_voice = session.get("voice_session")
    is_reconnect = False

    if existing_voice and existing_voice.connected:
        # Reuse the still-connected xAI session
        logger.info("[MODULE][%s] Browser reconnected — reusing xAI session (turn %d)", session_id, existing_voice._turn_count)
        voice_session = existing_voice
        is_reconnect = True
    elif existing_voice and existing_voice._receive_task and not existing_voice._receive_task.done():
        # xAI receive loop is still running (reconnecting maybe)
        logger.info("[MODULE][%s] Browser reconnected — xAI receive loop still active", session_id)
        voice_session = existing_voice
        is_reconnect = True
    else:
        # No existing session or it's dead — create new one
        if existing_voice:
            logger.warning("[MODULE][%s] Previous voice session dead — creating new one", session_id)
            await existing_voice.disconnect()

        module_key = session["module_key"]
        system_prompt = build_module_prompt(module_key, session.get("session_state", {}))

        async def on_agent_transcript(text: str, turn: int):
            print(f"[MODULE][{session_id}] Student said (turn {turn}): {text[:80]}...")
            session.setdefault("student_turns", 0)
            session["student_turns"] += 1
            # Track conversation for report card generation
            session.setdefault("conversation_log", [])
            session["conversation_log"].append({"role": "agent", "content": text, "turn": turn})

        async def on_client_transcript(text: str, turn: int):
            print(f"[MODULE][{session_id}] Coach said (turn {turn}): {text[:80]}...")
            session.setdefault("coach_turns", 0)
            session["coach_turns"] += 1
            # Track conversation for report card generation
            session.setdefault("conversation_log", [])
            session["conversation_log"].append({"role": "client", "content": text, "turn": turn})
            if not session.get("coach_concluded") and "that is a wrap for today" in text.lower():
                session["coach_concluded"] = True
                print(f"[MODULE][{session_id}] Coach concluded session naturally")
                voice_session = session.get("voice_session")
                if voice_session:
                    await voice_session._send_browser({
                        "type": "session_complete",
                        "message": "Your coach has wrapped up the session.",
                    })

        voice_session = VoiceSession(
            session_id=session_id,
            system_prompt=system_prompt,
            voice=session.get("voice", "Sal"),
            on_agent_transcript=on_agent_transcript,
            on_client_transcript=on_client_transcript,
        )
        session["voice_session"] = voice_session

    # ── Connect to xAI if needed ────────────────────────────
    if not voice_session.connected:
        await websocket.send_json({"type": "status", "status": "connecting_voice"})
        connected = await voice_session.connect()
        if not connected:
            await websocket.send_json({
                "type": "error",
                "message": "Failed to connect to voice service.",
            })
            await websocket.close()
            return

    # ── Swap browser callback to this WebSocket ─────────────
    async def send_to_this_browser(msg: dict):
        try:
            await websocket.send_json(msg)
        except Exception:
            pass

    voice_session.set_browser_callback(send_to_this_browser)
    await websocket.send_json({"type": "status", "status": "ready"})

    if is_reconnect:
        await websocket.send_json({
            "type": "status",
            "status": "reconnected",
            "turn": voice_session._turn_count,
        })

    # ── Trigger greeting on first connection only ───────────
    if not is_reconnect:
        await asyncio.sleep(0.05)  # Let receive loop attach
        await voice_session.trigger_greeting()

    # ── Bridge: browser → xAI (audio + commands) ────────────
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
            logger.info("[MODULE][%s] Browser disconnected", session_id)
        except Exception as e:
            logger.error("[MODULE][%s] Browser→xAI error: %s", session_id, e)

    async def keepalive_ping():
        """Send periodic pings to browser to prevent proxy idle timeout."""
        try:
            while True:
                await asyncio.sleep(10)
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
        except asyncio.CancelledError:
            pass

    # Run browser bridge — when it ends, we just detach browser callback.
    # The xAI session continues running independently.
    ping_task = asyncio.create_task(keepalive_ping())
    try:
        await browser_to_xai()
    except Exception as e:
        logger.error("[MODULE][%s] Bridge error: %s", session_id, e)
    finally:
        ping_task.cancel()
        # Detach this browser — the voice session keeps running
        # Only clear if it's still pointing to our callback
        if voice_session._send_to_browser is send_to_this_browser:
            voice_session.set_browser_callback(None)
        logger.info("[MODULE][%s] Browser bridge ended (xAI session stays alive)", session_id)


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

    # ── Generate AI report card from conversation transcript ──
    report_card = None
    conversation_log = session.get("conversation_log", [])
    module_info = AVAILABLE_MODULES.get(module_key, {})
    module_name = module_info.get("name", module_key.replace("_", " ").title())

    if conversation_log and len(conversation_log) >= 2:
        try:
            report_card = await generate_module_report_card(
                module_key=module_key,
                module_name=module_name,
                conversation_log=conversation_log,
                duration_seconds=duration_seconds,
                student_turns=session.get("student_turns", 0),
                coach_turns=session.get("coach_turns", 0),
                session_qualified=session_qualified,
            )
            if report_card:
                # Save to module_sessions table (not report_cards — that has
                # a FK to training_sessions which module sessions aren't in)
                await db.save_module_report_card(session_id, report_card)
                logger.info(
                    "[MODULE] Report card saved on module_sessions: %s | score=%s",
                    session_id, report_card.get("overall_score"),
                )
        except Exception as e:
            logger.error("[MODULE] Report card generation failed: %s", e, exc_info=True)

    # ── Auto-generate homework if enough sessions ──
    homework_data = None
    try:
        report_cards = await db.get_user_report_cards(user["user_id"], limit=50)
        if len(report_cards) >= 5:
            engine = HomeworkEngine(min_sessions=5)
            result = engine.analyze(report_cards)
            if result:
                homework_data = {
                    "sessions_analyzed": result.sessions_analyzed,
                    "overall_assessment": result.overall_assessment,
                    "strengths": result.strengths,
                    "weaknesses": result.weaknesses,
                    "assignments": [asdict(a) for a in result.assignments],
                    "focus_order": result.recommended_focus_order,
                }
                await db.save_homework_report(user["user_id"], homework_data)
                logger.info("[MODULE] Homework auto-generated for user %s", user["user_id"])
    except Exception as e:
        logger.error("[MODULE] Homework generation failed: %s", e, exc_info=True)

    _active_module_sessions.pop(session_id, None)

    response = {
        "session_id": session_id,
        "module_key": module_key,
        "duration_seconds": duration_seconds,
        "billed_minutes": billed_minutes,
        "mastery": mastery_data,
        "session_qualified": session_qualified,
    }
    if report_card:
        response["report_card"] = report_card
    if homework_data:
        response["homework"] = homework_data
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
    script_type: str = ""  # final_expense, term_life, iul, mortgage_protection, whole_life, general_life


class UpdateScriptRequest(BaseModel):
    name: str | None = None
    content: str | None = None
    script_type: str | None = None


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
        user["user_id"], req.name.strip(), req.content, source="paste",
        script_type=req.script_type.strip(),
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
        script_type=req.script_type.strip() if req.script_type is not None else None,
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


# ══════════════════════════════════════════════════════════════
# Road to Mastery — Curriculum & Progress API
# ══════════════════════════════════════════════════════════════

@router.get("/mastery-plan")
async def get_mastery_plan(request: Request):
    """Get the Road to Mastery curriculum and user's progress."""
    user = get_current_user(request)
    user_id = user["user_id"]

    plan = await db.get_mastery_plan(user_id)

    return {
        "curriculum": CURRICULUM,
        "phases": PHASES,
        "total_days": TOTAL_DAYS,
        "total_activities": TOTAL_ACTIVITIES,
        "plan": plan,
    }


class StartPlanRequest(BaseModel):
    reset: bool = False


@router.post("/mastery-plan/start")
async def start_mastery_plan(req: StartPlanRequest, request: Request):
    """Start or reset the Road to Mastery plan."""
    user = get_current_user(request)
    user_id = user["user_id"]

    existing = await db.get_mastery_plan(user_id)
    if existing and not req.reset:
        return {"plan": existing, "message": "Plan already exists"}

    plan = await db.create_mastery_plan(user_id)
    return {"plan": plan, "message": "Plan started"}


class CompleteActivityRequest(BaseModel):
    day: int
    activity_index: int


@router.post("/mastery-plan/complete")
async def complete_plan_activity(req: CompleteActivityRequest, request: Request):
    """Mark a specific activity as completed."""
    user = get_current_user(request)
    user_id = user["user_id"]

    plan = await db.get_mastery_plan(user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No active mastery plan. Start one first.")

    # Validate day and activity_index
    day_data = next((d for d in CURRICULUM if d["day"] == req.day), None)
    if not day_data:
        raise HTTPException(status_code=400, detail=f"Invalid day: {req.day}")
    if req.activity_index < 0 or req.activity_index >= len(day_data["activities"]):
        raise HTTPException(status_code=400, detail=f"Invalid activity index: {req.activity_index}")

    # Check if already completed
    completed = plan.get("completed_activities", [])
    already_done = any(
        c["day"] == req.day and c["activity_index"] == req.activity_index
        for c in completed
    )
    if already_done:
        return {"plan": plan, "message": "Activity already completed"}

    plan = await db.complete_plan_activity(user_id, req.day, req.activity_index)
    return {"plan": plan, "message": "Activity completed"}


@router.post("/mastery-plan/reset")
async def reset_mastery_plan(request: Request):
    """Reset the Road to Mastery plan to day 1."""
    user = get_current_user(request)
    user_id = user["user_id"]
    plan = await db.reset_mastery_plan(user_id)
    return {"plan": plan, "message": "Plan reset"}

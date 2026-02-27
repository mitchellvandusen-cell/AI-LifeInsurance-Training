"""
Training session routes.
Handles session creation, WebSocket voice streaming, and session completion.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from src.api.middleware import get_current_user, get_ws_user
from src.core import database as db
from src.core.orchestrator import ConversationOrchestrator
from src.engine.persona_generator import PersonaGenerator
from src.prompts.system_prompt import build_system_prompt
from src.services.voice import VoiceSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Active sessions in memory (session_id → orchestrator)
_active_sessions: dict[str, dict] = {}

# Maximum session age before automatic cleanup (2 hours)
_SESSION_TTL_SECONDS = 2 * 60 * 60


async def _cleanup_stale_sessions():
    """Background task: evict sessions older than TTL to prevent memory leaks."""
    while True:
        await asyncio.sleep(300)  # Check every 5 minutes
        now = time.time()
        stale = [
            sid for sid, s in _active_sessions.items()
            if now - s.get("start_time", now) > _SESSION_TTL_SECONDS
        ]
        for sid in stale:
            session = _active_sessions.pop(sid, None)
            if session:
                voice_sess = session.get("voice_session")
                if voice_sess:
                    await voice_sess.disconnect()
                logger.warning("[SESSION] Evicted stale session %s (TTL exceeded)", sid)


def start_session_cleanup():
    """Call once at startup to begin the background cleanup loop."""
    asyncio.create_task(_cleanup_stale_sessions())


def _generate_client_info(persona) -> dict:
    """Generate the simplified client info shown to the agent.
    Only: first name, age, email, heart attack/cancer/stroke history, address, state.
    """
    states = [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    ]
    streets = [
        "Oak", "Maple", "Cedar", "Pine", "Elm", "Birch", "Willow",
        "Main", "Park", "Lake", "Hill", "River", "Valley", "Spring",
    ]
    types = ["St", "Ave", "Dr", "Ln", "Blvd", "Ct", "Way", "Rd"]

    first_name = persona.name.split()[0]
    state = random.choice(states)
    street_num = random.randint(100, 9999)
    street_name = random.choice(streets)
    street_type = random.choice(types)

    # Random email
    domains = ["gmail.com", "yahoo.com", "hotmail.com", "aol.com", "outlook.com"]
    email_user = first_name.lower() + str(random.randint(10, 999))
    email = f"{email_user}@{random.choice(domains)}"

    # Health history from persona
    conditions = [c.lower() for c in persona.health_conditions]
    has_heart_attack = any("heart" in c or "cardiac" in c or "myocardial" in c for c in conditions)
    has_cancer = any("cancer" in c or "carcinoma" in c or "tumor" in c for c in conditions)
    has_stroke = any("stroke" in c or "cerebrovascular" in c for c in conditions)

    return {
        "first_name": first_name,
        "age": persona.age,
        "email": email,
        "state": state,
        "address": f"{street_num} {street_name} {street_type}",
        "heart_attack_history": has_heart_attack,
        "cancer_history": has_cancer,
        "stroke_history": has_stroke,
    }


class StartSessionRequest(BaseModel):
    archetype: str | None = None
    voice: str | None = None  # Auto-select based on persona gender if not specified


# xAI voices: Ara (F), Eve (F), Rex (M), Leo (M), Sal (neutral)
VOICE_MAP = {"male": ["Rex", "Leo"], "female": ["Ara", "Eve"]}


def _pick_voice(gender: str, requested: str | None) -> str:
    """Pick a voice matching the persona's gender."""
    if requested:
        return requested
    voices = VOICE_MAP.get(gender, ["Sal"])
    return random.choice(voices)


@router.post("/start")
async def start_session(req: StartSessionRequest, request: Request):
    """Start a new training session. Returns session info and client card."""
    user = get_current_user(request)
    user_id = user["user_id"]

    # Check subscription / billing
    remaining = await db.get_remaining_minutes(user_id)
    total_available = (
        remaining["subscription_minutes"]
        + remaining["addon_minutes"]
        + (remaining["wallet_cents"] // 10)  # 10 cents per minute
    )
    if total_available <= 0:
        raise HTTPException(
            status_code=402,
            detail="No training time available. Add funds or upgrade your subscription.",
        )

    # Generate persona
    gen = PersonaGenerator()
    persona = gen.generate(archetype_name=req.archetype)

    # Auto-select voice based on persona gender
    voice = _pick_voice(persona.gender, req.voice)

    # Create orchestrator
    orch = ConversationOrchestrator(persona=persona)

    # Generate client info card
    client_info = _generate_client_info(persona)

    # Save to database
    session_record = await db.create_session(
        user_id=user_id,
        persona_data=persona.model_dump(),
        client_info=client_info,
        voice_name=voice,
    )

    # Store in memory
    _active_sessions[session_record["id"]] = {
        "orchestrator": orch,
        "user_id": user_id,
        "voice": voice,
        "voice_session": None,
        "start_time": time.time(),
        "turn_count": 0,
    }

    print(f"[SESSION] Started: {session_record['id']} | {persona.name} ({persona.gender}) | voice={voice}")

    return {
        "session_id": session_record["id"],
        "client_info": client_info,
        "voice": voice,
    }


@router.websocket("/ws/{session_id}")
async def training_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time voice training.
    Bridges browser ↔ xAI Voice Agent API with training engine in the middle.
    """
    await websocket.accept()
    print(f"[WS][{session_id}] WebSocket accepted, authenticating...")

    # Authenticate
    ws_user = await get_ws_user(websocket)
    if not ws_user:
        print(f"[WS][{session_id}] Auth failed — closing")
        return

    # Get active session
    session = _active_sessions.get(session_id)
    if not session:
        print(f"[WS][{session_id}] Session not found in active sessions")
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return

    if session["user_id"] != ws_user["user_id"]:
        await websocket.send_json({"type": "error", "message": "Unauthorized"})
        await websocket.close()
        return

    orch: ConversationOrchestrator = session["orchestrator"]

    # Disconnect any existing voice session to prevent duplicate agents
    existing_voice = session.get("voice_session")
    if existing_voice:
        print(f"[WS][{session_id}] Disconnecting previous voice session before new connection")
        await existing_voice.disconnect()
        session["voice_session"] = None

    # Build initial system prompt
    state_vars = orch.sm.get_state_for_prompt()
    objection_context = orch.objection_engine.get_objection_context(orch.sm)
    initial_prompt = build_system_prompt(
        persona=orch.persona,
        state_vars=state_vars,
        objection_context=objection_context,
    )

    # Callback: when agent transcript is received (user spoke)
    async def on_agent_transcript(text: str, turn: int):
        session["turn_count"] = turn
        print(f"[WS][{session_id}] Processing agent turn {turn}: {text[:60]}...")
        # Run through training engine
        result = orch.process_agent_turn(text)
        # Save transcript
        await db.save_transcript(session_id, turn, "agent", text)
        # Update xAI instructions with new state
        if voice_session and voice_session.connected:
            await voice_session.update_instructions(result["system_prompt"])
        # Send state update to browser
        try:
            await websocket.send_json({
                "type": "state_update",
                "data": {
                    "phase": result["state_summary"]["current_phase"],
                    "trust": result["state_summary"]["trust_score"],
                    "authority": result["state_summary"]["authority_score"],
                    "engagement": result["state_summary"]["engagement_level"],
                    "objection": result.get("objection_triggered"),
                },
            })
        except Exception as e:
            print(f"[WS][{session_id}] Failed to send state update: {e}")

    # Callback: when client transcript is received (AI spoke)
    async def on_client_transcript(text: str, turn: int):
        print(f"[WS][{session_id}] Processing client response turn {turn}: {text[:60]}...")
        orch.process_client_response(text)
        await db.save_transcript(session_id, turn, "client", text)

    # Create voice session
    voice_session = VoiceSession(
        session_id=session_id,
        system_prompt=initial_prompt,
        voice=session.get("voice", "Sal"),
        on_agent_transcript=on_agent_transcript,
        on_client_transcript=on_client_transcript,
    )
    session["voice_session"] = voice_session

    # Connect to xAI
    await websocket.send_json({"type": "status", "status": "connecting_voice"})
    connected = await voice_session.connect()
    if not connected:
        print(f"[WS][{session_id}] Voice connection failed — closing WebSocket")
        await websocket.send_json({
            "type": "error",
            "message": "Failed to connect to voice service. Check XAI_API_KEY.",
        })
        await websocket.close()
        return

    print(f"[WS][{session_id}] Voice ready — starting audio bridge")
    await websocket.send_json({"type": "status", "status": "ready"})

    # Bridge: browser → xAI (audio forwarding)
    async def browser_to_xai():
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                msg_type = data.get("type")

                if msg_type == "audio":
                    audio_data = data.get("data", "")
                    if audio_data:
                        await voice_session.send_audio(audio_data)

                elif msg_type == "end":
                    print(f"[WS][{session_id}] Client sent 'end' — closing bridge")
                    break

        except WebSocketDisconnect:
            print(f"[WS][{session_id}] Browser disconnected")
        except Exception as e:
            print(f"[WS][{session_id}] Browser→xAI error: {e}")
            import traceback
            traceback.print_exc()

    # Bridge: xAI → browser (audio + events forwarding)
    async def xai_to_browser():
        async def send_to_browser(msg: dict):
            try:
                await websocket.send_json(msg)
            except Exception:
                pass
        await voice_session.receive_events(send_to_browser)

    # Run both bridges concurrently — FIRST_COMPLETED is correct here:
    # when either side disconnects, we tear down the other side
    try:
        browser_task = asyncio.create_task(browser_to_xai(), name="browser_to_xai")
        xai_task = asyncio.create_task(xai_to_browser(), name="xai_to_browser")

        done, pending = await asyncio.wait(
            [browser_task, xai_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Log which task finished first
        for task in done:
            exc = task.exception() if not task.cancelled() else None
            if exc:
                print(f"[WS][{session_id}] Task {task.get_name()} failed: {exc}")
            else:
                print(f"[WS][{session_id}] Task {task.get_name()} completed")

        for task in pending:
            print(f"[WS][{session_id}] Cancelling {task.get_name()}")
            task.cancel()

    except Exception as e:
        print(f"[WS][{session_id}] Bridge error: {e}")
    finally:
        await voice_session.disconnect()
        print(f"[WS][{session_id}] Session cleanup complete")


@router.post("/{session_id}/end")
async def end_session(session_id: str, request: Request):
    """End a training session and generate the report card."""
    user = get_current_user(request)

    session = _active_sessions.get(session_id)
    if not session:
        # Session already ended — return existing report card if available
        existing = await db.get_report_card_by_session(session_id)
        if existing and str(existing["user_id"]) == user["user_id"]:
            return {
                "session_id": session_id,
                "report_id": str(existing["id"]),
                "report": existing.get("full_report", {}),
                "duration_seconds": existing.get("duration_seconds", 0),
                "already_ended": True,
            }
        raise HTTPException(status_code=404, detail="Session not found")

    if session["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    orch: ConversationOrchestrator = session["orchestrator"]

    # Disconnect voice
    voice_sess = session.get("voice_session")
    if voice_sess:
        await voice_sess.disconnect()

    # Generate report card (scores from grading engine)
    report = orch.end_session()

    # Enhance report with AI-generated coaching text
    try:
        from src.engine.report_analyzer import enhance_report_with_ai
        conversation_log = orch.sm.state.conversation_log
        report = await enhance_report_with_ai(report, conversation_log)
    except Exception as e:
        logger.warning("AI report enhancement failed, using template text: %s", e)

    # Calculate billing
    duration_seconds = int(time.time() - session["start_time"])
    billed_minutes = max(1, duration_seconds // 60)

    # Determine billing source
    remaining = await db.get_remaining_minutes(user["user_id"])
    billed_from = "subscription"
    cost_cents = 0

    if remaining["subscription_minutes"] >= billed_minutes:
        await db.use_subscription_minutes(user["user_id"], billed_minutes)
    elif remaining["addon_minutes"] >= billed_minutes:
        billed_from = "add_on"
        await db.use_addon_minutes(user["user_id"], billed_minutes)
    else:
        # Bill from wallet at 10 cents per minute
        billed_from = "wallet"
        cost_cents = billed_minutes * 10
        success = await db.deduct_wallet(
            user["user_id"], cost_cents, session_id, f"Training session: {billed_minutes} minutes"
        )
        if not success:
            cost_cents = 0  # Allow session even if wallet insufficient

    # Save to database
    final_state = orch.sm.get_state_for_prompt()
    await db.end_session(
        session_id=session_id,
        duration_seconds=duration_seconds,
        report_card=report,
        final_state=final_state,
        billed_minutes=billed_minutes,
        cost_cents=cost_cents,
        billed_from=billed_from,
    )

    # Save report card separately
    report_id = await db.save_report_card(session_id, user["user_id"], report)

    # Compute daily analytics
    from datetime import datetime, timezone
    await db.compute_analytics_for_date(user["user_id"], datetime.now(timezone.utc))

    # Clean up
    _active_sessions.pop(session_id, None)

    return {
        "session_id": session_id,
        "report_id": report_id,
        "report": report,
        "duration_seconds": duration_seconds,
        "billed_minutes": billed_minutes,
        "cost_cents": cost_cents,
        "billed_from": billed_from,
    }


@router.get("/{session_id}")
async def get_session(session_id: str, request: Request):
    user = get_current_user(request)
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(session["user_id"]) != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return session


@router.get("/{session_id}/transcript")
async def get_transcript(session_id: str, request: Request):
    user = get_current_user(request)
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(session["user_id"]) != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return await db.get_session_transcript(session_id)


@router.get("/")
async def list_sessions(request: Request, limit: int = 50, offset: int = 0):
    user = get_current_user(request)
    return await db.get_user_sessions(user["user_id"], limit, offset)

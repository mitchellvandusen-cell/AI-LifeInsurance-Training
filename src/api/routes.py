"""
FastAPI routes for InsuranceGrokBot.
Exposes endpoints for the frontend to:
- Start sessions with random or specific personas
- Send agent messages and receive AI client responses
- Get grading reports
- Get available archetypes
"""

from __future__ import annotations

import os
from typing import Optional

import openai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.core.orchestrator import ConversationOrchestrator
from src.engine.persona_generator import PersonaGenerator

app = FastAPI(
    title="InsuranceGrokBot",
    description="AI Sales Training for Life Insurance Agents",
    version="1.0.0",
)

# Active sessions
sessions: dict[str, ConversationOrchestrator] = {}


# ── Request/Response Models ─────────────────────────────────────

class StartSessionRequest(BaseModel):
    archetype: Optional[str] = None
    seed: Optional[int] = None
    randomize: bool = True


class StartSessionResponse(BaseModel):
    session_id: str
    persona: dict


class AgentMessageRequest(BaseModel):
    session_id: str
    text: str
    audio_metadata: Optional[dict] = None


class AgentMessageResponse(BaseModel):
    client_response: str
    turn_number: int
    state_summary: dict
    objection_triggered: Optional[dict] = None
    analysis: dict


class EndSessionRequest(BaseModel):
    session_id: str


class ArchetypeListResponse(BaseModel):
    archetypes: list[str]


# ── LLM Client ─────────────────────────────────────────────────

async def _get_llm_response(system_prompt: str, conversation_history: list[dict]) -> str:
    """Call xAI Grok to generate the AI client response (async)."""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="No LLM API key configured. Set XAI_API_KEY.",
        )

    client = openai.AsyncOpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation_history:
        role = "user" if msg["role"] == "agent" else "assistant"
        messages.append({"role": role, "content": msg["content"]})

    response = await client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "grok4-1-fast-reasoning"),
        max_tokens=500,
        messages=messages,
    )

    return response.choices[0].message.content


# ── Routes ──────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "InsuranceGrokBot",
        "version": "1.0.0",
        "description": "AI Sales Training for Life Insurance Agents",
        "endpoints": {
            "POST /session/start": "Start a new training session",
            "POST /session/message": "Send agent message, receive AI client response",
            "POST /session/end": "End session and get report card",
            "GET /archetypes": "List available client archetypes",
            "GET /session/{session_id}/state": "Get current session state",
            "GET /session/{session_id}/history": "Get conversation history",
        },
    }


@app.get("/archetypes", response_model=ArchetypeListResponse)
async def list_archetypes():
    """List all available client archetypes."""
    gen = PersonaGenerator()
    return ArchetypeListResponse(archetypes=gen.get_archetype_names())


@app.post("/session/start", response_model=StartSessionResponse)
async def start_session(req: StartSessionRequest):
    """Start a new training session with a random or specific persona."""
    archetype = None if req.randomize else req.archetype
    orch = ConversationOrchestrator(
        archetype_name=archetype,
        seed=req.seed,
    )

    session_id = orch.sm.state.session_id
    sessions[session_id] = orch

    return StartSessionResponse(
        session_id=session_id,
        persona=orch.get_persona_info(),
    )


@app.post("/session/message", response_model=AgentMessageResponse)
async def send_message(req: AgentMessageRequest):
    """
    Send the agent's message and receive the AI client's response.
    This is the main conversation loop endpoint.
    """
    orch = sessions.get(req.session_id)
    if not orch:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Process agent turn
    result = orch.process_agent_turn(
        agent_text=req.text,
        audio_metadata=req.audio_metadata,
    )

    # Get conversation history for LLM
    history = orch.get_conversation_history()

    # Generate AI client response
    try:
        client_response = await _get_llm_response(
            system_prompt=result["system_prompt"],
            conversation_history=history,
        )
    except Exception as e:
        # Fallback response if LLM fails
        client_response = _fallback_response(orch, result)

    # Process client response for state updates
    orch.process_client_response(client_response)

    return AgentMessageResponse(
        client_response=client_response,
        turn_number=result["turn_number"],
        state_summary=result["state_summary"],
        objection_triggered=result["objection_triggered"],
        analysis=result["analysis"],
    )


@app.post("/session/end")
async def end_session(req: EndSessionRequest):
    """End the session and return the full grading report."""
    orch = sessions.get(req.session_id)
    if not orch:
        raise HTTPException(status_code=404, detail="Session not found.")

    report = orch.end_session()

    # Clean up session
    del sessions[req.session_id]

    return report


@app.get("/session/{session_id}/state")
async def get_state(session_id: str):
    """Get current session state (for debugging/live display)."""
    orch = sessions.get(session_id)
    if not orch:
        raise HTTPException(status_code=404, detail="Session not found.")
    return orch.get_current_state()


@app.get("/session/{session_id}/history")
async def get_history(session_id: str):
    """Get full conversation history."""
    orch = sessions.get(session_id)
    if not orch:
        raise HTTPException(status_code=404, detail="Session not found.")
    return orch.get_conversation_history()


@app.get("/session/{session_id}/persona")
async def get_persona(session_id: str):
    """Get persona info for the current session."""
    orch = sessions.get(session_id)
    if not orch:
        raise HTTPException(status_code=404, detail="Session not found.")
    return orch.get_persona_info()


def _fallback_response(orch: ConversationOrchestrator, result: dict) -> str:
    """Generate a basic response when LLM is unavailable."""
    state = result["state_summary"]
    phase = state["current_phase"]

    if result.get("objection_triggered"):
        return result["objection_triggered"]["text"]

    responses = {
        "intro": "Hello? Yeah, I'm here. Who is this?",
        "rapport_discovery": "Mm-hmm, yeah, I guess that makes sense. What else do you need to know?",
        "medical_underwriting": "Uh, let me think... I take a blood pressure pill, that's about it I think.",
        "preframing": "Okay, so what happens next?",
        "presentation": "Alright, so what does this cost me?",
        "close": "Okay, I think I'm interested. What do you need from me?",
    }

    return responses.get(phase, "I'm still here, go ahead.")

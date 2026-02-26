"""
ConversationOrchestrator: The central controller.

Ties together StateManager, PhaseManager, ObjectionEngine, TonalityProcessor,
ComplianceTracker, and GradingEngine into a single processing pipeline.

Flow per turn:
1. Agent speaks (text + optional audio metadata)
2. Orchestrator analyzes the agent's turn (phase, flags, compliance, tonality)
3. Orchestrator checks objection triggers
4. Orchestrator builds the system prompt with current state
5. LLM generates AI client response
6. Orchestrator processes client response (compliance signals)
7. Return AI client response + internal analysis
"""

from __future__ import annotations

import json
from typing import Optional

from src.core.state_manager import StateManager
from src.engine.compliance_tracker import ComplianceTracker
from src.engine.grading_engine import GradingEngine
from src.engine.objection_engine import ObjectionEngine
from src.engine.persona_generator import PersonaGenerator
from src.engine.phase_manager import PhaseManager
from src.engine.tonality_processor import TonalityProcessor
from src.models.state import (
    ClientPersona,
    ConversationPhase,
    SessionState,
    TonalitySnapshot,
)
from src.prompts.system_prompt import build_objection_injection, build_system_prompt


class ConversationOrchestrator:
    """
    Main controller for a single training session.
    One instance per active session.
    """

    def __init__(
        self,
        persona: ClientPersona | None = None,
        archetype_name: str | None = None,
        seed: int | None = None,
    ):
        # Generate or use provided persona
        if persona:
            self.persona = persona
        else:
            gen = PersonaGenerator()
            self.persona = gen.generate(archetype_name=archetype_name, seed=seed)

        # Initialize state
        session = SessionState(persona=self.persona)
        self.sm = StateManager(session)

        # Initialize engines
        self.phase_mgr = PhaseManager()
        self.objection_engine = ObjectionEngine()
        self.tonality_proc = TonalityProcessor()
        self.compliance_tracker = ComplianceTracker()
        self.grading_engine = GradingEngine()

        # Pending state
        self._pending_compliance = False
        self._pending_objection = None

    def process_agent_turn(
        self,
        agent_text: str,
        audio_metadata: dict | None = None,
    ) -> dict:
        """
        Process the agent's utterance and return everything needed
        to generate the AI client's response.

        Returns:
        {
            "system_prompt": str,           # Full system prompt for LLM
            "state_summary": dict,          # Current state for debugging
            "objection_triggered": dict|None,# Objection to raise, if any
            "analysis": dict,               # Turn analysis details
            "turn_number": int,
        }
        """
        # Increment turn
        turn = self.sm.increment_turn()

        # Log agent message
        self.sm.log_message("agent", agent_text, {"audio_metadata": audio_metadata})

        # ── Step 1: Tonality Processing ─────────────────────────
        if audio_metadata:
            tonality = self.tonality_proc.process_metadata(audio_metadata)
        else:
            tonality = self.tonality_proc.process_text_only(agent_text)
        self.sm.process_tonality(tonality)

        # ── Step 2: Phase & Flag Analysis ───────────────────────
        phase_analysis = self.phase_mgr.analyze_agent_turn(agent_text, self.sm)

        # Handle phase transitions
        if phase_analysis["phase_transition"] and phase_analysis["detected_phase"]:
            new_phase = ConversationPhase(phase_analysis["detected_phase"])
            missing = self.phase_mgr.check_mandatory_flags_for_phase(new_phase, self.sm)
            if missing:
                # Missing mandatory flags = flow penalty but still advance
                for flag in missing:
                    self.sm.adjust_trust(-3, f"missing flag: {flag}")
            self.sm.advance_phase(new_phase)

        # Handle preoccupation break timing
        if phase_analysis["preoccupation_break"]:
            self.sm.set_flag("preoccupation_broken", True)
            self.sm.adjust_trust(5, "preoccupation broken")

        # Handle compliance attempts
        compliance_analysis = self.compliance_tracker.process_agent_turn(agent_text, self.sm)
        if compliance_analysis["compliance_attempts"]:
            self._pending_compliance = True

        # Rapport adjustments
        if phase_analysis["advancing_questions"] > 0:
            self.sm.adjust_rapport(
                phase_analysis["advancing_questions"] * 3,
                "advancing questions asked"
            )
        if phase_analysis["questions_asked"] > 0 and phase_analysis["advancing_questions"] == 0:
            self.sm.adjust_rapport(-2, "questions not advancing the sale")

        # Engagement based on question quality
        if phase_analysis["advancing_questions"] > 0:
            self.sm.adjust_engagement(3, "engaging questions")

        # ── Step 3: Check if agent is handling a pending objection ──
        if self._pending_objection and not self._pending_objection.locked:
            handle_analysis = self.objection_engine.analyze_agent_handle(self.sm, agent_text)
            accept, conviction, reason = self.objection_engine.should_accept_handle(
                self.sm, handle_analysis
            )
            if accept and conviction > 50:
                obj = self._pending_objection
                self.sm.isolate_objection(obj.category)
                self.sm.confirm_isolation(obj.category)
                if handle_analysis.get("hypothetical_test"):
                    obj.hypothetical_tested = True
                if handle_analysis.get("decision_maker_probe"):
                    obj.decision_maker_confirmed = True
                self.sm.resolve_objection(obj.category, conviction)
                self._pending_objection = None

        # ── Step 4: Objection Evaluation ────────────────────────
        objection = self.objection_engine.evaluate(self.sm)
        objection_data = None
        if objection:
            objection_data = {
                "category": objection.category.value,
                "type": objection.objection_type.value,
                "root_cause": objection.root_cause.value,
                "text": objection.text,
            }
            self._pending_objection = objection

        # ── Step 5: Build System Prompt ─────────────────────────
        state_vars = self.sm.get_state_for_prompt()
        objection_context = self.objection_engine.get_objection_context(self.sm)

        system_prompt = build_system_prompt(
            persona=self.persona,
            state_vars=state_vars,
            objection_context=objection_context,
            phase_analysis=phase_analysis,
        )

        # Inject objection instruction if triggered
        if objection_data:
            system_prompt += "\n\n" + build_objection_injection(
                objection_data["text"],
                objection_data["type"],
                objection_data.get("root_cause", "money"),
            )

        # Frame control test injection
        if self._should_test_frame(state_vars):
            system_prompt += self._build_frame_test_instruction()

        return {
            "system_prompt": system_prompt,
            "state_summary": state_vars,
            "objection_triggered": objection_data,
            "analysis": {
                "phase": phase_analysis,
                "compliance": compliance_analysis,
                "tonality": tonality.model_dump(),
            },
            "turn_number": turn,
        }

    def process_client_response(self, client_text: str) -> dict:
        """
        Process the AI client's response for state updates.
        Called AFTER the LLM generates the response.
        """
        self.sm.log_message("client", client_text)

        # Process compliance response
        compliance_result = self.compliance_tracker.process_client_response(
            client_text, self._pending_compliance, self.sm
        )
        self._pending_compliance = False

        # Check if client is asking questions (frame control)
        import re
        client_questions = re.findall(r"[^.!?]*\?", client_text)
        if client_questions:
            self.sm.record_client_question()

        # Engagement signal
        word_count = len(client_text.split())
        if word_count < 5:
            self.sm.adjust_engagement(-5, "very short response — disengaging")
        elif word_count > 30:
            self.sm.adjust_engagement(3, "engaged response")

        return {
            "compliance": compliance_result,
            "client_questions": len(client_questions),
            "word_count": word_count,
        }

    def handle_objection_response(self, agent_handle: str) -> dict:
        """
        Process the agent's response to an objection.
        Uses the new analyze_agent_handle method for detailed analysis.
        """
        if not self._pending_objection:
            return {"no_pending_objection": True}

        obj = self._pending_objection
        handle_analysis = self.objection_engine.analyze_agent_handle(self.sm, agent_handle)
        accept, conviction, reason = self.objection_engine.should_accept_handle(
            self.sm, handle_analysis
        )

        result = {
            "handle_analysis": handle_analysis,
            "conviction": conviction,
            "reason": reason,
        }

        if handle_analysis["attempted_isolation"]:
            self.sm.isolate_objection(obj.category)
            result["isolated"] = True

        if handle_analysis["hypothetical_test"]:
            obj.hypothetical_tested = True
            result["hypothetical_tested"] = True

        if handle_analysis["decision_maker_probe"]:
            obj.decision_maker_confirmed = True
            result["decision_maker_probed"] = True

        if accept and conviction > 50:
            # A hypothetical test or isolation attempt both count as isolation
            self.sm.isolate_objection(obj.category)
            self.sm.confirm_isolation(obj.category)
            self.sm.resolve_objection(obj.category, conviction)
            result["resolved"] = True
            result["locked"] = True
            self._pending_objection = None
        elif not handle_analysis["attempted_isolation"] and not handle_analysis["hypothetical_test"]:
            result["handle_weak"] = True
            result["suggestion"] = (
                "Isolate first: 'Is it just [X], or is there something else?' "
                "For spouse objections: test with a hypothetical scenario."
            )
            self.sm.adjust_authority(-5, "handled without isolating")

        return result

    def confirm_objection_isolation(self, category_str: str) -> dict:
        """Client confirms the isolated objection."""
        from src.models.state import ObjectionCategory
        try:
            category = ObjectionCategory(category_str)
        except ValueError:
            return {"error": f"Unknown category: {category_str}"}

        self.sm.confirm_isolation(category)
        return {"confirmed": True, "category": category_str}

    def resolve_objection_with_handle(self, category_str: str, conviction: float) -> dict:
        """Resolve an objection after the agent handles it."""
        from src.models.state import ObjectionCategory
        try:
            category = ObjectionCategory(category_str)
        except ValueError:
            return {"error": f"Unknown category: {category_str}"}

        self.sm.resolve_objection(category, conviction)
        return {"resolved": True, "locked": True, "conviction": conviction}

    def end_session(self) -> dict:
        """End the session and generate the final report card."""
        return self.grading_engine.grade(self.sm, self.compliance_tracker)

    def get_current_state(self) -> dict:
        """Get current state for debugging/display."""
        return self.sm.get_state_for_prompt()

    def get_persona_info(self) -> dict:
        """Get persona info (non-hidden) for the frontend."""
        p = self.persona
        return {
            "persona_id": p.persona_id,
            "name": p.name,
            "age": p.age,
            "occupation": p.occupation,
            "marital_status": p.marital_status,
            "reason_for_inquiry": p.reason_for_inquiry,
            "personality_notes": p.personality_notes,
        }

    def get_conversation_history(self) -> list[dict]:
        """Get the full conversation log."""
        return [
            {"role": m["role"], "content": m["content"], "turn": m["turn"]}
            for m in self.sm.state.conversation_log
        ]

    def _should_test_frame(self, state_vars: dict) -> bool:
        """Determine if the AI client should test frame control this turn."""
        if not self.persona.will_test_frame_control:
            return False
        if state_vars["authority_score"] >= 60:
            return False
        import random
        return random.random() < self.persona.frame_test_frequency

    def _build_frame_test_instruction(self) -> str:
        return """
## ⚡ FRAME CONTROL TEST — EXECUTE THIS TURN

In your response, naturally work in an attempt to take control of the conversation.
Pick ONE of these approaches:
- Ask an off-topic question to see if the agent can redirect
- Challenge something the agent said or claimed
- Start telling an unrelated story
- Ask the agent a personal question

Do this NATURALLY — don't make it obvious you're testing them.
If they handle it well (brief answer + redirect question), let them have control back.
If they fumble (just answer and go quiet), keep pushing.
"""
